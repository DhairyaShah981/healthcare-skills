# Changelog

All notable changes to healthcare-skills are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.3.0] — 2026-05-24

### Added — 2 more skills (27 total)

- `epic-sandbox-bootstrap` — 12-step Epic on FHIR sandbox onboarding checklist + runnable smoke-test exercising Patient.read / Observation.search / refresh
- `cds-hook-tester` — golden-fixture regression for a CDS Hooks 1.0 service: discovery check + per-hook subset-match runner

### Added — CLI

- `bin/healthcare-skills.js` — Node, zero-dep, `npx`-installable
- Subcommands: `list`, `info`, `add`, `add-all`, `search`, `tags`, `doctor`
- Flags: `--ide`, `--skills-root`, `--dry-run`, `--json`
- `tests/cli.bats` — 43-assertion bash smoke harness, green in CI

### Added — TypeScript reference impls

- `ts/phi-log-filter` — pino + winston redactor (4 smoke tests)
- `ts/webhook-verify` — Retell / Vapi / GitHub / Stripe / Slack / Twilio / Segment / generic (9 smoke tests)
- `ts/audit-trail` — `audited()` wrapper + Express middleware (3 smoke tests)
- `ts/consent-gate` — SMART scope + FHIR Consent middleware (10 smoke tests)
- All four use `node --test` (no dependencies)

### Added — Web discovery site

- `docs/site/` — zero-framework static site (HTML + CSS + vanilla JS)
- `scripts/build_site.js` generates `skills.json` from frontmatter
- Search across name / description / tags; filter by tag; tier pills
- GitHub Pages workflow auto-deploys on every push touching skills/

### CI

- `validate-skills.yml` expanded with `ts-smoke`, `cli-smoke`, and `site-build` jobs
- `pages.yml` builds and deploys the site

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

## [0.1.0] — 2026-05-24

### Added — 17 skills

**Tier 0 — Universal**
- `phi-redact` — detect & redact PHI (Safe Harbor 18) from any text/code/log/diff
- `fhir-bundle` — generate valid FHIR R4 bundles from a clinical description
- `hipaa-review` — review a diff for HIPAA Security Rule violations

**Tier 1 — Core**
- `clinical-eval`, `audit-trail`, `consent-gate`, `deid-vault`, `hl7-transform`, `cds-hook`, `icd-snomed-map`

**Tier 2 — From real production incidents**
- `voice-agent-lint`, `alembic-guard`, `jsonb-pydantic-pair`, `tenant-rls-guard`, `async-blocking-lint`, `secrets-placeholder`, `synthea-fixture`

### Tooling
- `install.sh` — one-command install for Claude Code, Cursor, Codex CLI, Gemini CLI
- `scripts/validate.sh` — frontmatter linter, run in CI on every PR
- `.github/workflows/validate-skills.yml` — CI gate

[Unreleased]: https://github.com/DhairyaShah981/healthcare-skills/compare/v0.3.0...HEAD
[0.3.0]: https://github.com/DhairyaShah981/healthcare-skills/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/DhairyaShah981/healthcare-skills/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/DhairyaShah981/healthcare-skills/releases/tag/v0.1.0
