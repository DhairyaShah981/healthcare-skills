# Per-EHR SMART on FHIR quirks

Things the spec doesn't tell you about. Drawn from production integrations.

## Epic
- `aud` parameter is **required**. Set it to the `iss` value the launcher passed.
- Sandbox base: `https://fhir.epic.com/interconnect-fhir-oauth/api/FHIR/R4`
- App registration: <https://fhir.epic.com> — manual approval, ~1 business day.
- Supports refresh tokens but **only for backend / system apps**. Patient-facing standalone apps don't get refresh tokens by default.
- `patient/*.read` works; `user/*.read` works for clinician-launched contexts.
- Production launches must be signed up under a customer-specific client_id; sandbox client_id is for testing only.
- App must be registered as either "Patients" or "Clinicians or Administrative Users" — different flows.

## Cerner / Oracle Health
- Sandbox: `https://fhir-ehr.cerner.com/r4/<tenant>/`
- `Accept-Encoding: identity` sometimes required on token endpoint (otherwise gzip-mangled response).
- Supports both confidential (with `client_secret`) and public (PKCE only) clients.
- Refresh-token rotation: yes; the old refresh token is invalidated on use.

## Athena (athenahealth)
- Sandbox: contact athena partner support; no public sandbox URL.
- **No refresh tokens** for sandbox apps; production apps must specifically request them.
- `aud` parameter checked strictly.
- `launch/patient` scope requires the EHR to pick a patient; missing means standalone-no-patient flow.

## Allscripts / Veradigm
- Multiple FHIR endpoints per tenant; the launcher passes the specific one via `iss`.
- App registration via Allscripts Developer Program — slower onboarding than Epic.

## Meditech
- Limited SMART 2.0 support as of writing. Default to 1.0 patterns.
- `iss` discovery may use a different `.well-known/` path; check `metadata` operation as fallback.

## SMART Health IT sandbox (universal testing)
- Public sandbox at <https://launch.smarthealthit.org/>
- Useful for unit tests; doesn't reflect any particular vendor's quirks.
- Free, no registration required.

## Common gotchas across vendors
- **id_token claims**. Don't assume `sub`, `fhirUser`, or `profile`. Inspect each EHR's id_token shape and code defensively.
- **Scope downgrade.** EHRs may grant fewer scopes than you requested. Always check `tok["scope"]` against what you asked for and degrade gracefully.
- **CORS on `.well-known/smart-configuration`.** Some EHRs don't include CORS headers; fetch from your backend, not directly from the browser.
- **Token endpoint encoding.** `application/x-www-form-urlencoded`, not JSON. A common silent failure.
