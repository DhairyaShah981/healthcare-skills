---
name: cds-hook-tester
description: |
  Test a CDS Hooks 1.0 service against a directory of golden request /
  expected-card pairs. Verifies discovery endpoint, fires each hook with a
  canned context + prefetch, diffs the Cards returned against an expected
  shape, and reports per-fixture PASS / FAIL. Use when the user builds a
  CDS Hooks service (see `cds-hook` skill) and asks how to test it, or
  hits regressions when changing the rules.
when_to_use: |
  Activate when the user:
  - Built a CDS Hooks service (composed with the `cds-hook` skill) and
    needs a test harness
  - Asks "how do I regression-test my DDI rules?"
  - Wants golden fixtures for patient-view / medication-prescribe / order-select
  - Is wiring up CI for a CDS Hooks service
  - Mentions Cards, suggestions, links — and wants to assert on them
allowed-tools: [Read, Write, Edit, Bash]
license: MIT
tags: [cds, fhir, healthcare, testing, eval]
incident: |
  CDS Hooks services drift silently: a rule registry edit changes whether
  a Card fires for the canonical "aspirin + warfarin" case, and the next
  clinician at the next site sees no warning. Without a golden-fixture
  regression suite, the only way to detect this is in production. This
  skill provides the canonical test harness: a directory of request +
  expected-card JSON pairs, a runner that diffs actual vs expected, and
  a CI gate.
---

# cds-hook-tester

> Golden-fixture regression for a CDS Hooks service. Detect rule drift before clinicians do.

## When to use

- The user built a CDS Hooks service and asks how to test it.
- The user is wiring CI for a CDS service.
- The user wants confidence that "the canonical DDI cases still fire."

## How it works

1. **Lay out fixtures.**
   ```
   cds-tests/
   ├── discovery.expected.json           # what GET /cds-services should return
   ├── medication-prescribe/
   │   ├── 001_aspirin_warfarin/
   │   │   ├── request.json              # POST body to /cds-services/{id}
   │   │   └── expected.json             # expected Cards (subset match)
   │   ├── 002_amoxicillin_pen_allergy/
   │   │   ├── request.json
   │   │   └── expected.json
   │   └── 003_no_interaction_noop/
   │       ├── request.json
   │       └── expected.json
   ├── patient-view/
   │   ├── 001_smoker_counsel/...
   │   └── 002_flu_vax_due/...
   └── order-select/
       └── ...
   ```

2. **Discovery check.** `GET /cds-services` against the service. Assert the response shape matches `discovery.expected.json` (services list, hooks, prefetch declarations).

3. **Per-fixture hook check.**
   - `POST /cds-services/{hook-id}` with `request.json` as body
   - Receive response (one or more Cards)
   - **Subset match** against `expected.json` — every assertion in expected must be satisfied in actual; actual may have additional fields (forward-compatible)

4. **Subset-match rules** (sane defaults):
   - String fields: exact match unless prefixed with `~` for substring (`"~bleeding"` matches anywhere)
   - Array fields: every element in expected must have a matching element in actual (order-insensitive)
   - `indicator`, `summary` are required to match; `detail` is optional unless asserted
   - `suggestions[].uuid` is normalized away (UUIDs change run-over-run)

5. **Severity gate.** Some Cards are safety-critical; tag fixtures as `severity: critical` and fail loud if expected critical Cards don't appear in actual.

6. **CI integration.** Wire as a pytest / Vitest suite or a standalone runner. Run on every PR that touches the CDS service.

## Example

`cds-tests/medication-prescribe/001_aspirin_warfarin/request.json`:
```json
{
  "hook": "medication-prescribe",
  "hookInstance": "test-001",
  "context": {
    "patientId": "P-TEST",
    "userId": "Practitioner/TEST",
    "medications": {
      "resourceType": "Bundle",
      "entry": [{"resource": {"resourceType": "MedicationRequest",
        "medicationCodeableConcept": {"coding": [
          {"system": "http://www.nlm.nih.gov/research/umls/rxnorm",
           "code": "1191", "display": "aspirin"}
        ]}}}]
    }
  },
  "prefetch": {
    "active_meds": {"resourceType": "Bundle", "entry": [{"resource": {
      "resourceType": "MedicationRequest",
      "medicationCodeableConcept": {"coding": [
        {"system": "http://www.nlm.nih.gov/research/umls/rxnorm",
         "code": "11289", "display": "warfarin"}
      ]}}}]}
  }
}
```

`cds-tests/medication-prescribe/001_aspirin_warfarin/expected.json`:
```json
{
  "severity": "critical",
  "cards": [{
    "summary": "~aspirin",
    "indicator": "warning",
    "detail": "~bleeding"
  }]
}
```

Run:
```bash
python scripts/cds_hook_tester.py \
    --service http://localhost:8000 \
    --fixtures cds-tests/ \
    --strict
```

Output:
```
cds-hook-tester
  discovery                                       PASS
  medication-prescribe/001_aspirin_warfarin       PASS  (1 card matched)
  medication-prescribe/002_amoxicillin_pen_allergy PASS (1 card matched)
  medication-prescribe/003_no_interaction_noop    PASS  (0 cards as expected)
  patient-view/001_smoker_counsel                 PASS  (1 card matched)
  patient-view/002_flu_vax_due                    FAIL
      expected card with summary ~"influenza vaccination" not present
      actual cards: ["Pneumococcal vaccination due"]

5/6 fixtures passed (1 critical FAIL)
```

## Edge cases

- **Non-deterministic Cards.** Some services include timestamps or UUIDs in Cards; the runner strips known volatile fields (`uuid`, `hookInstance`-echo) before comparison.
- **Card ordering.** CDS Hooks doesn't guarantee Card order; comparison is order-insensitive.
- **Suggestions FHIR resources.** A suggestion's `actions[].resource` is FHIR-shaped; deep-compare with the `fhir-bundle` skill's structural rules (no PHI, valid resource type).
- **Empty-Cards expectations.** A fixture with `"cards": []` expects the service to return zero Cards; useful for noop / negative cases.
- **CRD / DTR specifics.** Da Vinci CRD `order-select` Cards include payer / coverage references; assert those exist but allow IDs to vary by deployment.
- **Don't include real PHI in fixtures.** Use synthetic patient IDs (`P-TEST`) and synthetic medication identifiers.

## References

- CDS Hooks 1.0 spec: <https://cds-hooks.hl7.org/1.0/>
- [`scripts/cds_hook_tester.py`](./scripts/cds_hook_tester.py) — runnable harness
- [`examples/fixtures/`](./examples/fixtures/) — sample request + expected pairs
- Compose with: `cds-hook` (the service this skill tests), `synthea-fixture` (patient bundles)
