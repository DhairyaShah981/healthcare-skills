#!/usr/bin/env python3
"""
cds_hook_tester.py — golden-fixture regression for a CDS Hooks 1.0 service.

Layout:
    fixtures/
      discovery.expected.json
      <hook-id>/<case-name>/
        request.json        # POST body
        expected.json       # subset match against the response

Usage:
    python cds_hook_tester.py --service http://localhost:8000 --fixtures cds-tests/
    python cds_hook_tester.py --strict           # WARN → FAIL
    python cds_hook_tester.py --critical-only    # only run severity:critical fixtures
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any


# ── HTTP ──────────────────────────────────────────────────────────────────

def http_get(url: str) -> tuple[int, dict[str, Any]]:
    try:
        with urllib.request.urlopen(url, timeout=10) as r:
            return r.status, json.loads(r.read() or b"{}")
    except urllib.error.HTTPError as e:
        return e.code, {}


def http_post_json(url: str, body: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    data = json.dumps(body).encode()
    req = urllib.request.Request(url, data=data,
                                  headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status, json.loads(r.read() or b"{}")
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read() or b"{}")
        except Exception:
            return e.code, {}


# ── matching ──────────────────────────────────────────────────────────────

def subset_match(expected: Any, actual: Any, path: str = "$") -> list[str]:
    """Return a list of mismatch descriptions; empty list = match."""
    if isinstance(expected, dict):
        if not isinstance(actual, dict):
            return [f"{path}: expected dict, got {type(actual).__name__}"]
        errors: list[str] = []
        for k, ev in expected.items():
            if k not in actual:
                errors.append(f"{path}.{k}: missing")
                continue
            errors.extend(subset_match(ev, actual[k], f"{path}.{k}"))
        return errors
    if isinstance(expected, list):
        if not isinstance(actual, list):
            return [f"{path}: expected list, got {type(actual).__name__}"]
        errors = []
        for i, ev in enumerate(expected):
            if not any(not subset_match(ev, av, f"{path}[?]") for av in actual):
                errors.append(f"{path}[{i}]: no matching element in actual")
        return errors
    if isinstance(expected, str) and expected.startswith("~"):
        needle = expected[1:].lower()
        if isinstance(actual, str) and needle in actual.lower():
            return []
        return [f"{path}: substring '{needle}' not in {actual!r}"]
    if expected != actual:
        return [f"{path}: expected {expected!r}, got {actual!r}"]
    return []


def normalize_cards(resp: dict[str, Any]) -> dict[str, Any]:
    """Strip volatile fields so comparisons are stable."""
    cards = resp.get("cards", [])
    for c in cards:
        for s in c.get("suggestions", []) or []:
            s.pop("uuid", None)
    return resp


# ── runner ────────────────────────────────────────────────────────────────

def run(service: str, fixtures: Path, strict: bool, critical_only: bool) -> int:
    passed = failed = critical_failed = 0
    print("cds-hook-tester")

    # discovery
    disc_expected_path = fixtures / "discovery.expected.json"
    if disc_expected_path.exists():
        code, body = http_get(f"{service}/cds-services")
        expected = json.loads(disc_expected_path.read_text())
        errors = subset_match(expected, body)
        if code != 200 or errors:
            print(f"  discovery                                       FAIL")
            for e in errors:
                print(f"      {e}")
            failed += 1
            if critical_only:
                return 1
        else:
            print(f"  discovery                                       PASS")
            passed += 1

    # per-hook
    for hook_dir in sorted(p for p in fixtures.iterdir() if p.is_dir()):
        hook_id = hook_dir.name
        if hook_id == "discovery":
            continue
        for case_dir in sorted(p for p in hook_dir.iterdir() if p.is_dir()):
            label = f"{hook_id}/{case_dir.name}"
            req_path = case_dir / "request.json"
            exp_path = case_dir / "expected.json"
            if not (req_path.exists() and exp_path.exists()):
                continue
            req = json.loads(req_path.read_text())
            expected = json.loads(exp_path.read_text())
            severity = expected.pop("severity", "normal")
            if critical_only and severity != "critical":
                continue
            code, body = http_post_json(f"{service}/cds-services/{hook_id}", req)
            body = normalize_cards(body)
            errors = subset_match(expected, body)
            if errors or code != 200:
                tag = "FAIL"
                failed += 1
                if severity == "critical":
                    critical_failed += 1
                print(f"  {label:<48} {tag}")
                if code != 200:
                    print(f"      HTTP {code}")
                for e in errors:
                    print(f"      {e}")
            else:
                tag = "PASS"
                passed += 1
                n_cards = len(body.get("cards", []))
                print(f"  {label:<48} {tag}  ({n_cards} card{'s' if n_cards != 1 else ''})")

    print(f"\n{passed}/{passed+failed} fixtures passed"
          + (f" ({critical_failed} critical FAIL)" if critical_failed else ""))
    if failed and (strict or critical_failed):
        return 1
    return 0 if failed == 0 else 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--service", required=True, help="CDS service base URL (no trailing slash)")
    ap.add_argument("--fixtures", type=Path, required=True)
    ap.add_argument("--strict", action="store_true")
    ap.add_argument("--critical-only", action="store_true")
    args = ap.parse_args()
    return run(args.service.rstrip("/"), args.fixtures, args.strict, args.critical_only)


if __name__ == "__main__":
    raise SystemExit(main())
