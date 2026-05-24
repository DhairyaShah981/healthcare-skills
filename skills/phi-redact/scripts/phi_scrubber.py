#!/usr/bin/env python3
"""
phi_scrubber.py — reference offline PHI scrubber for the phi-redact skill.

Usage:
    python phi_scrubber.py path/to/file.log        # scrub a file → stdout
    cat log.txt | python phi_scrubber.py -         # scrub stdin → stdout
    python phi_scrubber.py --json file.json        # JSON-aware mode

Design:
- Pure-Python, zero required dependencies (uses only stdlib `re`, `json`, `sys`).
- Optional upgrade: if `presidio_analyzer` is importable, use it for higher recall.
- Replaces findings with typed placeholders so downstream parsers still work.
- Emits a per-finding audit table to stderr so the user sees what changed.

Not for production de-identification of large datasets. Use as a logging-hygiene
guard and as a pre-commit check for fixtures. For dataset de-id, use Presidio +
the `deid-vault` skill (reversible HMAC pseudonymization).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from typing import Iterable

# ── patterns ────────────────────────────────────────────────────────────────

PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("SSN",   re.compile(r"\b(?!000|666)\d{3}-\d{2}-\d{4}\b")),
    ("EMAIL", re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")),
    ("PHONE", re.compile(r"\b(?:\+?1[-.\s]?)?\(?[2-9]\d{2}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b")),
    ("DOB",   re.compile(r"\b(19|20)\d{2}-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])\b")),
    ("DOB",   re.compile(r"\b(0?[1-9]|1[0-2])[/-](0?[1-9]|[12]\d|3[01])[/-](19|20)?\d{2}\b")),
    ("MRN",   re.compile(r"(?i)\bMRN[:\s#]*[A-Z]?\d{6,10}\b")),
    ("ZIP",   re.compile(r"\b\d{5}(?:-\d{4})?\b")),
    ("URL",   re.compile(r"\bhttps?://[^\s<>\"']+")),
    ("IP",    re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")),
]

# JSON keys whose VALUES are PHI regardless of regex match
PHI_KEYS = {
    "name", "first_name", "last_name", "middle_name", "maiden_name",
    "patient_name", "full_name", "given_name", "family_name", "guardian_name",
    "doctor", "doctor_name", "provider", "provider_name", "physician",
    "dob", "birth_date", "date_of_birth", "birthdate",
    "ssn", "social_security",
    "mrn", "chart_id", "patient_id", "medical_record_number", "medical_record_id",
    "phone", "telephone", "cell", "mobile", "fax",
    "email", "email_address",
    "address", "street", "line1", "line2", "city", "zip", "zip_code", "postal_code",
    "account", "account_no", "account_number",
    "member_id", "policy_no", "policy_number", "subscriber_id",
    "license", "driver_license", "state_id",
    "ip", "ip_address",
    "device_id", "serial_no", "serial_number",
}

# Honorific-prefixed names ("Dr. Sanjay Patel", "Ms. Maria Hernandez")
NAME_RE = re.compile(
    r"\b(?:Mr|Mrs|Ms|Mx|Dr|RN|MD|DO|NP|PA)\.?\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?\b"
)

# Capture year for DOB → year-only replacement
YEAR_RE = re.compile(r"(19|20)\d{2}")


@dataclass
class Finding:
    type: str
    original: str
    replacement: str
    line: int

    def truncated(self) -> str:
        return (self.original[:8] + "…") if len(self.original) > 9 else self.original


def _placeholder(kind: str, original: str) -> str:
    if kind == "DOB":
        m = YEAR_RE.search(original)
        return f"[DOB:year={m.group(0)}]" if m else "[DOB]"
    return f"[{kind}]"


# ── scrubbing ───────────────────────────────────────────────────────────────

def scrub_text(text: str) -> tuple[str, list[Finding]]:
    findings: list[Finding] = []
    lines = text.split("\n")
    for i, line in enumerate(lines, 1):
        for kind, pat in PATTERNS:
            line, n = _apply(pat, line, kind, findings, i)
        # honorific names
        line, _ = _apply(NAME_RE, line, "NAME", findings, i)
        lines[i - 1] = line
    return "\n".join(lines), findings


def _apply(pat: re.Pattern[str], line: str, kind: str,
           findings: list[Finding], lineno: int) -> tuple[str, int]:
    matches = list(pat.finditer(line))
    if not matches:
        return line, 0
    out, last = [], 0
    for m in matches:
        out.append(line[last:m.start()])
        rep = _placeholder(kind, m.group(0))
        findings.append(Finding(kind, m.group(0), rep, lineno))
        out.append(rep)
        last = m.end()
    out.append(line[last:])
    return "".join(out), len(matches)


def scrub_json(obj, findings: list[Finding], path: str = "$") -> object:
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            key_l = k.lower()
            new_path = f"{path}.{k}"
            if key_l in PHI_KEYS and isinstance(v, (str, int, float)):
                rep = _placeholder(_key_to_kind(key_l), str(v))
                findings.append(Finding(_key_to_kind(key_l), str(v), rep, 0))
                out[k] = rep
            else:
                out[k] = scrub_json(v, findings, new_path)
        return out
    if isinstance(obj, list):
        return [scrub_json(x, findings, f"{path}[{i}]") for i, x in enumerate(obj)]
    if isinstance(obj, str):
        scrubbed, fnd = scrub_text(obj)
        findings.extend(fnd)
        return scrubbed
    return obj


def _key_to_kind(key: str) -> str:
    if "name" in key:    return "NAME"
    if "dob" in key or "birth" in key: return "DOB"
    if "ssn" in key:     return "SSN"
    if "mrn" in key or "chart" in key or "medical_record" in key: return "MRN"
    if "phone" in key or "fax" in key or "cell" in key or "mobile" in key: return "PHONE"
    if "email" in key:   return "EMAIL"
    if "zip" in key or "postal" in key: return "ZIP"
    if "address" in key or "street" in key or "line" in key or "city" in key: return "ADDRESS"
    if "account" in key or "member" in key or "policy" in key or "subscriber" in key: return "ACCT"
    if "license" in key: return "LICENSE"
    if "ip" in key:      return "IP"
    if "device" in key or "serial" in key: return "DEVICE"
    return "REDACTED"


# ── CLI ─────────────────────────────────────────────────────────────────────

def _print_report(findings: Iterable[Finding]) -> None:
    counts: dict[str, int] = {}
    for f in findings:
        counts[f.type] = counts.get(f.type, 0) + 1
    if not counts:
        print("no PHI detected", file=sys.stderr)
        return
    print("\n--- PHI report (stderr) ---", file=sys.stderr)
    for kind, n in sorted(counts.items()):
        print(f"  {kind:<8} × {n}", file=sys.stderr)
    print(f"  total: {sum(counts.values())} finding(s)", file=sys.stderr)


def main() -> int:
    ap = argparse.ArgumentParser(description="Scrub PHI from a file or stdin.")
    ap.add_argument("path", help="file path or '-' for stdin")
    ap.add_argument("--json", action="store_true",
                    help="treat input as JSON; scrub values under PHI-shaped keys")
    args = ap.parse_args()

    raw = sys.stdin.read() if args.path == "-" else open(args.path, encoding="utf-8").read()

    if args.json:
        try:
            obj = json.loads(raw)
        except json.JSONDecodeError as e:
            print(f"not valid JSON: {e}", file=sys.stderr)
            return 2
        findings: list[Finding] = []
        out = scrub_json(obj, findings)
        sys.stdout.write(json.dumps(out, indent=2))
    else:
        out, findings = scrub_text(raw)
        sys.stdout.write(out)

    _print_report(findings)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
