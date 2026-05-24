# Roadmap

## v0.1 — Foundation (May 2026, ✅ this release)
17 skills (Tier 0/1/2), four-IDE install, CI validation, MIT license.

## v0.2 — More incident skills
Drawn from the same "we got burned by X" backlog the Tier-2 skills came from.

- `smart-oauth-scaffold` — Epic SMART on FHIR + Fernet token encryption
- `prior-auth-fhir` — `CoverageEligibilityRequest` / `CoverageEligibilityResponse` builders
- `epic-sandbox-bootstrap` — clean Epic sandbox account + smoke tests
- `migration-bisect` — find the migration that broke a deploy
- `clinic-config-extract` — find hardcoded clinic slugs and refactor them to YAML
- `route-fatness` — enforce ≤30-line route handlers (Trifetch clinic-os lesson #1)
- `cds-hook-tester` — golden-fixture runner for the cds-hook skill

## v0.3 — TypeScript companion
Every skill currently uses Python reference snippets. Add TS / Node equivalents (Express middleware, Drizzle/Prisma examples, Zod schemas instead of Pydantic).

## v0.4 — Skill discovery UX
- Web browser at `skills.healthcare-skills.dev` (search by tag, incident, regulation)
- `npx healthcare-skills add phi-redact` — fetch one skill without cloning the repo
- AsciiCast demos per skill

## Long-term

- HL7 v2.5.1 → FHIR R4 message-by-message coverage (currently ADT/ORU/SIU only)
- Drug-drug interaction CDS rules sourced from RxNorm + DrugBank
- Skill-pack composition — let teams `extends:` a base pack and add overrides
- Compliance-pack variants for SOC 2, HITRUST, GDPR, India DPDPA
