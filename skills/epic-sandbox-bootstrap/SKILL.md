---
name: epic-sandbox-bootstrap
description: |
  Bootstrap an Epic on FHIR sandbox account end-to-end: app registration,
  client_id wiring, scope selection, redirect URI, JWKS, plus a smoke-test
  harness that exercises Patient.read / Observation.search / SMART launch.
  Use when the user asks "set up Epic sandbox", "Epic on FHIR sandbox",
  "how do I test against Epic", or is starting an Epic integration from
  scratch.
when_to_use: |
  Activate when the user:
  - Is starting an Epic on FHIR integration from scratch
  - Mentions Epic, Epic sandbox, fhir.epic.com, or "the Epic developer account"
  - Asks how to register / configure an app for Epic
  - Has a failing Epic launch and needs to step through the config checklist
  - Wants a smoke-test that proves Epic auth + a basic read works
allowed-tools: [Read, Write, Edit, Bash, WebFetch]
license: MIT
tags: [epic, smart, oauth, healthcare, sandbox]
incident: |
  Epic-on-FHIR onboarding has 12+ steps spread across the Epic developer
  portal, the SMART spec, and the org's own infra. Engineers consistently
  miss one (wrong `aud`, redirect URI mismatch, scope missing, sandbox
  vs prod client_id swapped) and waste a half-day diagnosing a generic
  "invalid_request" error. This skill walks through the checklist in
  order and ships a smoke-test that proves the wiring is correct before
  anyone writes app code.
---

# epic-sandbox-bootstrap

> 12-step Epic on FHIR onboarding — checklist + smoke test. Pairs with `smart-oauth-scaffold`.

## When to use

- The user is starting an Epic integration from zero.
- The user has a failing Epic launch and needs to step through what's misconfigured.
- The user wants a smoke-test that proves auth + a basic FHIR read works.

## How it works

1. **Pick the sandbox flavour.**
   - **Public sandbox** (no registration) — for read-only smoke-tests against canned Epic data. Base: `https://fhir.epic.com/interconnect-fhir-oauth/api/FHIR/R4/`.
   - **Custom sandbox** (free, register at <https://fhir.epic.com>) — for a real client_id, scope review, and tenant-like config. Typical for any serious integration.
   - **Connectathon / vendor environment** — production-shape; only after passing Epic's app review.

2. **Register the app.** At <https://fhir.epic.com> → Build Apps → Create. Fields that cause silent failures later if wrong:
   - **Application audience** — `Patients` vs `Clinicians or Administrative Users`. Choose based on who'll launch the app; this affects the available scopes.
   - **Incoming APIs** — pick R4, not DSTU2 (unless legacy).
   - **OAuth 2.0 Redirect URIs** — exact match, no trailing slash mismatches. Add one per env.
   - **App endpoint URI / Launch URI** — required for EHR launch; the URL the EHR opens.
   - **Backend services / Backend system** — only for system-to-system; needs a JWKS URL.

3. **Pick scopes.** For patient-launched apps:
   - `launch openid fhirUser online_access`
   - `patient/Patient.read patient/Observation.read patient/Condition.read` (etc, what you actually need)
   - `offline_access` if you need refresh tokens

   For backend / system services:
   - `system/Patient.read system/Observation.read` etc.
   - JWKS-signed `client_assertion` (no client_secret in this flow)

4. **Discover the endpoints.** Always read `.well-known/smart-configuration`:
   ```bash
   curl https://fhir.epic.com/interconnect-fhir-oauth/api/FHIR/R4/.well-known/smart-configuration | jq
   ```
   This gives you `authorization_endpoint`, `token_endpoint`, `revocation_endpoint`, plus the supported scopes and capabilities.

5. **Wire your service.** Compose with `smart-oauth-scaffold`. The Epic-specific bits:
   - `aud` parameter is **required** and must equal the `iss` value the launcher passed (or the sandbox base URL for standalone).
   - For confidential clients, Epic prefers `private_key_jwt` (asymmetric) — publish a JWKS at a stable URL.
   - Refresh tokens only for backend / system apps in some Epic configurations.

6. **Run the smoke-test.** [`scripts/epic_smoke.py`](./scripts/epic_smoke.py):
   - Fetches `.well-known/smart-configuration`
   - Does an authorization flow (standalone, against a known test patient)
   - Exchanges code for token
   - Calls `Patient/{id}` and asserts a non-empty response
   - Calls `Observation?patient={id}&category=vital-signs&_count=5` and asserts ≥1 result
   - Optionally exercises refresh
   - Prints PASS / FAIL with the specific step that failed

7. **Promote.** Once smoke passes against sandbox, the same code points at the customer's production base URL with a different `client_id`. Epic app review is required before production go-live; budget weeks, not days.

## Step-by-step checklist (run this for every new Epic deployment)

| # | Step | Common failure |
|---|---|---|
| 1 | Register app at fhir.epic.com | wrong audience |
| 2 | Note the **sandbox** `client_id` and (if confidential) `client_secret` | swapped with prod |
| 3 | Add **all** redirect URIs (dev, staging, prod) | trailing slash mismatch |
| 4 | Pick scopes that match the audience | mixing `patient/*` and `system/*` |
| 5 | If confidential: publish JWKS at a stable URL | self-signed cert; Epic rejects |
| 6 | Configure `SMART_CLIENT_ID`, `SMART_REDIRECT_URI`, `SMART_FERNET_KEY` in your service | leaked to git |
| 7 | Fetch `.well-known/smart-configuration` from the Epic FHIR base | wrong base URL |
| 8 | Run `scripts/epic_smoke.py --base <fhir-base>` | `aud` missing |
| 9 | Verify `Patient/{id}` returns 200 + non-empty | scope missing |
| 10 | Verify a search query returns at least one bundle entry | wrong patient context |
| 11 | Verify refresh works (if requested `offline_access`) | refresh not granted to this audience |
| 12 | Tag the working config, then bump `client_id` to the production app | swap order wrong; prod app not yet approved |

## Example smoke-test output

```
$ python scripts/epic_smoke.py --base https://fhir.epic.com/interconnect-fhir-oauth/api/FHIR/R4 \
                                --patient Tbt3KuCY0B5PSrJvCu2j-PlK.aiHsu2xUjUM8bWpetXoB
fetching .well-known/smart-configuration...         PASS
  authorization_endpoint=https://fhir.epic.com/.../oauth2/authorize
  token_endpoint=https://fhir.epic.com/.../oauth2/token
standalone authorize → token...                       PASS
  scopes granted: launch/patient openid fhirUser patient/Patient.read patient/Observation.read offline_access
read Patient/...                                       PASS
  resourceType=Patient name=Camila Lopez gender=female
search Observation?patient=...&category=vital-signs&_count=5  PASS
  5 results, first: 8867-4 Heart rate 82 /min
refresh token exchange...                              PASS
  new access_token issued; expires in 3600s

epic-sandbox-bootstrap: all 5 smoke checks passed.
```

## Edge cases

- **Audience mismatch.** Epic checks `aud` against `iss` strictly; some sandboxes accept the FHIR base, some accept the authorization server URL. Try both if the first fails.
- **Custom EHR launch context.** Some Epic deployments inject extra context parameters (`launch_token`, custom claims) — read the actual launch URL the EHR sends, don't assume.
- **JWKS rotation.** If you use asymmetric client auth, keep N≥2 keys in your JWKS during rotation — Epic caches keys briefly.
- **Patient scope vs user scope.** A clinician-launched app gets `user/*` scopes; a patient-launched app gets `patient/*`. Mixing them in the request triggers `invalid_scope`.
- **`offline_access` not always granted.** Some Epic audiences refuse refresh tokens regardless of the request. Handle the no-refresh case gracefully.
- **Production app review is a separate process** with its own checklist (security, privacy, branding). Budget weeks. Don't conflate sandbox-passing with production-ready.

## References

- Epic on FHIR portal: <https://fhir.epic.com>
- Epic OAuth 2.0 launch: <https://fhir.epic.com/Documentation?docId=oauth2&section=Launch>
- Epic OAuth 2.0 confidential clients: <https://fhir.epic.com/Documentation?docId=oauth2&section=Backend>
- SMART App Launch 2.0: <https://hl7.org/fhir/smart-app-launch/STU2/>
- [`scripts/epic_smoke.py`](./scripts/epic_smoke.py) — runnable smoke test
- [`references/epic-quirks.md`](./references/epic-quirks.md) — production gotchas
- Compose with: `smart-oauth-scaffold` (the runtime wiring this skill bootstraps), `audit-trail` (record launches)
