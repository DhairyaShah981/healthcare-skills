# Epic on FHIR — production gotchas

Drawn from real Epic integrations. Most aren't documented in the official spec.

## Onboarding & app review
- **Sandbox `client_id` ≠ production `client_id`.** Easy to miss. Production requires app review through the customer's Epic instance.
- **App review takes weeks.** Budget for it. Sandbox-passing != production-ready.
- **App audience is locked at registration.** Patients vs Clinicians changes which scopes you can request; you can't switch later, you re-register.
- **One app per audience.** If you serve both patient-facing and clinician-facing flows, register two separate apps.

## Auth flow
- **`aud` parameter is required** and must equal the FHIR base URL the launch came from. Missing `aud` → `invalid_request`.
- **Redirect URI is exact-match.** `https://example.com/cb` and `https://example.com/cb/` are different. Trailing slashes have killed many integrations.
- **`launch` scope is required for EHR launch**, omitted for standalone. Mixing fails silently (returns wrong context).
- **`fhirUser` claim ID is opaque.** Don't parse it; treat it as a string. Use `Practitioner/{id}` via the `fhirUser` URL if you need the user resource.
- **PKCE is required for SMART 2.0**, optional for 1.0. Epic supports both; default to PKCE.

## Scopes
- **Scope downgrade.** Epic may grant fewer scopes than you ask for. Always inspect `tok["scope"]` after exchange.
- **Mixed `patient/*` and `system/*` scope requests fail.** Pick one tier.
- **`offline_access` ≠ guaranteed refresh token.** Some Epic audiences ignore the request.
- **`Patient.search` is restricted.** Patient-context apps generally can't query by name; you operate within the launched patient's record.

## FHIR responses
- **Bundle entries can be empty `{}`** for resources the user doesn't have access to. Filter these in your client.
- **`Reference` strings may be relative or absolute.** Normalize before joining to the base URL.
- **Pagination links** sometimes return absolute URLs that differ from the FHIR base (different load balancer hostname). Use the link verbatim.
- **`_count` ≤ 100** in most Epic deployments. Higher values silently capped.
- **`_summary=true` doesn't always populate `meta.tag` correctly**; don't rely on it.

## TLS & headers
- **Epic strict-checks `Accept` header.** Send `Accept: application/fhir+json`, not `application/json`.
- **`User-Agent` is logged on Epic side** and useful when debugging with Epic support — include your app name and version.
- **TLS 1.2 minimum.** Some Epic edges still reject TLS 1.3 in old configurations; usually fine for new sandboxes.

## JWKS & key rotation
- **Self-signed certs sometimes rejected.** Epic prefers certs from a known CA for production JWKS endpoints.
- **JWKS cache TTL** — Epic caches keys for up to 24h. Keep N≥2 keys during rotation.
- **Algorithm:** `RS384` is preferred per the SMART 2.0 spec; some Epic deployments accept `RS256`.

## Debugging tools
- Inspect token claims at <https://jwt.io> — verify `aud`, `iss`, `exp`.
- Epic's "App Orchard" (rebranded "Showroom" → "Connection Hub") is the marketplace; not required for sandbox.
- For deep debugging, Epic's CSAR / Open Epic team is reachable via the support portal.
