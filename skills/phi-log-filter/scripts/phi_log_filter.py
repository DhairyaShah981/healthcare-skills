"""
phi_log_filter.py — continuous PHI scrubbing at the logger boundary.

Exports:
  - phi_processor(allowlist) — structlog processor
  - PhiFilter(allowlist)     — stdlib logging.Filter
  - scrub_value(v)           — pure helper

Strategy:
  1. Key-based wholesale replacement for known PHI-shaped keys
  2. Regex sweep on every string VALUE (catches free-text PHI)

Allowlist keys are preserved verbatim (e.g. patient_id, trace_id).
"""
from __future__ import annotations

import logging
import re
from typing import Any, Iterable

# ── PHI-shaped keys (mirror of phi-redact) ────────────────────────────────

PHI_KEYS = {
    "name", "first_name", "last_name", "middle_name", "maiden_name",
    "patient_name", "full_name", "given_name", "family_name",
    "doctor", "doctor_name", "provider", "provider_name",
    "dob", "birth_date", "date_of_birth", "birthdate",
    "ssn", "social_security",
    "mrn", "chart_id", "medical_record_number",
    "phone", "telephone", "cell", "mobile", "fax",
    "email", "email_address",
    "address", "street", "line1", "line2", "city", "zip", "zip_code",
    "account", "account_no", "account_number",
    "member_id", "policy_no", "policy_number", "subscriber_id",
    "ip", "ip_address",
}

REGEX = [
    ("SSN",   re.compile(r"\b\d{3}-\d{2}-\d{4}\b")),
    ("EMAIL", re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")),
    ("PHONE", re.compile(r"\b(?:\+?1[-.\s]?)?\(?[2-9]\d{2}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b")),
    ("DOB",   re.compile(r"\b(19|20)\d{2}-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])\b")),
    ("MRN",   re.compile(r"(?i)\bMRN[:\s#]*[A-Z]?\d{6,10}\b")),
]
YEAR_RE = re.compile(r"(19|20)\d{2}")


def _key_kind(key: str) -> str:
    k = key.lower()
    if "name" in k:       return "NAME"
    if "dob" in k or "birth" in k: return "DOB"
    if "ssn" in k:        return "SSN"
    if "mrn" in k:        return "MRN"
    if "phone" in k or "fax" in k or "cell" in k: return "PHONE"
    if "email" in k:      return "EMAIL"
    if "address" in k or "street" in k or "line" in k or "city" in k: return "ADDRESS"
    if "zip" in k:        return "ZIP"
    if "account" in k or "member" in k or "policy" in k or "subscriber" in k: return "ACCT"
    if "ip" in k:         return "IP"
    return "REDACTED"


def _scrub_string(s: str) -> str:
    for kind, pat in REGEX:
        s = pat.sub(lambda m: _placeholder(kind, m.group(0)), s)
    return s


def _placeholder(kind: str, original: str) -> str:
    if kind == "DOB":
        m = YEAR_RE.search(original)
        return f"[PHI:DOB:year={m.group(0)}]" if m else "[PHI:DOB]"
    return f"[PHI:{kind}]"


def scrub_value(v: Any) -> Any:
    if isinstance(v, str):
        return _scrub_string(v)
    if isinstance(v, dict):
        return scrub_mapping(v, allowlist=set())
    if isinstance(v, list):
        return [scrub_value(x) for x in v]
    return v


def scrub_mapping(d: dict, *, allowlist: Iterable[str]) -> dict:
    out: dict[str, Any] = {}
    al = set(allowlist)
    for k, v in d.items():
        if k in al:
            out[k] = v
        elif k.lower() in PHI_KEYS and isinstance(v, (str, int, float)):
            out[k] = _placeholder(_key_kind(k), str(v))
        else:
            out[k] = scrub_value(v)
    return out


# ── structlog processor ──────────────────────────────────────────────────

def phi_processor(allowlist: Iterable[str] = ()) -> callable:
    al = set(allowlist) | {"event", "level", "timestamp", "logger"}
    def _proc(logger, method_name, event_dict):
        try:
            return scrub_mapping(event_dict, allowlist=al)
        except Exception:
            return {"event": "phi-filter-failure"}
    return _proc


# ── stdlib logging Filter ────────────────────────────────────────────────

class PhiFilter(logging.Filter):
    def __init__(self, allowlist: Iterable[str] = ()) -> None:
        super().__init__()
        self.allowlist = set(allowlist)

    def filter(self, record: logging.LogRecord) -> bool:
        try:
            if isinstance(record.msg, str):
                record.msg = _scrub_string(record.msg)
            if isinstance(record.args, dict):
                record.args = scrub_mapping(record.args, allowlist=self.allowlist)
            elif isinstance(record.args, tuple):
                record.args = tuple(scrub_value(a) for a in record.args)
            extra = getattr(record, "extra", None)
            if isinstance(extra, dict):
                record.extra = scrub_mapping(extra, allowlist=self.allowlist)
        except Exception:
            record.msg = "[phi-filter-failure]"
            record.args = ()
        return True


# ── self-test ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    sample = {
        "event": "patient_loaded",
        "patient_id": "P9981",
        "patient_name": "Maria Hernandez",
        "dob": "1962-04-11",
        "phone": "415-555-0173",
        "note": "Called daughter at j.oconnor@example.com, MRN8829340 confirmed.",
    }
    cleaned = scrub_mapping(sample, allowlist={"event", "patient_id"})
    import json
    print(json.dumps(cleaned, indent=2))
