# Synthea — synthetic patient bundles for clinical evals

[Synthea](https://synthea.mitre.org/) is the standard tool for generating synthetic FHIR R4 patient bundles. Use it (or its frozen output) as the fixture set for every clinical eval — never real patient data.

## Why frozen fixtures matter

If you regenerate Synthea bundles each test run, three things go wrong:
1. Your evals become non-deterministic — scores fluctuate run-over-run from data noise, not model behaviour.
2. Diffing eval results across PRs becomes impossible — was the score change from a model change or a fixture change?
3. Regression detection is blind — a model can quietly get worse and the score change blends into the fixture noise.

**Always commit fixtures to git.** Treat them as code.

## Generating a fixture set

```bash
git clone https://github.com/synthetichealth/synthea && cd synthea
./run_synthea -s 42 -p 100 California
# outputs to output/fhir/*.json
```

Recommended flags:
- `-s 42` — fixed seed (any integer; just keep it stable)
- `-p 100` — population size; 50–200 is plenty for most evals
- A US state — affects demographics, plausible providers

## Picking a fixture set

| Eval task | Suggested set size | Why |
|---|---|---|
| Triage | 50–100 cases | Need urgency-level diversity |
| Extraction | 20–50 cases | Each case is rich; per-case is expensive |
| Summarisation | 20–30 cases | Slow to grade |
| Coding (ICD/SNOMED) | 100–500 cases | Coverage of code space matters |
| Chart Q&A | 50–100 cases × 3–5 Q each | Question diversity > case diversity |

## Hand-built edge cases

Synthea is fine for the bulk of your fixtures but doesn't cover:
- Rare conditions in your specialty (build 5–10 by hand)
- Adversarial cases (intentionally ambiguous symptoms; should produce a refusal)
- Recent guidelines (Synthea lags on updated criteria)
- Multi-language patients (Synthea is English-only)

Build these in a separate `evals/golden/handbuilt/` directory and version them separately.

## Fixture file structure

```
evals/golden/
├── synthea/                    # bulk fixtures
│   ├── 0001_smith_john.json
│   ├── 0002_doe_jane.json
│   └── ...
├── handbuilt/                  # specialty edge cases
│   ├── chest_pain_with_radiation.json
│   ├── ent_severe_pediatric_otitis.json
│   └── ambiguous_dizziness.json
├── annotations/                # gold labels per fixture (separate file!)
│   ├── triage.csv              # fixture_id, expected_urgency, rationale
│   ├── coding.csv              # fixture_id, expected_icd10, expected_snomed
│   └── extraction.json
└── metadata.yaml               # versioning, generation date, seed
```

## Annotations belong in a separate file

Don't embed gold labels in the FHIR bundle itself — it makes the bundle invalid and confuses anyone re-running Synthea. Keep `golden/<fixture>.json` clean and put gold labels in `annotations/`.

## Versioning the fixture set

`metadata.yaml`:
```yaml
synthea_version: 3.2.0
seed: 42
population: 100
state: California
generated: 2026-05-24
handbuilt_count: 18
total_count: 118
```

Bump this when fixtures change. Eval scores tagged with a fixture version are comparable; scores across versions are not.

## Don't ship Synthea bundles to production

Synthea bundles are *plausible* but not always *internally consistent*. They're great for eval; they're not safe to use as production seed data because:
- Medication / condition pairings sometimes don't match real prescribing
- Vital signs may not match the conditions
- Provider identities and locations are real-world strings (US state names, real city names) which can confuse downstream systems expecting unique identifiers
