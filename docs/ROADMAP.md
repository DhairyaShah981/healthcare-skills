# Roadmap

## v0.1 — Foundation (May 2026, ✅ shipped)
17 skills (Tier 0/1/2), four-IDE install, CI validation, MIT license.

## v0.2 — More incident skills (May 2026, ✅ shipped)
8 additional skills, bringing the total to 25 (now 27 in v0.3):
- ✅ `smart-oauth-scaffold` — Epic / Cerner / Athena SMART on FHIR + Fernet token encryption
- ✅ `prior-auth-fhir` — Da Vinci PAS / CRD / DTR payload builders
- ✅ `route-fatness` — fat-route handler linter + service-layer extraction
- ✅ `clinic-config-extract` — hardcoded slug scanner + YAML refactor
- ✅ `migration-bisect` — Alembic bisect harness with ephemeral DB
- ✅ `webhook-verify` — constant-time HMAC verification for 8 providers
- ✅ `phi-log-filter` — continuous logger-boundary PHI scrubber (structlog/pino/winston)
- ✅ `specialty-scaffold` — base + override clinical specialty scaffolder

## v0.3 — Remaining backlog + tooling (May 2026, ✅ shipped)
- ✅ `epic-sandbox-bootstrap` — 12-step Epic on FHIR sandbox onboarding + smoke
- ✅ `cds-hook-tester` — golden-fixture runner for a CDS Hooks service
- ✅ CLI (`npx healthcare-skills <cmd>`) with list / info / add / add-all / search / tags / doctor
- ✅ TypeScript reference impls — phi-log-filter, webhook-verify, audit-trail, consent-gate
- ✅ Web discovery site (`docs/site/`) auto-deploying to GitHub Pages
- ✅ Full QA: 43 CLI tests + 26 TS unit tests + 10-step site QA via headless browser

## v0.4 — More TypeScript reference impls
Port the remaining high-signal Python skills to TS:
- `deid-vault` (Node crypto + HMAC)
- `tenant-rls-guard` (TS AST via `ts-morph`)
- `voice-agent-lint` (TS-native)

## v0.5 — Skill discovery UX polish
- AsciiCast demos per skill (`asciinema`) embedded in the site
- Incident-driven landing pages (clickable from each card to the postmortem)
- `npx healthcare-skills add <name>` shipping via npm (currently only via repo checkout)

## Long-term

- HL7 v2.5.1 → FHIR R4 message-by-message coverage (currently ADT/ORU/SIU only)
- Drug-drug interaction CDS rules sourced from RxNorm + DrugBank
- Skill-pack composition — let teams `extends:` a base pack and add overrides
- Compliance-pack variants for SOC 2, HITRUST, GDPR, India DPDPA
