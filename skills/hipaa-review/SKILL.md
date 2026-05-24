---
name: hipaa-review
description: |
  Review a git diff, file, or PR for HIPAA Security Rule violations (encryption at
  rest / in transit, audit logging, access control, minimum necessary, breach risk).
  Use when the user asks to "review for HIPAA", "compliance review", "is this
  HIPAA-safe", "check this PR before I merge", or runs a code review on
  patient-data-touching code.
when_to_use: |
  Activate when the user:
  - Asks to "review for HIPAA", "compliance review", or "audit this PR"
  - Is about to merge code that touches patient data, auth, logging, or storage
  - Pastes a diff, a route handler, a DB model, or an integration script
    that handles patient data
  - Mentions encryption, access control, audit logs, or HHS Breach Notification
  - References 45 CFR §164 or the HIPAA Security Rule
allowed-tools: [Read, Grep, Edit, Bash]
license: MIT
tags: [hipaa, security, healthcare, compliance, linter]
incident: |
  Most healthtech engineering orgs run formal HIPAA reviews only at quarterly
  cadence, while ship velocity is per-PR. The gap between when bad code is
  written and when the security officer reviews it is days-to-weeks; that gap
  is when breaches happen. This skill encodes the Security Rule checklist into
  a per-PR gate so every diff that touches patient data gets at least a
  structured first pass before merge.
---

# hipaa-review

> Per-PR HIPAA Security Rule review. The first-pass gate, not the final word.

> **Important.** This skill produces engineering review output. It is not legal advice and does not substitute for review by your privacy / security officer. Run it as a fast pre-merge sanity check.

## When to use

- The user is about to merge a PR / land a diff that touches patient data, auth, logging, storage, or any healthcare integration.
- The user asks for a "HIPAA review", "compliance check", or "security review on the PHI side".
- The user pastes a route handler, DB schema, integration script, or logging config.
- The user references 45 CFR §164 (HIPAA Security Rule) or the HHS Breach Notification Rule.

## How it works

Run the review as a structured **eight-section checklist**. For each section, report **PASS** / **WARN** / **FAIL** with the specific line and a one-line remediation. End with a top-line verdict.

### 1. Encryption at rest (45 CFR §164.312(a)(2)(iv))
Look for:
- DB models / migrations that store PHI without `EncryptedType`, `pgcrypto`, KMS-managed encryption, or equivalent
- Local file writes (`open(path, "w")`, `fs.writeFileSync`) of PHI-shaped content
- S3 / GCS uploads without server-side encryption configured (`ServerSideEncryption=aws:kms` / `kmsKeyName=…`)
- Backups, exports, cron-job dumps — these are a common PHI-at-rest gap

### 2. Encryption in transit (45 CFR §164.312(e)(1))
Look for:
- HTTP (not HTTPS) URLs for PHI-touching endpoints (`http://` in fetch / requests calls)
- TLS verify disabled (`verify=False`, `rejectUnauthorized: false`, `--insecure`)
- ngrok or `*.example.com` URLs left in production configs (see also `secrets-placeholder` skill)
- WebSockets without `wss://`
- Internal service-to-service calls trusted blindly without mTLS

### 3. Access control (§164.312(a)(1))
Look for:
- Routes that accept a `patient_id` from the request and don't verify the caller is authorized for that patient
- Multi-tenant queries missing `client_id` / `tenant_id` predicates (route into `tenant-rls-guard`)
- Admin endpoints without explicit role checks
- "Service" tokens with effectively unlimited scope
- Missing or wildcard CORS origins on PHI endpoints

### 4. Audit controls (§164.312(b))
Look for:
- Reads / writes of patient data that **aren't** logged to an audit table (route into `audit-trail`)
- Audit logs going only to ephemeral stdout (no durable sink)
- Audit logs containing the PHI they were meant to *record access to* (audit rows should reference a resource, not embed it)
- Missing actor identity (every audit event needs *who* did the thing)
- No retention policy — HIPAA requires 6-year retention

### 5. Person / entity authentication (§164.312(d))
Look for:
- Passwords stored or compared in plaintext
- JWT secrets hardcoded
- Sessions without expiry / refresh policy
- MFA disabled for admin / privileged accounts
- Service accounts without rotation

### 6. Integrity (§164.312(c)(1))
Look for:
- Records that are mutable after they should be immutable (signed notes, completed encounters, finalized prescriptions)
- No append-only history for clinical edits
- DB updates that lose the previous value (no soft-delete / versioning) for clinical data

### 7. Minimum necessary (§164.502(b))
Look for:
- `SELECT *` from `patients` (or similar) when only one field is used
- API responses leaking the full patient record when the caller asked for one field
- Logging full request / response bodies when only a status is needed
- Vendor integrations that send more PHI than the contract requires

### 8. Breach Notification triggers (§164.404)
Look for:
- PHI in logs that ship to a vendor (Datadog, Sentry, LogRocket, FullStory) without a BAA flag
- PHI in error messages that surface to the end user (or worse, to a vendor's bug tracker)
- Stack traces with patient names / DOBs / MRNs
- Screenshots / session recordings of PHI flowing to a marketing analytics tool

## Output format

```
HIPAA-REVIEW — <file or PR>
─────────────────────────────────────────────
1. Encryption at rest       PASS / WARN / FAIL
2. Encryption in transit    PASS / WARN / FAIL
3. Access control           PASS / WARN / FAIL
4. Audit controls           PASS / WARN / FAIL
5. Authentication           PASS / WARN / FAIL
6. Integrity                PASS / WARN / FAIL
7. Minimum necessary        PASS / WARN / FAIL
8. Breach risk              PASS / WARN / FAIL

Findings:
  [§164.312(a)(2)(iv) FAIL]  app/models/patient.py:34 — `Column(String)` stores SSN without encryption.
      → Use `EncryptedType(String, key=settings.PHI_KEY)` from sqlalchemy-utils.
  [§164.312(b) WARN]         app/routes/patients.py:88 — `get_patient` doesn't emit an audit event.
      → Apply `@audited("patient.read", phi_args=("patient_id",))` from healthcare-skills.

Top-line verdict: REQUEST CHANGES — 1 FAIL, 1 WARN.
```

Always:
- Cite the regulation by section number.
- Give a concrete remediation (file + line + suggested fix).
- Distinguish FAIL (block merge) from WARN (merge with follow-up issue) from PASS.

## Example

**Input (the user pastes this diff)**
```python
# app/routes/patients.py
@router.get("/patients/{patient_id}")
def get_patient(patient_id: str, db: Session = Depends(get_db)):
    patient = db.query(Patient).filter_by(id=patient_id).first()
    logger.info(f"loaded patient: {patient.first_name} {patient.last_name}, dob={patient.dob}")
    return patient
```

**Output**
```
HIPAA-REVIEW — app/routes/patients.py
─────────────────────────────────────────────
1. Encryption at rest       —    (DB schema not shown)
2. Encryption in transit    —    (no HTTP/HTTPS code shown)
3. Access control           FAIL  no authorization check; any authenticated user can read any patient_id.
4. Audit controls           FAIL  patient read is not recorded in an AuditEvent table.
5. Authentication           —
6. Integrity                —
7. Minimum necessary        WARN  returns entire patient record; consider a response schema.
8. Breach risk              FAIL  logger.info leaks first/last name + DOB into application logs.

Findings:
  [§164.312(a)(1) FAIL] line 3 — missing access-control check.
      → Add `verify_caller_has_access(current_user, patient_id)` before the query.
      → See healthcare-skills `consent-gate`.

  [§164.312(b) FAIL] line 4 — no audit trail.
      → Wrap with `@audited("patient.read", phi_args=("patient_id",))`.
      → See healthcare-skills `audit-trail`.

  [§164.502(b) WARN] line 5 — returning full Patient model.
      → Return a `PatientReadResponse` Pydantic schema that excludes SSN, raw DOB, address.

  [§164.404 FAIL] line 4 — PHI in log line.
      → Replace with `logger.info("patient.loaded", patient_id=patient_id)`.
      → Run `phi-redact` over recent logs to confirm prior bleeds.

Top-line verdict: REQUEST CHANGES — 3 FAIL, 1 WARN.
```

## Edge cases

- **"It's behind a VPN" is not a substitute.** Network controls are admin / physical safeguards; the technical safeguards in §164.312 still apply.
- **De-identified data is out of scope.** If a code path operates only on data that's been through `phi-redact` or `deid-vault`, mark the relevant sections N/A and say so.
- **Logging *that* something happened is not the same as logging *what*.** "Patient lookup attempted" is fine; "Patient lookup attempted: Maria Hernandez" is a breach.
- **Vendor logs aren't safe by default.** A BAA with Datadog doesn't make PHI in logs OK — it just makes it not-illegal under HIPAA. Treat the log contents as PHI regardless.
- **Don't over-redact at the boundary.** A PHI scrub in a `/patients/{id}` *response* breaks the application — that path is *meant* to return patient data to an authorized caller. Only flag responses that go *outside* the trust boundary (vendor, marketing, public).
- **"Minimum necessary" doesn't apply to treatment.** §164.502(b)(2) carves out treatment activity from the minimum-necessary rule. A clinical user reading a chart is presumptively allowed to see the full chart.

## References

- HIPAA Security Rule — 45 CFR §164.302 to §164.318: [`references/hipaa-security-rule.md`](./references/hipaa-security-rule.md)
- HIPAA Privacy Rule — 45 CFR §164.500 to §164.534
- HIPAA Breach Notification Rule — 45 CFR §164.400 to §164.414
- OWASP healthcare cheat-sheet: [`references/owasp-healthcare.md`](./references/owasp-healthcare.md)
- HHS Security Risk Assessment Tool: <https://www.hhs.gov/hipaa/for-professionals/security/guidance/index.html>
- NIST 800-66 (HIPAA Security Rule implementation guidance): <https://csrc.nist.gov/pubs/sp/800/66/r2/final>
