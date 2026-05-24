---
name: clinical-eval
description: |
  Scaffold a reproducible eval suite for clinical AI outputs (triage, summarisation,
  extraction, chart-question-answering) with frozen Synthea fixtures and rubric-based
  LLM-as-judge scoring. Use when the user asks to "evaluate the model", "build an
  eval", "regression-test the prompt", "score clinical accuracy", or mentions that
  a prompt / model upgrade landed without an eval gate.
when_to_use: |
  Activate when the user:
  - Asks to evaluate a clinical AI feature (triage, summarisation, extraction)
  - Wants a regression gate before a prompt or model change ships
  - Mentions "scoring", "rubric", "judge model", or "ground truth" for clinical outputs
  - Is about to upgrade a model (Sonnet → Opus, GPT-4 → GPT-5) on a healthcare path
  - Has Synthea bundles or frozen test fixtures and needs an eval harness around them
allowed-tools: [Read, Write, Edit, Bash]
license: MIT
tags: [eval, healthcare, llm, regression, fhir]
incident: |
  Voice-agent and OCR-extractor prompts drift silently when models update.
  Without a CI-gated eval suite, the first signal of regression is a clinician
  noticing a wrong medication on a chart — weeks after the change shipped.
  This skill encodes the eval-first pattern that fhir-mcp's `/evals` directory
  uses: pinned judge model, frozen fixtures, rubric-based scoring, CI gate.
---

# clinical-eval

> Build the eval suite *before* the next prompt change ships. Frozen Synthea fixtures, pinned judge model, CI-gated.

## When to use

- The user is about to upgrade a model or rewrite a prompt for a clinical AI feature.
- The user asks "how do I know if the model got worse?" or "what's our regression test?"
- The user has a feature that does triage / summarisation / extraction / chart-Q&A and no eval suite exists.
- The user mentions Synthea bundles, golden fixtures, or "ground truth" for clinical outputs.

## How it works

1. **Identify the task.** Ask the user (or infer from code) which clinical task is being evaluated. Common ones:
   - **Triage** — given a chief complaint, return urgency level
   - **Extraction** — given a clinical note, return structured FHIR resources
   - **Summarisation** — given an encounter, return a SOAP-style summary
   - **Chart Q&A** — given a patient bundle + question, return an answer
   - **Coding** — given a description, return an ICD-10 / SNOMED code

2. **Pick the dataset.** Default to **Synthea** synthetic patient bundles. Either:
   - Pull from `synthea-fixture` skill (frozen, version-controlled)
   - Generate fresh with `synthea --population 100 --seed 42`
   Never use real patient data in an eval suite.

3. **Define the rubric.** Every eval needs a structured score, not just "good/bad". For each task type, the rubric maps to a clinical concern:
   - Triage: accuracy of urgency level + safety (false-negative emergencies are catastrophic)
   - Extraction: precision + recall on each resource type, with PHI-leakage as a separate dimension
   - Summarisation: completeness, factual accuracy, omission of dangerous info
   - Chart Q&A: factual accuracy + appropriate refusal ("I don't see that in the record")

4. **Pin the judge model.** When using LLM-as-judge, pin the version (`claude-sonnet-4-6`, `gpt-4o-2024-08-06`). A judge that drifts is worse than no judge.

5. **Scaffold the harness.** Generate a directory like:
   ```
   evals/
   ├── conftest.py          # pinned judge model, fixture loading, audit isolation
   ├── golden/              # frozen Synthea bundles (.json)
   ├── rubrics/
   │   ├── triage.yaml
   │   └── extraction.yaml
   ├── judge/
   │   └── triage_prompt.md
   ├── test_triage.py
   ├── test_extraction.py
   └── report.py             # generate per-run scoreboard
   ```

6. **Wire the CI gate.** Add a GitHub Actions / equivalent step that runs the eval on PRs that touch the prompt / model code. Fail the build if score drops below a threshold (e.g. 0.85 for triage, 0.90 for extraction).

7. **Track scores over time.** Each run appends to `evals/scoreboard.jsonl`. This lets the team see drift over weeks even when individual PRs all pass.

## Example

**Input (user prompt):**
> *We have a triage prompt in `app/llm/triage.py`. We're about to swap from Sonnet 4.6 to Opus 4.7. Set up an eval suite.*

**Output (abbreviated — full files in `examples/`):**

`evals/rubrics/triage.yaml`:
```yaml
task: triage
score_dimensions:
  - name: urgency_match
    weight: 0.4
    description: |
      Does the model assign the same urgency level (EMERGENT, URGENT, ROUTINE, SELF-CARE)
      as the gold annotation?
  - name: safety
    weight: 0.4
    description: |
      Does the model avoid under-triaging? A false-negative on an EMERGENT case
      is catastrophic. Score 0 if model returns ROUTINE or SELF-CARE for an
      EMERGENT gold case.
  - name: rationale_quality
    weight: 0.2
    description: |
      Does the model cite the symptom or vital sign that drove its decision,
      and is the citation accurate against the patient bundle?
threshold:
  pass: 0.85
  alert: 0.75
```

`evals/test_triage.py`:
```python
import pytest
from app.llm.triage import classify
from evals.judge import score_with_rubric

CASES = [
    ("chest_pain_with_radiation.json", "EMERGENT"),
    ("ear_pain_3_days.json",          "ROUTINE"),
    ("sore_throat_mild.json",         "SELF-CARE"),
    ("severe_headache_neuro_signs.json", "EMERGENT"),
    # ... 50 more
]

@pytest.mark.parametrize("fixture,expected", CASES)
def test_triage(fixture, expected):
    bundle = load_fixture(fixture)
    actual = classify(bundle)
    result = score_with_rubric("triage", actual=actual, expected=expected, bundle=bundle)
    assert result.total >= 0.85, result.explain()
```

`.github/workflows/clinical-eval.yml`:
```yaml
name: clinical-eval
on:
  pull_request:
    paths:
      - 'app/llm/**'
      - 'prompts/**'
      - 'evals/**'
jobs:
  triage:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: pip install -e .
      - env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
          JUDGE_MODEL: claude-sonnet-4-6
        run: pytest evals/test_triage.py -v --tb=short
```

## Edge cases

- **Don't grade your own homework.** If the model under test is `gpt-4o`, the judge should be a *different* model family (Claude, Gemini) to avoid same-family biases.
- **Determinism matters.** Set `temperature=0` and seed everything you can. A non-deterministic eval is noise.
- **Safety dimensions dominate.** A 95% accurate triage that fails on the 5% true emergencies is worse than 80% across the board. Weight safety high in the rubric.
- **Synthea has gaps.** Synthea doesn't model rare diseases well, doesn't include all specialties, and can produce internally inconsistent bundles. Add 10–20 hand-built fixtures for your specialty's edge cases.
- **LLM judges drift with new versions.** Pin by date-stamped model ID, not by alias.
- **Track the rubric, not just the score.** Sometimes the model improves on one dimension and regresses on another and the total looks unchanged. Show per-dimension scores in the report.
- **Don't include PHI in fixtures.** Even for "internal-only" evals. Synthetic data only.

## References

- Synthea synthetic patient generator: <https://synthea.mitre.org/>
- Inspect AI (Anthropic's eval framework): <https://inspect.ai-safety-institute.org.uk/>
- BIG-Bench Hard rubrics for inspiration: <https://github.com/google/BIG-bench>
- [`examples/triage-eval.yaml`](./examples/triage-eval.yaml)
- [`examples/deid-leakage-eval.yaml`](./examples/deid-leakage-eval.yaml)
- [`references/synthea-bundles.md`](./references/synthea-bundles.md)
