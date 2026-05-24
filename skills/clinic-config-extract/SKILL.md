---
name: clinic-config-extract
description: |
  Find hardcoded clinic / tenant / customer identifiers ("redding", "ent_sd",
  "stockton-cardiology") scattered across a codebase and refactor them to a
  single YAML config keyed by `client_id`. Use when the user asks to
  "onboard another clinic", "add a new tenant", "find all the hardcoded slugs",
  or hits a bug where the third clinic broke because the second one's slug
  was assumed.
when_to_use: |
  Activate when the user:
  - Plans to onboard a new clinic / tenant / customer
  - Asks "where are all the places clinic X is hardcoded?"
  - Reviews multi-tenant code and finds string literals like "redding",
    "stockton-cardiology", "tenant_001"
  - Mentions configuration drift, per-tenant overrides, or "adding clinic #3"
allowed-tools: [Read, Grep, Edit, Bash]
license: MIT
tags: [multi-tenancy, refactor, linter, healthcare]
incident: |
  Clinic slugs (`"redding"`, `"ent_sd"`, `"stockton-cardiology"`) appeared
  hardcoded in 20+ files across services, templates, and config. Onboarding
  the second clinic required changing code; onboarding the third surfaced
  paths where a slug check defaulted to the first clinic, silently routing
  data wrong. This skill finds the slugs and refactors them to a single
  YAML config; CI gates against new hardcodes.
---

# clinic-config-extract

> Tenant slugs are config, not code. Find them, extract them, prevent regression.

## When to use

- The user plans to onboard another clinic / tenant.
- The user reviews multi-tenant code and finds bare string literals like `"redding"`, `"ent_sd"`, `"stockton-cardiology"`.
- A bug report says "feature X works for clinic A but not clinic B".
- The user wants a list of "everywhere clinic X appears in the codebase".

## How it works

1. **Bootstrap `clinics.yaml`.** Single source of truth, keyed by `client_id`:
   ```yaml
   clinics:
     redding:
       display_name: "Redding Internal Medicine"
       specialty: internal-medicine
       timezone: America/Los_Angeles
       ehr_base_url: https://ecw.redding.example.com
       fax_provider: srfax
       phi_storage: us-west1
       enabled_features: [scheduling, refills]
     ent_sd:
       display_name: "ENT San Diego"
       specialty: ent
       timezone: America/Los_Angeles
       ehr_base_url: https://ecw.ent-sd.example.com
       fax_provider: phaxio
       enabled_features: [scheduling, intake]
     stockton_cardiology:
       display_name: "Stockton Cardiology"
       specialty: cardiology
       timezone: America/Los_Angeles
       enabled_features: [scheduling, refills, intake]
   ```

2. **Grep the codebase for known slugs.** For each slug in `clinics.yaml`:
   ```bash
   grep -rn --include='*.py' --include='*.ts' --include='*.tsx' --include='*.yaml' \
     -E '"(redding|ent_sd|stockton-cardiology)"' app/ web/
   ```
   Annotate each finding with its category:
   - **Configuration value** (e.g. EHR URL, timezone) → move to `clinics.yaml`, replace with `clinic.ehr_base_url`
   - **Conditional branch** (`if clinic_id == "redding": ...`) → replace with a feature flag or specialty check
   - **Default value** (`clinic_id = clinic_id or "redding"`) → **never default**; require an explicit ID
   - **Display string** (UI copy showing clinic name) → use `clinic.display_name`

3. **Refactor.** For each finding, propose the diff:
   ```python
   # before
   if patient.clinic_id == "redding":
       timezone = pytz.timezone("America/Los_Angeles")

   # after
   timezone = pytz.timezone(clinics.get(patient.clinic_id).timezone)
   ```

4. **Add a CI gate.** A `.clinic-slugs.deny` file lists every known slug; CI fails if any new code (outside `clinics.yaml` and explicit allowlist paths) introduces the literal:
   ```bash
   # .github/workflows/no-clinic-slugs.yml
   - run: |
       slugs=$(grep -v '^#' .clinic-slugs.deny | tr '\n' '|' | sed 's/|$//')
       ! git diff --name-only origin/main... \
         | grep -vE '(clinics.yaml|tests/fixtures/)' \
         | xargs -r grep -lE "\"($slugs)\"" \
         && echo "clean" || (echo "found hardcoded slug" && exit 1)
   ```

5. **Add a default-prevention test.** A unit test asserts that any code path that takes `clinic_id` raises if it's `None` / `""` / unknown — never silently defaults.

## Rules

| ID | Severity | Rule |
|---|---|---|
| CCE-001 | ERROR | Hardcoded clinic slug literal outside `clinics.yaml` / `tests/fixtures/`. |
| CCE-002 | ERROR | Code path that branches on a clinic slug literal (`if x == "redding"`). |
| CCE-003 | ERROR | Default-to-clinic-X pattern (`clinic_id or "redding"`). |
| CCE-004 | WARN  | Per-clinic file at `app/<slug>/...` — should be a per-specialty module or a single module driven by config. |

## Example output

```
clinic-config-extract — repo scan
─────────────────────────────────────────────
CCE-001  app/services/scheduling.py:23   "redding"       → use clinic.ehr_base_url
CCE-002  app/routes/intake.py:45         if clinic_id == "ent_sd": → branch on clinic.specialty == "ent"
CCE-003  app/middleware/tenant.py:11     clinic_id or "redding"    → raise on missing
CCE-001  web/src/lib/clinic.ts:8         'stockton-cardiology'     → fetch from /api/clinics
CCE-004  app/redding/                    per-clinic directory      → consolidate or rename to app/internal_medicine/
3 ERROR, 1 WARN
```

## Edge cases

- **Display strings in legal / contractual docs** legitimately hardcode a clinic's name (Terms of Service, BAA, customer-facing email subjects). Allowlist those paths.
- **Test fixtures** intentionally pin to a known slug. The CI gate exempts `tests/fixtures/` by default.
- **Migration data.** Historic DB rows are tagged with slugs; never rewrite history. `clinics.yaml` is forward-looking.
- **One-clinic deployments** (a clinic running its own instance). The repo should still use `clinics.yaml` with one entry — adding the second one then becomes a config change, not a refactor.
- **Slug != client_id.** Some codebases call it `client_id`, `tenant_id`, or `org_id`. The linter accepts a config key for the local convention.

## References

- Trifetch clinic-os lessons-learned #2 (the original incident)
- Multi-tenant SaaS patterns (Microsoft Azure docs are good): <https://learn.microsoft.com/en-us/azure/architecture/guide/multitenant/overview>
- Feature-flag patterns (Martin Fowler): <https://martinfowler.com/articles/feature-toggles.html>
- [`scripts/find_hardcoded_slugs.py`](./scripts/find_hardcoded_slugs.py)
- [`examples/clinics.yaml`](./examples/clinics.yaml)
- See also: `tenant-rls-guard` (the runtime side of multi-tenancy)
