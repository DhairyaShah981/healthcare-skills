# OWASP — healthcare-specific application security

Mapping of OWASP Top 10 (2021) to common healthcare-engineering failure modes. Use this alongside the HIPAA Security Rule checklist for a fuller review.

## A01:2021 — Broken Access Control
**Healthcare flavour:** missing patient-level authorization. Just because a user is logged in doesn't mean they should see patient X.
- "IDOR" — `/api/patients/{id}` accepting any `id` the caller passes
- Multi-tenant `client_id` predicates missing on queries (see `tenant-rls-guard`)
- Admin endpoints reachable by regular users
- Service tokens with effectively root scope

## A02:2021 — Cryptographic Failures
- TLS verify disabled (`verify=False`, `--insecure`)
- HTTP (not HTTPS) URLs for PHI endpoints
- Field-level encryption missing on SSN / DOB / account numbers
- Backups / exports written unencrypted
- Keys in source control or environment files committed to git

## A03:2021 — Injection
- SQL injection in raw queries against patient data
- LDAP injection in directory auth
- Command injection in PDF / fax generation pipelines (`pdftotext`, `unoconv`)
- HL7v2 segment injection — fields with `|` `^` `&` characters reaching parsers unescaped

## A04:2021 — Insecure Design
- "Send by SMS" / "Print to local printer" surfaces that bypass audit controls
- Long-lived bearer tokens with no refresh
- Implicit trust between services without mTLS

## A05:2021 — Security Misconfiguration
- Default DB / admin credentials
- Verbose error pages leaking stack traces with PHI
- Permissive CORS (`Access-Control-Allow-Origin: *`) on PHI endpoints
- Debug routes exposed in production
- ngrok URLs in production configs

## A06:2021 — Vulnerable and Outdated Components
- Unpatched FHIR / HL7 libraries — these get CVEs
- Old jose / pyjwt versions vulnerable to algorithm confusion
- Old TLS versions enabled on backend services

## A07:2021 — Identification and Authentication Failures
- Password reset flows without rate limits
- Magic-link tokens that don't expire
- MFA disabled for admin / clinician accounts
- Session fixation in patient portals

## A08:2021 — Software and Data Integrity Failures
- Clinical signatures not cryptographically protected
- Immutable resources made mutable by feature flag
- Lab results pulled from a source without integrity verification
- CI / build pipelines pulling unpinned dependencies

## A09:2021 — Security Logging and Monitoring Failures
- No audit trail on PHI reads (see `audit-trail`)
- Audit logs not durably stored / not centralised
- No alerting on anomalous access patterns (one user reading 500 charts in 5 minutes)
- PHI in logs that ship to vendors without BAA (see also `phi-redact`)

## A10:2021 — Server-Side Request Forgery
- Receiver of file uploads making outbound HTTP requests to user-supplied URLs
- PDF / image processors fetching remote resources
- "Print to remote URL" surfaces in fax/integration code

## Healthcare-specific additions outside OWASP

- **Tool-URL hardcoding in voice agents** — see `voice-agent-lint` and `secrets-placeholder`.
- **De-identification leakage** — pseudonyms reused across patients, vault key in repo.
- **Lab order spoofing** — `MedicationRequest.requester` not verified against current user.
- **PHI in URLs** — `/patients?name=Maria%20Hernandez` ends up in proxy / CDN logs.
- **Webhook secrets in committed JSON** — common in voice / EHR integration code.

## OWASP API Security Top 10 (2023) — quick map

| OWASP API | Healthcare hot spot |
|---|---|
| API1 — Broken Object Level Authorization | Per-patient access checks |
| API2 — Broken Authentication | Bearer tokens, JWT secrets |
| API3 — Broken Object Property Level Authorization | Returning full Patient when scope is narrower |
| API5 — Broken Function Level Authorization | Admin routes reachable by clinicians |
| API6 — Unrestricted Access to Sensitive Business Flows | "Bulk export" endpoint without rate / quota |
| API9 — Improper Inventory Management | Old `/v1/` endpoints still serving PHI |
