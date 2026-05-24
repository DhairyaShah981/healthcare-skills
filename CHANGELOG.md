# Changelog

All notable changes to healthcare-skills are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.0] — 2026-05-24

### Added — 8 more skills (25 total)

**Tier 3 — v0.2 additions**
- `smart-oauth-scaffold` — SMART on FHIR app launch + Fernet-encrypted token storage + refresh-on-401 for Epic / Cerner / Athena / Allscripts / Meditech
- `prior-auth-fhir` — Da Vinci PAS / CRD / DTR builders (`CoverageEligibilityRequest`, PAS `Claim`, `QuestionnaireResponse`)
- `route-fatness` — lint fat route handlers (line count, external calls, DB queries, branch depth) and suggest service-layer extraction
- `clinic-config-extract` — find hardcoded clinic / tenant slugs across the codebase and refactor to a single YAML config
- `migration-bisect` — `git bisect` for Alembic migrations; ephemeral DB + per-revision smoke probe
- `webhook-verify` — constant-time HMAC verification for Retell / Vapi / Twilio / Stripe / Slack / GitHub / Segment webhooks with replay-window enforcement
- `phi-log-filter` — continuous PHI-scrubbing processor for structlog / Python logging / loguru / winston / pino
- `specialty-scaffold` — scaffold a new clinical specialty (cardiology / ENT / GI / derm / peds / women's health / psychiatry / endocrine) on top of a shared base with overrides only

### Tooling
- README skill index extended to include Tier 3
- Reference implementations for each skill: SMART OAuth (FastAPI), HMAC verifiers (7 providers), structlog PHI processor, route-fatness AST linter, slug scanner, migration bisect harness, specialty scaffolder

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

[Unreleased]: https://github.com/DhairyaShah981/healthcare-skills/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/DhairyaShah981/healthcare-skills/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/DhairyaShah981/healthcare-skills/releases/tag/v0.1.0
