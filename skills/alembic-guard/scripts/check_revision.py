#!/usr/bin/env python3
"""
check_revision.py — pre-commit lint for Alembic migrations.

Walks `alembic/versions/*.py` and applies the alembic-guard rules:
  ALG-001 revision ID ≤ 32 chars
  ALG-002 linear chain
  ALG-003 explicit downgrade
  ALG-004 no PHI in comments
  ALG-005 batched data migrations

Usage:
    python check_revision.py                     # walks alembic/versions/
    python check_revision.py path/to/versions/   # explicit path
    python check_revision.py --files a.py b.py   # named files (pre-commit hook usage)

Exit 0 when clean, 1 on ERROR findings.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REVISION_RE = re.compile(r"^revision(?:\s*:\s*str)?\s*=\s*[\"']([^\"']+)[\"']", re.M)
DOWNREV_RE = re.compile(r"^down_revision(?:\s*:.*)?\s*=\s*[\"']([^\"']+)[\"']", re.M)
DOWNGRADE_DEF_RE = re.compile(r"^def\s+downgrade\b", re.M)
EXEC_UPDATE_RE = re.compile(r"op\.execute\(\s*[\"\']\s*UPDATE\s", re.I)
EXEC_DELETE_RE = re.compile(r"op\.execute\(\s*[\"\']\s*DELETE\s", re.I)

# Lightweight PHI detection (ALG-004)
PHI_PATTERNS = [
    ("NAME", re.compile(r"\b(?:Mr|Mrs|Ms|Mx|Dr)\.?\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?\b")),
    ("NAME", re.compile(r"\bpatient\s+[A-Z][a-z]+\s+[A-Z][a-z]+", re.I)),
    ("SSN",  re.compile(r"\b\d{3}-\d{2}-\d{4}\b")),
    ("MRN",  re.compile(r"(?i)\bMRN[:\s#]*[A-Z]?\d{6,10}\b")),
    ("ACCT", re.compile(r"\bnumber\s+\d{4,}\b", re.I)),
    ("ACCT", re.compile(r"\baccount[:\s#]+\d{4,}\b", re.I)),
]

MAX_REVISION_LEN = 32


def check_file(path: Path) -> list[tuple[str, str, str]]:
    text = path.read_text(encoding="utf-8", errors="replace")
    findings: list[tuple[str, str, str]] = []

    # ALG-001
    m = REVISION_RE.search(text)
    if m:
        rev = m.group(1)
        if len(rev) > MAX_REVISION_LEN:
            findings.append(("ALG-001", "ERROR",
                             f"revision '{rev}' is {len(rev)} chars (max {MAX_REVISION_LEN})"))
    else:
        findings.append(("ALG-001", "WARN", "no `revision = ...` declaration found"))

    md = DOWNREV_RE.search(text)
    if md and len(md.group(1)) > MAX_REVISION_LEN:
        findings.append(("ALG-001", "ERROR",
                         f"down_revision '{md.group(1)}' exceeds {MAX_REVISION_LEN} chars"))

    # ALG-003
    if not DOWNGRADE_DEF_RE.search(text):
        findings.append(("ALG-003", "WARN", "no downgrade() function"))

    # ALG-004 — PHI in file contents (comments + strings)
    for tag, pat in PHI_PATTERNS:
        for hit in pat.findall(text):
            findings.append(("ALG-004", "ERROR",
                             f"possible PHI ({tag}) in file: {hit[:24]}…"))

    # ALG-005 — naked UPDATE / DELETE in op.execute
    if EXEC_UPDATE_RE.search(text) or EXEC_DELETE_RE.search(text):
        findings.append(("ALG-005", "WARN",
                         "bare UPDATE/DELETE in op.execute — prefer chunked / batched migration"))

    return findings


def check_linearity(versions_dir: Path) -> list[tuple[str, str, str]]:
    """ALG-002 — exactly one head (no down_revision points to it)."""
    files = list(versions_dir.glob("*.py"))
    if not files:
        return []
    revs: list[str] = []
    down_revs: set[str] = set()
    for f in files:
        text = f.read_text(encoding="utf-8", errors="replace")
        m = REVISION_RE.search(text)
        if m:
            revs.append(m.group(1))
        for line in re.findall(r"^down_revision\s*=\s*(.+)$", text, re.M):
            for s in re.findall(r"[\"']([^\"']+)[\"']", line):
                down_revs.add(s)
    heads = [r for r in revs if r not in down_revs]
    if len(heads) > 1:
        return [("ALG-002", "ERROR",
                 f"multiple heads on disk: {heads}; run `alembic merge` and commit the merge")]
    return []


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("path", nargs="?", default="alembic/versions",
                    help="versions/ directory (default: alembic/versions)")
    ap.add_argument("--files", nargs="*", default=None,
                    help="check only the named files (pre-commit hook usage)")
    args = ap.parse_args()

    if args.files:
        files = [Path(p) for p in args.files]
        versions_dir = None
    else:
        versions_dir = Path(args.path)
        if not versions_dir.is_dir():
            print(f"{versions_dir}: no such directory", file=sys.stderr)
            return 2
        files = sorted(versions_dir.glob("*.py"))

    error_count = 0
    for f in files:
        findings = check_file(f)
        if not findings:
            continue
        print(f"\n{f}")
        for rule, sev, msg in findings:
            print(f"  {rule}  {sev:<5}  {msg}")
            if sev == "ERROR":
                error_count += 1

    if versions_dir:
        for rule, sev, msg in check_linearity(versions_dir):
            print(f"\n{versions_dir}")
            print(f"  {rule}  {sev:<5}  {msg}")
            if sev == "ERROR":
                error_count += 1

    if error_count:
        print(f"\n{error_count} ERROR finding(s). Block commit.", file=sys.stderr)
        return 1
    print("\nalembic-guard: clean")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
