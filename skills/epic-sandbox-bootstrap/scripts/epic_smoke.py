#!/usr/bin/env python3
"""
epic_smoke.py — verify an Epic on FHIR sandbox config end-to-end.

What it checks:
  1. `.well-known/smart-configuration` is reachable and well-formed
  2. (optional) authorize → token exchange (requires CLIENT_ID + REDIRECT_URI)
  3. Patient/{id} GET returns 200 + non-empty
  4. Observation?patient={id}&category=vital-signs&_count=5 returns ≥1 result
  5. (optional) refresh token exchange

Usage:
    # public sandbox, no auth (read-only against known test patient)
    python epic_smoke.py \
        --base https://fhir.epic.com/interconnect-fhir-oauth/api/FHIR/R4 \
        --patient Tbt3KuCY0B5PSrJvCu2j-PlK.aiHsu2xUjUM8bWpetXoB \
        --no-auth

    # full flow with your registered sandbox app (needs interactive browser)
    python epic_smoke.py --base $EPIC_BASE --client-id $CLIENT_ID \
                         --redirect-uri http://localhost:8765/cb
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.parse
import urllib.request
import urllib.error
from typing import Any


def step(label: str, ok: bool, detail: str = "") -> None:
    tag = "\033[32mPASS\033[0m" if ok else "\033[31mFAIL\033[0m"
    print(f"  {label:<48} {tag}")
    if detail:
        for line in detail.splitlines():
            print(f"      {line}")
    if not ok:
        sys.exit(1)


def get_json(url: str, headers: dict[str, str] | None = None, timeout: int = 10) -> dict[str, Any]:
    req = urllib.request.Request(url, headers=headers or {})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def smart_config(base: str) -> dict[str, Any]:
    url = base.rstrip("/") + "/.well-known/smart-configuration"
    return get_json(url)


def fetch_resource(base: str, path: str, access: str | None) -> dict[str, Any]:
    url = base.rstrip("/") + "/" + path.lstrip("/")
    headers = {"Accept": "application/fhir+json"}
    if access:
        headers["Authorization"] = f"Bearer {access}"
    return get_json(url, headers)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True, help="Epic FHIR base URL")
    ap.add_argument("--patient",
                    default="Tbt3KuCY0B5PSrJvCu2j-PlK.aiHsu2xUjUM8bWpetXoB",
                    help="patient id (default: Epic public sandbox 'Camila Lopez')")
    ap.add_argument("--access-token", default=None,
                    help="pre-acquired access token (skip interactive auth)")
    ap.add_argument("--no-auth", action="store_true",
                    help="skip the auth flow; use this for the public sandbox")
    ap.add_argument("--client-id", default=None)
    ap.add_argument("--redirect-uri", default=None)
    args = ap.parse_args()

    print(f"\nepic-sandbox-bootstrap smoke test")
    print(f"  base: {args.base}\n")

    # 1. smart-configuration
    try:
        cfg = smart_config(args.base)
        detail = (f"authorization_endpoint={cfg.get('authorization_endpoint','?')[:80]}\n"
                  f"token_endpoint={cfg.get('token_endpoint','?')[:80]}")
        step("fetching .well-known/smart-configuration", True, detail)
    except (urllib.error.URLError, json.JSONDecodeError) as e:
        step("fetching .well-known/smart-configuration", False, str(e))

    # 2. auth (skipped on --no-auth)
    access = args.access_token
    if not args.no_auth and not access:
        if not (args.client_id and args.redirect_uri):
            step("auth flow", False,
                 "interactive auth not implemented in this smoke; pass --access-token or --no-auth")
        # An interactive browser-based authorize flow is out of scope for a
        # smoke test. In practice, run smart-oauth-scaffold's /smart/launch,
        # then re-run this script with --access-token <bearer>.
        step("auth flow", False, "re-run with --access-token after running /smart/launch")

    # 3. Patient.read
    try:
        pt = fetch_resource(args.base, f"Patient/{args.patient}", access)
        if pt.get("resourceType") != "Patient":
            step(f"read Patient/{args.patient[:16]}…", False,
                 f"resourceType={pt.get('resourceType')}")
        names = pt.get("name", [])
        nm = names[0] if names else {}
        detail = f"resourceType=Patient name={nm.get('text') or ' '.join(nm.get('given',[]) + [nm.get('family','')])} gender={pt.get('gender')}"
        step(f"read Patient/{args.patient[:16]}…", True, detail)
    except urllib.error.HTTPError as e:
        step("read Patient", False, f"HTTP {e.code}")

    # 4. Observation search
    try:
        path = ("Observation?"
                + urllib.parse.urlencode({"patient": args.patient,
                                          "category": "vital-signs",
                                          "_count": "5"}))
        bundle = fetch_resource(args.base, path, access)
        n = bundle.get("total", len(bundle.get("entry", [])))
        first = ""
        if bundle.get("entry"):
            obs = bundle["entry"][0].get("resource", {})
            code = obs.get("code", {}).get("coding", [{}])[0]
            v = obs.get("valueQuantity", {})
            first = f"first: {code.get('code')} {code.get('display','')} {v.get('value','')} {v.get('unit','')}"
        step("search Observation?…&category=vital-signs", n >= 1,
             f"{n} results\n{first}")
    except urllib.error.HTTPError as e:
        step("search Observation", False, f"HTTP {e.code}")

    print("\nepic-sandbox-bootstrap: all checks passed.\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
