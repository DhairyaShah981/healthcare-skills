"""
smart_oauth_fastapi.py — reference SMART on FHIR launch + token lifecycle.

Endpoints:
  GET  /smart/launch      — entry from EHR; persist iss+launch+state, redirect to authorize
  GET  /smart/callback    — exchange code for tokens; persist Fernet-encrypted
  POST /smart/refresh     — manual refresh
  POST /smart/logout      — revoke + clear

Storage: SQLAlchemy + Fernet at rest.
PKCE: enforced (S256).
Auto-refresh on 401: wired via `EhrFhirClient.fetch()` wrapper.

Production hardening (not shown): rate limiting on /callback, JWKS for asymmetric
client auth (SMART 2.0 private_key_jwt), session cookies with Secure+HttpOnly+SameSite.
"""
from __future__ import annotations

import base64
import hashlib
import os
import secrets
import time
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx
from cryptography.fernet import Fernet
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse

# Replace with your project's modules:
# from app.db import SessionLocal, get_db
# from app.models.smart import SmartSession
# from healthcare_skills.audit_trail import audited

CLIENT_ID    = os.environ["SMART_CLIENT_ID"]
REDIRECT_URI = os.environ["SMART_REDIRECT_URI"]
SCOPES       = os.environ.get("SMART_SCOPES",
                              "launch openid fhirUser patient/*.read offline_access")
FERNET       = Fernet(os.environ["SMART_FERNET_KEY"].encode())

router = APIRouter(prefix="/smart", tags=["smart"])


# ── pkce helpers ──────────────────────────────────────────────────────────

def _pkce_pair() -> tuple[str, str]:
    verifier = secrets.token_urlsafe(64)
    challenge = base64.urlsafe_b64encode(
        hashlib.sha256(verifier.encode()).digest()
    ).rstrip(b"=").decode()
    return verifier, challenge


# ── well-known config (cached) ────────────────────────────────────────────

_well_known_cache: dict[str, tuple[dict, float]] = {}

async def _smart_config(iss: str) -> dict:
    now = time.time()
    cached = _well_known_cache.get(iss)
    if cached and now - cached[1] < 3600:
        return cached[0]
    async with httpx.AsyncClient(timeout=10) as cli:
        r = await cli.get(f"{iss.rstrip('/')}/.well-known/smart-configuration")
        r.raise_for_status()
    cfg = r.json()
    _well_known_cache[iss] = (cfg, now)
    return cfg


# ── /launch — EHR enters here ─────────────────────────────────────────────

@router.get("/launch")
async def launch(request: Request, iss: str, launch: str | None = None) -> RedirectResponse:
    cfg = await _smart_config(iss)
    state = secrets.token_urlsafe(32)
    verifier, challenge = _pkce_pair()

    request.session.update({"state": state, "verifier": verifier, "iss": iss})
    params = {
        "response_type": "code",
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "scope": SCOPES,
        "aud": iss,
        "state": state,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
    }
    if launch:
        params["launch"] = launch

    auth = cfg["authorization_endpoint"]
    return RedirectResponse(f"{auth}?{httpx.QueryParams(params)}")


# ── /callback — exchange code for tokens ──────────────────────────────────

# @audited(action="smart.callback")
@router.get("/callback")
async def callback(request: Request, code: str, state: str) -> RedirectResponse:
    expected = request.session.pop("state", None)
    if state != expected:
        raise HTTPException(400, "state mismatch")

    iss = request.session["iss"]
    verifier = request.session.pop("verifier", "")
    cfg = await _smart_config(iss)

    async with httpx.AsyncClient(timeout=10) as cli:
        r = await cli.post(cfg["token_endpoint"], data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": REDIRECT_URI,
            "client_id": CLIENT_ID,
            "code_verifier": verifier,
        }, headers={"Accept": "application/json"})
    if r.status_code != 200:
        raise HTTPException(400, f"token exchange failed: {r.status_code}")
    tok = r.json()

    session = _persist_session(
        iss=iss,
        fhir_url=iss,
        patient_id=tok.get("patient"),
        scopes=tok.get("scope", "").split(),
        access_token=tok["access_token"],
        refresh_token=tok.get("refresh_token"),
        expires_at=datetime.now(tz=timezone.utc) + timedelta(seconds=tok.get("expires_in", 3600)),
        id_token=tok.get("id_token"),
    )
    request.session["smart_session_id"] = session.id
    return RedirectResponse("/")


# ── /refresh ──────────────────────────────────────────────────────────────

# @audited(action="smart.refresh")
@router.post("/refresh")
async def refresh(request: Request) -> dict[str, Any]:
    sess = _current_session(request)
    if not sess.refresh_token_enc:
        raise HTTPException(400, "no refresh token on this session")
    cfg = await _smart_config(sess.iss)
    refresh_token = FERNET.decrypt(sess.refresh_token_enc.encode()).decode()
    async with httpx.AsyncClient(timeout=10) as cli:
        r = await cli.post(cfg["token_endpoint"], data={
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": CLIENT_ID,
        }, headers={"Accept": "application/json"})
    if r.status_code != 200:
        raise HTTPException(401, "refresh failed; re-launch required")
    tok = r.json()
    sess.access_token_enc = FERNET.encrypt(tok["access_token"].encode()).decode()
    if tok.get("refresh_token"):
        sess.refresh_token_enc = FERNET.encrypt(tok["refresh_token"].encode()).decode()
    sess.expires_at = datetime.now(tz=timezone.utc) + timedelta(seconds=tok.get("expires_in", 3600))
    _commit(sess)
    return {"expires_at": sess.expires_at.isoformat()}


# ── /me ───────────────────────────────────────────────────────────────────

@router.get("/me")
async def me(request: Request) -> dict[str, Any]:
    sess = _current_session(request)
    return {
        "iss": sess.iss,
        "patient": sess.patient_id,
        "scopes": sess.scopes,
        "fhir_url": sess.fhir_url,
        "expires_at": sess.expires_at.isoformat(),
    }


# ── /logout ───────────────────────────────────────────────────────────────

# @audited(action="smart.logout")
@router.post("/logout")
async def logout(request: Request) -> dict[str, str]:
    sess = _current_session(request)
    cfg = await _smart_config(sess.iss)
    revocation_url = cfg.get("revocation_endpoint")
    if revocation_url and sess.refresh_token_enc:
        async with httpx.AsyncClient(timeout=5) as cli:
            await cli.post(revocation_url, data={
                "token": FERNET.decrypt(sess.refresh_token_enc.encode()).decode(),
                "client_id": CLIENT_ID,
            })
    _delete_session(sess.id)
    request.session.pop("smart_session_id", None)
    return {"status": "logged out"}


# ── EHR client with auto-refresh on 401 ───────────────────────────────────

class EhrFhirClient:
    def __init__(self, session) -> None:
        self.session = session

    async def fetch(self, path: str, **kw) -> httpx.Response:
        access = FERNET.decrypt(self.session.access_token_enc.encode()).decode()
        async with httpx.AsyncClient(base_url=self.session.fhir_url, timeout=15) as cli:
            r = await cli.get(path, headers={"Authorization": f"Bearer {access}", **kw.pop("headers", {})}, **kw)
        if r.status_code == 401:
            await refresh_session(self.session)
            access = FERNET.decrypt(self.session.access_token_enc.encode()).decode()
            async with httpx.AsyncClient(base_url=self.session.fhir_url, timeout=15) as cli:
                r = await cli.get(path, headers={"Authorization": f"Bearer {access}"})
        return r


# ── persistence stubs (wire to your project) ──────────────────────────────

def _persist_session(**kw) -> Any:
    """Stub — replace with your project's SmartSession insert.

    Encrypt tokens with FERNET *before* writing. Never store plaintext.
    """
    raise NotImplementedError("wire to your project's DB")


def _current_session(request: Request) -> Any:
    """Stub — load SmartSession by request.session['smart_session_id']."""
    raise NotImplementedError


def _commit(sess) -> None:
    raise NotImplementedError


def _delete_session(session_id) -> None:
    raise NotImplementedError


async def refresh_session(sess) -> None:
    raise NotImplementedError
