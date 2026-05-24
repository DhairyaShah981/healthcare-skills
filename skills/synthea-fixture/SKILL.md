---
name: synthea-fixture
description: |
  Generate frozen, version-controlled Synthea-style FHIR R4 patient bundles
  for deterministic eval and integration tests. Use when the user asks to
  "create a test patient", "generate fixtures", "build synthetic data for
  evals", "I need a bundle for type-2 diabetic with hypertension", or wants
  to seed a dev EHR.
when_to_use: |
  Activate when the user:
  - Needs deterministic FHIR fixtures for tests / evals
  - Asks to generate a synthetic patient with specific conditions
  - Is building the dataset for the `clinical-eval` skill
  - Wants to seed a development EHR or test harness
  - Mentions Synthea, ground-truth annotations, or frozen fixtures
allowed-tools: [Read, Write, Edit, Bash]
license: MIT
tags: [eval, fhir, synthetic, healthcare, testing]
incident: |
  Engineers regenerating Synthea bundles on every test run caused eval
  scores to flutter run-over-run from data noise rather than model behaviour.
  Worse, when a developer regenerated the population to add a new case,
  every existing test's gold annotations needed re-mapping. This skill
  encodes the "fixtures as code" pattern: commit them, version them, treat
  them as the eval contract.
---

# synthea-fixture

> Frozen FHIR R4 fixtures for deterministic clinical evals. Treat fixtures as code.

## When to use

- The user needs FHIR bundles for the `clinical-eval` harness.
- The user asks for a synthetic patient with specific conditions ("65-year-old male, T2DM + HTN, on metformin + lisinopril").
- The user is seeding a dev EHR / integration test environment.
- The user mentions Synthea, frozen fixtures, golden datasets, or eval ground-truth.

## How it works

1. **Decide bulk vs hand-built.** Bulk (50–200 cases) via Synthea is right for broad coverage. Hand-built (5–20 cases) is right for specialty edge cases, adversarial cases, recent guidelines, multi-language.

2. **For bulk: run Synthea with fixed seed.**
   ```bash
   git clone https://github.com/synthetichealth/synthea
   cd synthea
   ./run_synthea -s 42 -p 100 California        # 100 patients, seeded
   # output: output/fhir/*.json
   ```
   Always pass `-s <integer>`. The seed is the entire reproducibility contract.

3. **For hand-built: use the generator script** (`scripts/build_fixture.py`):
   ```bash
   python scripts/build_fixture.py \
     --age 65 --sex male \
     --condition hypertension --condition type2-diabetes \
     --medication lisinopril --medication metformin \
     --vital bp=142/91 --vital hr=78 --vital bmi=28.4 \
     --out evals/golden/handbuilt/h001_male_65_htn_dm.json
   ```

4. **Treat fixtures as code.**
   - Commit them to git.
   - Annotations live in a *separate* file (`annotations/triage.csv`, etc.) — don't pollute the FHIR bundle.
   - Version the dataset in `metadata.yaml`:
     ```yaml
     synthea_version: 3.2.0
     seed: 42
     population: 100
     state: California
     generated: 2026-05-24
     handbuilt_count: 18
     total_count: 118
     ```

5. **Never include real PHI.** All fixture names should look obviously fake (`John Synthea`, `Jane Doe`, `Patient_001`). All dates should be year-only or year+month where possible.

6. **Add edge-case fixtures by hand.** Synthea is great for "average" cases but misses:
   - Rare diseases in your specialty
   - Adversarial / ambiguous symptom presentations
   - Multi-language patients
   - Recently-updated guidelines
   - Patients with conflicting clinical signals (a "refusal" target for chart Q&A)

7. **Snapshot the fixture set when stable.** When the eval scores stabilize on a fixture set, tag the directory in git (`fixtures-v1.0`). Future regressions are then traceable to either a model change or a fixture-version bump.

## Example

**Input:**
> *Build a fixture: 65-year-old male, hypertension and type-2 diabetes, current meds lisinopril + metformin, vitals BP 142/91, HR 78, BMI 28.4, HbA1c 7.2%.*

**Output:** `evals/golden/handbuilt/h001_male_65_htn_dm.json` — a FHIR R4 Bundle with:
- Patient (year-of-birth 1960, gender male, MRN `SYN-001`)
- Encounter (ambulatory, today)
- Condition × 2 (I10 + E11.9)
- MedicationRequest × 2 (RxNorm 314076 lisinopril, 860975 metformin)
- Observation × 4 (BP, HR, BMI, HbA1c — with `valueQuantity` + UCUM)

Plus a one-line entry in `evals/golden/handbuilt/_manifest.csv`:
```
h001_male_65_htn_dm.json, "M, 65, HTN+T2DM, on lisinopril+metformin, BP elevated, A1c 7.2"
```

A working generator and three example fixtures are in [`scripts/build_fixture.py`](./scripts/build_fixture.py) and [`examples/`](./examples/).

## Edge cases

- **Don't bake gold labels into the FHIR bundle.** The bundle is the *input* to the model; the label is the gold answer. Keep them separate so re-running Synthea doesn't invalidate labels.
- **Synthea isn't internally consistent.** Generated bundles sometimes have implausible combos (a medication contra-indicated for the listed condition). Audit your fixture set by hand for the critical evals.
- **Demographic representation.** Synthea models US-state demographics; if your patient population is different, supplement with hand-built fixtures representative of your real users.
- **Specialty depth.** Synthea is broad and shallow. For ENT / cardio / GI / oncology specialty-deep evals, build hand fixtures from sample charts (de-identified, public, or fully synthetic).
- **Bundle size.** Fixtures should be small enough to read at a glance — 5–10 resources, not 200. If you need volume, sample from a larger pool at test time.
- **PHI hygiene.** Even synthetic data can drift toward looking real. Run `phi-redact` over fixtures before committing, just in case. Look for accidentally-real-looking names, dates, or addresses.
- **Don't ship Synthea bundles as prod seed data.** Synthea is for *eval*, not production. The data isn't internally consistent enough for downstream systems to rely on.

## References

- Synthea: <https://synthea.mitre.org/>
- Synthea on GitHub: <https://github.com/synthetichealth/synthea>
- FHIR R4 Bundle: <https://www.hl7.org/fhir/R4/bundle.html>
- US Core profiles: see `fhir-bundle` skill's references
- [`scripts/build_fixture.py`](./scripts/build_fixture.py) — generator
- [`examples/h001_male_65_htn_dm.json`](./examples/h001_male_65_htn_dm.json)
- [`examples/_manifest.csv`](./examples/_manifest.csv)
- See also `clinical-eval` (consumes these fixtures) and `phi-redact` (PHI guardrail)
