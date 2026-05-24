"""
fastapi_consent_dep.py — reference patient-consent dependency for FastAPI.

Two variants:
  1. FHIR Consent backend — checks a Consent resource in the DB
  2. SMART on FHIR scopes — checks the access token's scope claim

Both write an audit row for every check (success or failure) via the
audit-trail skill's @audited decorator.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterable

from fastapi import Depends, HTTPException, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

# Replace these imports with your project's actual modules.
# from app.db import get_db
# from app.models.consent import Consent
# from app.auth import current_app, decode_token, AppPrincipal
# from healthcare_skills.audit_trail import audited


# ── FHIR Consent backend ──────────────────────────────────────────────────

def require_consent(*, scope: str, purpose: str = "treatment"):
    """
    Return a FastAPI dependency that enforces an active FHIR Consent resource
    permitting the requested scope for the requesting app + patient.

    Usage:
        @router.get(
            "/patients/{patient_id}/observations",
            dependencies=[Depends(require_consent(scope="patient/Observation.read"))],
        )
        def list_obs(patient_id: str, ...): ...
    """

    # @audited(action="consent.check", phi_args=("patient_id",))
    def _dep(
        patient_id: str,
        current_app: "AppPrincipal" = Depends("current_app"),
        db: Session = Depends("get_db"),
    ) -> None:
        now = datetime.now(tz=timezone.utc)
        consent = (
            db.query("Consent")
            .filter(
                "Consent.patient_id" == patient_id,
                "Consent.recipient" == current_app.id,
                "Consent.status" == "active",
                "Consent.scopes".contains([scope]),
                or_("Consent.period_start" <= now, "Consent.period_start".is_(None)),
                or_("Consent.period_end".is_(None), "Consent.period_end" >= now),
            )
            .first()
        )
        if consent is None:
            # Note: error body intentionally carries no PHI; just the missing scope
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": "consent_required",
                    "scope": scope,
                    "purpose": purpose,
                    "app": current_app.id,
                },
            )

        if _is_revoked_within(consent, now, max_age_seconds=60):
            # Caching window expired — re-check consent revocation list
            if _on_revocation_list(consent.id):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={"error": "consent_revoked", "consent_id": consent.id},
                )

    return _dep


# ── SMART on FHIR scope backend ───────────────────────────────────────────

def require_smart_scope(*, scope: str):
    """
    Return a FastAPI dependency that enforces a SMART on FHIR scope on the
    inbound access token. Handles scope inheritance — `patient/*.read` covers
    `patient/Observation.read`, `user/*.*` covers everything.
    """

    # @audited(action="scope.check")
    def _dep(token_claims: dict = Depends("decode_token")) -> None:
        granted = set(str(token_claims.get("scope", "")).split())
        if _scope_covers(granted, scope):
            return
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": "insufficient_scope", "required": scope},
        )

    return _dep


def _scope_covers(granted: Iterable[str], required: str) -> bool:
    """SMART scope inheritance: patient/*.read covers patient/Observation.read."""
    if required in granted:
        return True
    try:
        ctx, op = required.split("/", 1)        # ctx="patient", op="Observation.read"
        resource, verb = op.rsplit(".", 1)      # resource="Observation", verb="read"
    except ValueError:
        return False

    candidates = {
        f"{ctx}/*.{verb}",          # patient/*.read
        f"{ctx}/*.*",               # patient/*.*
        f"{ctx}/{resource}.*",      # patient/Observation.*
        "user/*.*",                 # user/*.* covers patient/*.*
        f"user/{resource}.{verb}",
        f"user/{resource}.*",
        f"user/*.{verb}",
    }
    return bool(candidates & set(granted))


# ── helpers (stubs — wire to your project) ─────────────────────────────────

def _is_revoked_within(consent, now: datetime, max_age_seconds: int) -> bool:
    """Has the consent been touched recently? If not, recheck the revocation list."""
    return True


def _on_revocation_list(consent_id: str) -> bool:
    """Check the consent-revocation list (Redis set, Postgres table, etc.)."""
    return False


# ── usage example ─────────────────────────────────────────────────────────

# from fastapi import APIRouter
# router = APIRouter(prefix="/patients")
#
# @router.get(
#     "/{patient_id}/observations",
#     dependencies=[Depends(require_consent(scope="patient/Observation.read"))],
# )
# @audited(action="observation.list", resource_type="Observation")
# def list_observations(patient_id: str, db: Session = Depends(get_db)):
#     return db.query(Observation).filter_by(patient_id=patient_id).all()
