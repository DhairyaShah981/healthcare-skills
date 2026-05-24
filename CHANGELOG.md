# Changelog

All notable changes to healthcare-skills are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] — 2026-05-24

### Added — 17 skills

**Tier 0 — Universal**
- `phi-redact` — detect & redact PHI (Safe Harbor 18) from any text/code/log/diff
- `fhir-bundle` — generate valid FHIR R4 bundles from a clinical description
- `hipaa-review` — review a diff for HIPAA Security Rule violations

**Tier 1 — Core**
- `clinical-eval` — eval suites for clinical AI outputs (Synthea fixtures + LLM-as-judge)
- `audit-trail` — `@audited()` decorator + AuditEvent table for patient-data functions
- `consent-gate` — patient consent verification gate for FastAPI / Express endpoints
- `deid-vault` — reversible HMAC pseudonymization + leak scanner
- `hl7-transform` — HL7v2 (ADT / ORU / SIU) ↔ FHIR R4 conversion
- `cds-hook` — CDS Hooks 1.0 service scaffolding
- `icd-snomed-map` — ICD-10 / SNOMED-CT / CPT / LOINC / RxNorm crosswalk

**Tier 2 — From real production incidents**
- `voice-agent-lint` — 17 production-failure rules for Retell / Vapi voice-agent JSONs
- `alembic-guard` — enforce ≤32-char revision IDs + linear chain
- `jsonb-pydantic-pair` — every JSONB column needs a matching Pydantic schema
- `tenant-rls-guard` — detect missing `client_id` predicates in multi-tenant queries
- `async-blocking-lint` — flag `requests` / `urllib` calls inside `async def`
- `secrets-placeholder` — placeholder-token + Secret Manager substitution
- `synthea-fixture` — frozen FHIR test bundles for deterministic evals

### Tooling
- `install.sh` — one-command install for Claude Code, Cursor, Codex CLI, Gemini CLI
- `scripts/validate.sh` — frontmatter linter, run in CI on every PR
- `.github/workflows/validate-skills.yml` — CI gate

[Unreleased]: https://github.com/DhairyaShah981/healthcare-skills/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/DhairyaShah981/healthcare-skills/releases/tag/v0.1.0
