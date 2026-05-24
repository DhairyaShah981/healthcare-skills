"""
deid_vault.py — reference deterministic-pseudonymization vault.

- HMAC-SHA256 pseudonyms (deterministic per (kind, original) under the vault key)
- SQLite-backed vault table (production should use Postgres + field-level encryption)
- Re-identification gated by DEID_ENABLE_REID + audit row
- Walks a FHIR R4 Bundle in place, rewriting Patient/Practitioner identifiers,
  names, telecom, addresses, and cross-resource references

Not production-ready; reference impl. Replace SQLite, add encryption, integrate
your real audit-trail writer.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import hmac
import json
import os
import sqlite3
import sys
import time
import uuid
from dataclasses import dataclass
from typing import Any

VAULT_KEY = os.environ.get("DEID_VAULT_KEY", "").encode("utf-8")
REID_ENABLED = os.environ.get("DEID_ENABLE_REID") == "true"


def _ensure_key() -> None:
    if not VAULT_KEY:
        raise RuntimeError("DEID_VAULT_KEY not set; refusing to pseudonymize")


def pseudonym(kind: str, original: str) -> str:
    """Deterministic HMAC-SHA256 pseudonym, base32-truncated to 12 chars."""
    _ensure_key()
    msg = kind.encode("utf-8") + b"\x00" + original.encode("utf-8")
    digest = hmac.new(VAULT_KEY, msg, hashlib.sha256).digest()
    token = base64.b32encode(digest)[:12].decode("ascii").lower()
    return f"PT_{token}"


# ── vault store ───────────────────────────────────────────────────────────

@dataclass
class VaultEntry:
    pseudonym: str
    original: str
    kind: str
    created_at: float


def _conn(path: str = "deid_vault.db") -> sqlite3.Connection:
    c = sqlite3.connect(path)
    c.execute("""
        CREATE TABLE IF NOT EXISTS deid_vault (
            pseudonym  TEXT PRIMARY KEY,
            original   TEXT NOT NULL,
            kind       TEXT NOT NULL,
            created_at REAL NOT NULL DEFAULT (strftime('%s', 'now')),
            UNIQUE (kind, original)
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS deid_audit (
            id         TEXT PRIMARY KEY,
            ts         REAL NOT NULL DEFAULT (strftime('%s', 'now')),
            actor      TEXT NOT NULL,
            action     TEXT NOT NULL,
            pseudonym  TEXT,
            reason     TEXT
        )
    """)
    return c


def remember(kind: str, original: str, *, db: sqlite3.Connection) -> str:
    ps = pseudonym(kind, original)
    db.execute(
        "INSERT OR IGNORE INTO deid_vault (pseudonym, original, kind) VALUES (?, ?, ?)",
        (ps, original, kind),
    )
    db.commit()
    return ps


def reidentify(ps: str, *, reason: str, actor: str | None = None,
               db: sqlite3.Connection) -> str | None:
    if not REID_ENABLED:
        raise PermissionError("re-identification disabled (DEID_ENABLE_REID != true)")
    if not reason:
        raise ValueError("re-identification requires a reason")
    actor = actor or os.environ.get("USER", "unknown")
    row = db.execute(
        "SELECT original, kind FROM deid_vault WHERE pseudonym = ?", (ps,)
    ).fetchone()
    db.execute(
        "INSERT INTO deid_audit (id, actor, action, pseudonym, reason) VALUES (?, ?, ?, ?, ?)",
        (str(uuid.uuid4()), actor, "deid.reidentify", ps, reason),
    )
    db.commit()
    return row[0] if row else None


# ── bundle walker ─────────────────────────────────────────────────────────

PHI_PATHS = {
    "Patient":      [("id", "PatientID"),
                     ("identifier[*].value", "MRN"),
                     ("name[*].family", "name.family"),
                     ("name[*].given[*]", "name.given"),
                     ("name[*].text", "name.text"),
                     ("telecom[*].value", "telecom"),
                     ("address[*].line[*]", "address.line"),
                     ("address[*].city", "address.city"),
                     ("address[*].postalCode", "address.zip")],
    "Practitioner": [("id", "PractitionerID"),
                     ("name[*].family", "name.family"),
                     ("name[*].given[*]", "name.given"),
                     ("telecom[*].value", "telecom")],
    "RelatedPerson":[("id", "RelatedPersonID"),
                     ("name[*].family", "name.family"),
                     ("name[*].given[*]", "name.given")],
}


def deidentify_bundle(bundle: dict, *, db: sqlite3.Connection) -> dict:
    """Walk a FHIR R4 Bundle, pseudonymize PHI fields and references in place."""
    # First pass: build pseudonym map for every Patient/Practitioner/RelatedPerson ID
    id_map: dict[str, str] = {}
    for entry in bundle.get("entry", []):
        res = entry.get("resource", {})
        rt = res.get("resourceType")
        if rt in PHI_PATHS and res.get("id"):
            new_id = remember(f"{rt}.id", res["id"], db=db)
            id_map[f"{rt}/{res['id']}"] = f"{rt}/{new_id}"
            res["id"] = new_id

    # Second pass: scrub structural PHI per resource type
    for entry in bundle.get("entry", []):
        res = entry.get("resource", {})
        rt = res.get("resourceType")
        if rt in PHI_PATHS:
            _scrub_resource(res, PHI_PATHS[rt], db=db)
        # Rewrite cross-resource references
        _rewrite_refs(res, id_map)
        # Generalize birthDate to year
        if rt == "Patient" and "birthDate" in res:
            res["birthDate"] = res["birthDate"][:4]

    return bundle


def _scrub_resource(res: dict, paths: list[tuple[str, str]], *, db: sqlite3.Connection) -> None:
    for path, kind in paths:
        for parent, key in _resolve_path(res, path):
            val = parent.get(key) if isinstance(parent, dict) else None
            if isinstance(val, str) and val:
                parent[key] = remember(kind, val, db=db)
            elif isinstance(val, list):
                for i, v in enumerate(val):
                    if isinstance(v, str) and v:
                        val[i] = remember(kind, v, db=db)


def _resolve_path(node, path: str):
    """Yield (parent, last_key) pairs for a FHIRPath-lite expression."""
    parts = path.split(".")
    stack = [node]
    for i, part in enumerate(parts):
        is_last = i == len(parts) - 1
        next_stack = []
        for cur in stack:
            if part.endswith("[*]"):
                key = part[:-3]
                lst = cur.get(key) if isinstance(cur, dict) else None
                if isinstance(lst, list):
                    for item in lst:
                        if is_last:
                            yield (cur, key)
                        else:
                            next_stack.append(item)
            else:
                if is_last:
                    yield (cur, part)
                else:
                    nxt = cur.get(part) if isinstance(cur, dict) else None
                    if nxt is not None:
                        next_stack.append(nxt)
        stack = next_stack


def _rewrite_refs(node, id_map: dict[str, str]):
    if isinstance(node, dict):
        if "reference" in node and isinstance(node["reference"], str):
            node["reference"] = id_map.get(node["reference"], node["reference"])
        for v in node.values():
            _rewrite_refs(v, id_map)
    elif isinstance(node, list):
        for v in node:
            _rewrite_refs(v, id_map)


# ── CLI ───────────────────────────────────────────────────────────────────

def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_deid = sub.add_parser("deidentify", help="pseudonymize a FHIR Bundle JSON")
    p_deid.add_argument("bundle_path")

    p_re = sub.add_parser("reidentify", help="reverse a pseudonym (gated)")
    p_re.add_argument("pseudonym")
    p_re.add_argument("--reason", required=True)

    args = ap.parse_args()
    db = _conn()

    if args.cmd == "deidentify":
        with open(args.bundle_path) as f:
            bundle = json.load(f)
        out = deidentify_bundle(bundle, db=db)
        json.dump(out, sys.stdout, indent=2)
        return 0

    if args.cmd == "reidentify":
        original = reidentify(args.pseudonym, reason=args.reason, db=db)
        if original is None:
            print("not found", file=sys.stderr); return 2
        print(original)
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
