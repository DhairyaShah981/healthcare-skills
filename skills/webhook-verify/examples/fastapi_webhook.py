"""FastAPI webhook endpoints with signature verification + replay protection."""
from __future__ import annotations

import json
import os

from fastapi import APIRouter, HTTPException, Request, status

# from healthcare_skills.audit_trail import audited
# from healthcare_skills.webhook_verify import verify
from webhook_verify import verify  # local reference impl

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


# ── Retell ────────────────────────────────────────────────────────────────

# @audited(action="webhook.retell.received")
@router.post("/retell")
async def retell_webhook(request: Request):
    raw = await request.body()
    secrets = [s for s in (os.environ.get("RETELL_WEBHOOK_SECRET"),
                           os.environ.get("RETELL_WEBHOOK_SECRET_PREV")) if s]
    if not verify("retell", raw, request.headers, secrets=secrets):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid signature")

    payload = json.loads(raw)
    event_id = payload.get("event_id") or payload.get("call_id")
    if event_id and _seen(event_id):
        return {"ok": True, "duplicate": True}

    # Process the event (call.completed, call.transferred, ...)
    return {"ok": True}


# ── Stripe ────────────────────────────────────────────────────────────────

@router.post("/stripe")
async def stripe_webhook(request: Request):
    raw = await request.body()
    if not verify("stripe", raw, request.headers,
                  secrets=[os.environ["STRIPE_WEBHOOK_SECRET"]]):
        raise HTTPException(401, "invalid signature")
    return {"ok": True}


# ── Twilio (form-encoded) ─────────────────────────────────────────────────

@router.post("/twilio")
async def twilio_webhook(request: Request):
    raw = await request.body()
    form = await request.form()
    full_url = str(request.url)
    if not verify("twilio", raw, request.headers,
                  secrets=[os.environ["TWILIO_AUTH_TOKEN"]],
                  url=full_url, form_params=dict(form)):
        raise HTTPException(401, "invalid signature")
    return {"ok": True}


# ── replay protection stub ────────────────────────────────────────────────

def _seen(event_id: str) -> bool:
    """Lookup in Redis / DB with TTL = max replay window (usually 24h)."""
    return False
