# healthcare-skills — PRD

## Vision

Healthcare engineering carries an unusually high "you should have known" cost: a missing `client_id` predicate is a cross-tenant breach; a `Column(JSONB)` without a Pydantic wrapper is a runtime `KeyError` in production; an unredacted patient name in a log line is a HIPAA notification event. These traps are well-known to engineers who've been burned by them, and almost entirely invisible to engineers who haven't.

**healthcare-skills encodes that hard-won institutional knowledge as portable, AI-pair-friendly skills.** Drop the pack into Claude Code (or Cursor, Codex CLI, Gemini CLI), and the AI will know to reach for `phi-redact` before paste-bin sharing a log, `tenant-rls-guard` before merging a query, `alembic-guard` before naming a migration.

## Goals (v0.1)

1. **17 skills shipped**, each tied to a real documented production incident.
2. **<60-second install** from `git clone` to working skill in any of four IDEs.
3. **Zero-key default** — every skill works offline; online integrations are strictly opt-in.
4. **PR-reviewable** — every skill is a single SKILL.md a junior eng can read and edit.
5. **Cross-IDE parity** — same skill body works in Claude Code, Cursor, Codex CLI, Gemini CLI.

## Non-goals (v0.1)

- A FHIR client library — skills *teach* the agent to build bundles; they don't ship a runtime.
- A HIPAA compliance certification — these are engineering aids, not a substitute for legal review.
- An IDE extension — we ship plain text files; the host IDE does the loading.
- Multi-language ports — Python references first; TypeScript/Go snippets where they add value.

## Success metrics

- **Adoption:** 50+ stars on GitHub within 30 days of launch (signal: the README pitch lands).
- **Reuse:** ≥3 community PRs adding new skills within 60 days (signal: the format is approachable).
- **Quality:** every skill has a before/after example a healthcare engineer recognizes (signal: real-world fit).

## Skill tiering (build order)

**Tier 0 — Universal:** `phi-redact`, `fhir-bundle`, `hipaa-review`. Three skills every healthtech eng will install immediately. Polished hardest; first in the README.

**Tier 1 — Core healthcare engineering:** `clinical-eval`, `audit-trail`, `consent-gate`, `deid-vault`, `hl7-transform`, `cds-hook`, `icd-snomed-map`. The seven skills that map directly to the original 10-skill brief.

**Tier 2 — Incident-driven additions:** `voice-agent-lint`, `alembic-guard`, `jsonb-pydantic-pair`, `tenant-rls-guard`, `async-blocking-lint`, `secrets-placeholder`, `synthea-fixture`. Sourced from documented production incidents on the Trifetch platform — these are the secret weapon and the social-proof signal.

## Out of scope for v0.1, on the roadmap

- TypeScript reference impls for every skill (Python-only now)
- A web-based skill browser
- `prior-auth-fhir` (CoverageEligibilityRequest builders)
- `smart-oauth-scaffold` (Epic SMART on FHIR)
- `epic-fhir-sandbox` (sandbox account bootstrap)

## Standards referenced

- HIPAA Privacy & Security Rules (45 CFR §160, §164)
- HIPAA Safe Harbor de-identification (45 CFR §164.514(b)(2))
- HL7 FHIR R4 (4.0.1)
- HL7 v2.5.1
- US Core Implementation Guide 6.1.0
- CDS Hooks 1.0
- ONC certification criteria (§170.315)
- NIST 800-53 (relevant controls)
