# Roadmap

## v0.1 — Foundation (May 2026, ✅ shipped)
17 skills (Tier 0/1/2), four-IDE install, CI validation, MIT license.

## v0.2 — More incident skills (May 2026, ✅ shipped)
8 additional skills, bringing the total to 25:
- ✅ `smart-oauth-scaffold` — Epic / Cerner / Athena SMART on FHIR + Fernet token encryption
- ✅ `prior-auth-fhir` — Da Vinci PAS / CRD / DTR payload builders
- ✅ `route-fatness` — fat-route handler linter + service-layer extraction
- ✅ `clinic-config-extract` — hardcoded slug scanner + YAML refactor
- ✅ `migration-bisect` — Alembic bisect harness with ephemeral DB
- ✅ `webhook-verify` — constant-time HMAC verification for 8 providers
- ✅ `phi-log-filter` — continuous logger-boundary PHI scrubber (structlog/pino/winston)
- ✅ `specialty-scaffold` — base + override clinical specialty scaffolder

## v0.3 — Remaining v0.2 backlog
- `epic-sandbox-bootstrap` — clean Epic sandbox account + smoke tests
- `cds-hook-tester` — golden-fixture runner for the cds-hook skill

## v0.4 — TypeScript companion
Every skill currently uses Python reference snippets. Add TS / Node equivalents (Express middleware, Drizzle/Prisma examples, Zod schemas instead of Pydantic).

## v0.5 — Skill discovery UX
- Web browser at `skills.healthcare-skills.dev` (search by tag, incident, regulation)
- `npx healthcare-skills add phi-redact` — fetch one skill without cloning the repo
- AsciiCast demos per skill

## Long-term

- HL7 v2.5.1 → FHIR R4 message-by-message coverage (currently ADT/ORU/SIU only)
- Drug-drug interaction CDS rules sourced from RxNorm + DrugBank
- Skill-pack composition — let teams `extends:` a base pack and add overrides
- Compliance-pack variants for SOC 2, HITRUST, GDPR, India DPDPA
