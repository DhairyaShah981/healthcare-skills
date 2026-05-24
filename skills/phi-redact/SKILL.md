---
name: phi-redact
description: |
  Detect and redact PHI (Protected Health Information) from any text, code, log, or diff
  before it leaves the machine. Use when the user asks to "scrub", "redact PHI",
  "de-identify a log", "check this for HIPAA leaks", "is this safe to share",
  or pastes patient-shaped text. Implements HIPAA Safe Harbor 18 identifiers
  (45 CFR §164.514(b)(2)).
when_to_use: |
  Activate when the user:
  - Pastes any text, log, JSON, or stack trace containing patient-shaped data
    (names, DOBs, MRNs, phone numbers, SSNs, addresses, account numbers)
  - Asks "is this safe to share?", "does this leak PHI?", "scrub this", "redact this"
  - Is about to commit a file under `fixtures/`, `tests/`, `examples/`, or `seed/`
  - Asks to review logging, telemetry, or error-reporting code for PHI exposure
  - Mentions sharing logs with a vendor, support, or in a bug report
allowed-tools: [Read, Grep, Edit, Bash, Write]
license: MIT
tags: [hipaa, phi, security, healthcare]
incident: |
  Structlog redaction was documented as policy but never enforced as code; a single
  processor change could silently leak patient names into application logs. PHI in
  a log line is a notifiable breach under the HIPAA Breach Notification Rule
  (45 CFR §164.404) — engineering teams have been forced to send breach letters
  to thousands of patients because of a misconfigured logger.
---

# phi-redact

> Detect and redact PHI from any text, code, log, or diff. Safe Harbor 18 identifiers, with explanations.

## When to use

- The user pastes a log line, JSON blob, fixture, or stack trace containing patient-shaped data.
- The user asks "is this safe to share?", "does this leak PHI?", or "scrub this for me".
- A pre-commit moment: the user is about to commit a file under `fixtures/`, `tests/`, `seed/`, `examples/`.
- A logging review: the user wants to audit `structlog`, `winston`, `pino`, or `loguru` config for PHI leakage.

## How it works

1. **Identify the source surface.** Determine what the user gave you: raw text, a file path, a diff, or a directory. If a directory, scan recursively but ignore `node_modules/`, `.venv/`, `dist/`, and `.git/`.

2. **Run the layered detector.** PHI hides in three layers — run all three:
   - **Structural** — JSON / YAML keys named `name`, `firstName`, `lastName`, `patient_name`, `dob`, `birthDate`, `ssn`, `mrn`, `phone`, `email`, `address`, `zip`, `account`, `member_id`.
   - **Regex** — apply the patterns in [`references/regex-patterns.md`](./references/regex-patterns.md). SSN (`\b\d{3}-\d{2}-\d{4}\b`), phone (`\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b`), email, MRN-like (`\bMRN[:\s]*\d{6,10}\b`), DOB (`\b\d{4}-\d{2}-\d{2}\b`), full ZIP (`\b\d{5}(?:-\d{4})?\b`).
   - **Named entities** — for free-text fields, flag capitalized two-word sequences that aren't in a known clinical-vocabulary allowlist (drug names, anatomy, diagnoses). When `scripts/phi_scrubber.py` is available, run it for higher recall.

3. **Replace, don't delete.** Substitute each finding with a typed placeholder so the result still parses:
   - Names → `[NAME]`
   - DOB → `[DOB]`
   - SSN → `[SSN]`
   - MRN → `[MRN]`
   - Phone → `[PHONE]`
   - Email → `[EMAIL]`
   - Address → `[ADDRESS]`
   - Account / member ID → `[ACCT]`
   - Any other Safe Harbor 18 identifier → `[REDACTED:<type>]`

4. **Apply Safe Harbor §164.514(b)(2)(i)(C) — age aggregation.** Ages over 89 must be replaced with `90+`. Granular dates (anything more specific than year) must be reduced to year for the indirect-identifiers risk threshold.

5. **Report**, don't just rewrite. Always return:
   - The redacted text
   - A table: `[FINDING_TYPE] line:col original → replacement` (truncate originals to 8 chars)
   - The count of redactions per category
   - A confidence note on any free-text that couldn't be classified

6. **Refuse mock-PHI generation that looks real.** If asked to "make up fake PHI that looks realistic", point the user at the `synthea-fixture` skill instead — synthetic data should be obviously synthetic.

## Example

**Before**
```
2026-05-24T08:14:22Z ERROR app.appointments: failed to confirm appointment
  patient_name="Maria Hernandez" dob="1962-04-11" mrn="MRN8829340"
  phone="415-555-0173" reason="Insurance card photo uploaded was unreadable"
  appointment_id="apt_8821" doctor="Dr. Sanjay Patel"
```

**After**
```
2026-05-24T08:14:22Z ERROR app.appointments: failed to confirm appointment
  patient_name="[NAME]" dob="[DOB:year=1962]" mrn="[MRN]"
  phone="[PHONE]" reason="Insurance card photo uploaded was unreadable"
  appointment_id="apt_8821" doctor="[NAME]"

Redactions:
| type    | line:col   | original   | replacement      |
|---------|-----------|------------|------------------|
| NAME    | 2:18      | Maria…     | [NAME]           |
| DOB     | 2:42      | 1962-04-11 | [DOB:year=1962]  |
| MRN     | 2:62      | MRN88293…  | [MRN]            |
| PHONE   | 3:9       | 415-555-…  | [PHONE]          |
| NAME    | 4:32      | Dr. Sanj…  | [NAME]           |

5 findings across 2 lines.
```

## Edge cases

- **Free-text inside JSON string fields.** `{"note": "Called Maria's daughter about refill"}` — the structural pass misses this because the key (`note`) isn't a known PHI key. Always run the regex+NER pass over string *values* even when the key is benign.
- **Date granularity is itself a PHI signal.** "1962-04-11" leaks more than "1962". Reduce to year for free-text and review fields; keep month-day only for dates that drive scheduling logic (and even then, never log them).
- **Doctor / provider names are still PHI in context.** A treating provider's name combined with a date is itself identifying. Redact provider names by default.
- **MRN formats vary.** Some EHRs use letters (`A8829340`), some use checksums, some use plain integers ≥7 digits. Treat any 7–10 digit number in a key-like context (`mrn`, `chart_id`, `patient_id`) as PHI.
- **ZIP3 vs ZIP5.** Safe Harbor allows the first three digits of a ZIP if the population is ≥20,000; default to redacting the full ZIP unless the user explicitly asks to keep ZIP3.
- **Refuse to "round-trip" real PHI** — if the user asks "what was the original name?", refuse. The skill is one-way.

## Run the reference scrubber

A reference Python implementation lives at [`scripts/phi_scrubber.py`](./scripts/phi_scrubber.py). It works offline (regex + structural) and optionally upgrades to [Presidio](https://github.com/microsoft/presidio) if installed.

```bash
# scrub a file
python skills/phi-redact/scripts/phi_scrubber.py path/to/log.txt

# scrub from stdin
cat app.log | python skills/phi-redact/scripts/phi_scrubber.py -
```

## References

- HIPAA Safe Harbor — 45 CFR §164.514(b)(2): [`references/safe-harbor-18.md`](./references/safe-harbor-18.md)
- HIPAA Breach Notification Rule — 45 CFR §164.404
- Regex catalogue: [`references/regex-patterns.md`](./references/regex-patterns.md)
- [Microsoft Presidio](https://github.com/microsoft/presidio) — open-source PII detection
- [HITRUST de-identification framework](https://hitrustalliance.net/)
- Example before / after: [`examples/before.log`](./examples/before.log) / [`examples/after.log`](./examples/after.log)
