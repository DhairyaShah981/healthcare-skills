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

## v0.4 — More TS ports + incident pages + composition (May 2026, ✅ shipped)
- ✅ `ts/deid-vault` (Node crypto + HMAC, 6 tests)
- ✅ `ts/tenant-rls-guard` (regex-based linter for Drizzle / Prisma / raw SQL, 8 tests)
- ✅ `ts/voice-agent-lint` (TS-native RTL-001..017, 8 tests)
- ✅ Per-skill incident landing pages on the web catalog (`docs/site/incident.html?skill=<name>`) — cards link here, not to GitHub directly
- ✅ HL7 v2 coverage broadened: ORU^R01 (lab result) + SIU^S12 (new appointment) example pairs
- ✅ Skill-pack composition pattern documented (`docs/COMPOSITION.md`)
- ✅ `.github/workflows/release.yml` — tag-driven GitHub Release; npm publish job opt-in via `NPM_TOKEN`
- ✅ `PUBLISHING.md` checklist for tag-and-publish flow
- ✅ Full QA: 43 CLI tests + 48 TS tests across 7 packages + 22-step browser QA (incident pages, search, filter, 404)

## v0.5 — UX polish (next)
- AsciiCast demos per skill (`asciinema`) embedded in the incident pages
- Maintainer-run `npm publish --access public` for the first version (currently 0.4.0 tarball ships via GitHub Release; PUBLISHING.md has the one-time auth steps)

## Long-term

- HL7 v2.5.1 → FHIR R4 message-by-message coverage (now ADT/ORU/SIU; add ORM, MDM, ADT-A03/A04/A08, ACK, BAR, DFT)
- Drug-drug interaction CDS rules sourced from RxNorm + DrugBank
- First-class `healthcare-skills compose <overlay-path>` subcommand (the pattern is documented in `docs/COMPOSITION.md`)
- Compliance-pack variants for SOC 2, HITRUST, GDPR, India DPDPA
