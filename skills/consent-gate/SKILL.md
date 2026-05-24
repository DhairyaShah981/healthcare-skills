---
name: consent-gate
description: |
  Add a patient-consent verification gate to API endpoints (FastAPI, Express,
  Django, Flask) so a clinician / app / vendor can only access patient data the
  patient has actually consented to share. Use when the user asks to "check
  consent", "verify the patient agreed", "block this endpoint until consented",
  or works on a route that exposes patient data to a third party.
when_to_use: |
  Activate when the user:
  - Asks to add patient consent verification to an endpoint
  - References a FHIR Consent resource, an OAuth scope, or "21st Century Cures"
  - Is integrating with a third-party app that needs patient authorization
  - Works on a route that exposes data outside the treatment context (research,
    marketing, analytics, partner sharing)
  - Mentions SMART on FHIR scopes, patient/* scopes, or app-level access
allowed-tools: [Read, Write, Edit, Bash]
license: MIT
tags: [hipaa, consent, healthcare, fhir, authorization]
incident: |
  Endpoints that exposed patient data to partner apps relied on application-
  level role checks but not on per-patient consent. Result: a partner app's
  bearer token could read any patient's data the org had — far beyond what
  each patient had actually authorized. The consent-gate dependency enforces
  the FHIR Consent resource (or equivalent) at the HTTP layer.
---

# consent-gate

> A small dependency that says "this patient has consented to this scope, for this app, right now."

## When to use

- The endpoint exposes patient data to a third-party app, partner, vendor, or research workflow.
- The org has FHIR `Consent` resources (or any patient-authorization record) and you need to enforce them.
- The user mentions SMART on FHIR `patient/*.read`, `patient/*.write`, or per-patient app authorization.
- The user is implementing 21st Century Cures patient-access APIs.

## How it works

1. **Decide what "consent" means in this codebase.** Three common shapes:
   - **FHIR Consent resource** — most rigorous; a `Consent` row with status `active`, scope mapping to the requested action.
   - **OAuth scopes** — SMART on FHIR `patient/Patient.read`, `patient/Observation.read`, with per-app authorisation.
   - **Application-level consent flags** — a `patient.consents` row keyed by `(patient_id, purpose, recipient)`.

   Ask the user; default to FHIR Consent for new code and OAuth scopes for SMART apps.

2. **Express the requirement at the route.** Add a dependency / decorator / middleware that names *what* the route is doing:
   ```python
   @router.get("/patients/{patient_id}/observations",
               dependencies=[Depends(require_consent(scope="patient/Observation.read"))])
   ```

3. **Resolve the patient context from the route, not the body.** The patient ID must come from the path or the authenticated caller — never from request body fields the caller can spoof.

4. **Check consent before the query, not after.** A consent failure must result in a 403 *before* the patient record is read, so the read never produces a log line or audit row that says "successfully read patient X."

5. **Audit the consent check itself.** Whether it passes or fails, write an audit row (`@audited("consent.check")`). Forensics often want "did we check consent and what did we find?"

6. **Return a structured error.** A 403 with a body that says *which* consent or scope was missing — but **not** with PHI in the message. Apps should be able to react to "patient has not consented to Observation.read" without leaking the patient's identity in the response.

7. **Re-check on every request.** Consent can be revoked at any time. Cache for at most 60 seconds; ideally not at all for write paths.

## Example (FastAPI + FHIR Consent)

```python
# app/security/consent.py
from fastapi import Depends, HTTPException, status
from healthcare_skills.audit_trail import audited

def require_consent(*, scope: str):
    @audited(action="consent.check")
    def _dep(
        patient_id: str,
        current_app: AppPrincipal = Depends(current_app),
        db: Session = Depends(get_db),
    ) -> None:
        consent = (
            db.query(Consent)
            .filter(
                Consent.patient_id == patient_id,
                Consent.recipient == current_app.id,
                Consent.status == "active",
                Consent.scope.contains(scope),
                Consent.period_start <= func.now(),
                or_(Consent.period_end.is_(None), Consent.period_end >= func.now()),
            )
            .first()
        )
        if consent is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"error": "consent_required", "scope": scope, "app": current_app.id},
            )
    return _dep


# app/routes/observations.py
@router.get(
    "/patients/{patient_id}/observations",
    dependencies=[Depends(require_consent(scope="patient/Observation.read"))],
)
@audited(action="observation.list", resource_type="Observation")
def list_observations(patient_id: str, db: Session = Depends(get_db)):
    return db.query(Observation).filter_by(patient_id=patient_id).all()
```

A full version, including a SMART-on-FHIR scope variant and an Express middleware, is in [`examples/fastapi_consent_dep.py`](./examples/fastapi_consent_dep.py).

## Example (SMART on FHIR scopes)

```python
def require_smart_scope(*, scope: str):
    """Verify the access token has the required SMART on FHIR scope."""
    def _dep(token_claims: dict = Depends(decode_token)) -> None:
        granted = set(token_claims.get("scope", "").split())
        if scope not in granted and not _scope_covers(granted, scope):
            raise HTTPException(403, {"error": "insufficient_scope", "required": scope})
    return _dep
```

The `_scope_covers` helper handles SMART scope inheritance: `patient/*.read` covers `patient/Observation.read`, `user/*.*` covers `patient/*.read`, etc.

## Edge cases

- **Break-glass access.** In genuine emergencies a clinician may need to access a patient who hasn't consented. Don't disable the gate — add a `break_glass` flag with stricter auditing (every break-glass event reviewed within 24h).
- **Consent for treatment is implicit.** Treatment-context consent is typically captured at intake, not per-request. The gate is for *secondary uses*: research, marketing, partner sharing.
- **Active != current.** A consent with status `active` but `period_end` in the past is no longer in force. Always check the period.
- **Revocation must be honoured immediately.** No caching past a few seconds for write paths.
- **Don't 404 instead of 403.** Returning 404 to hide existence is fine for unauthenticated requests; once a clinician is authenticated, returning 404 on a real patient confuses workflows. Use 403 with `consent_required`.
- **Audit the *check*, not the *body*.** The audit row for a consent check should say which scope was checked and which consent record matched, never the patient's name.
- **Provenance.** When a write succeeds under a consent, write a FHIR `Provenance` resource referencing the consent — this is the durable record of "this action was authorized by that consent."

## References

- HIPAA Privacy Rule — 45 CFR §164.508 (authorization)
- FHIR R4 [Consent](https://www.hl7.org/fhir/R4/consent.html) and [Provenance](https://www.hl7.org/fhir/R4/provenance.html)
- SMART on FHIR scopes: <https://hl7.org/fhir/smart-app-launch/scopes-and-launch-context.html>
- ONC §170.315(g)(10) — Standardized API for patient and population services
- [`examples/fastapi_consent_dep.py`](./examples/fastapi_consent_dep.py) — full reference impl
