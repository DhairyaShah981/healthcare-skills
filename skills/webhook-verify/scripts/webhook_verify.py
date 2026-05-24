"""
webhook_verify.py — per-provider HMAC signature verification.

All verifiers:
  - operate on raw body bytes (parse JSON only AFTER verifying)
  - use hmac.compare_digest for constant-time comparison
  - accept a list of secrets to support rotation

Providers: retell, vapi, github, stripe, slack, twilio, segment, generic.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import time
import urllib.parse
from typing import Mapping


# ── generic HMAC-SHA256, hex-encoded ──────────────────────────────────────

def _verify_hmac_sha256_hex(body: bytes, headers: Mapping[str, str], secret: str,
                             *, header_name: str = "X-Signature") -> bool:
    sig = headers.get(header_name) or headers.get(header_name.lower())
    if not sig:
        return False
    expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(sig.lower(), expected.lower())


# ── GitHub X-Hub-Signature-256 ────────────────────────────────────────────

def _verify_hub_signature_256(body: bytes, headers: Mapping[str, str], secret: str) -> bool:
    sig = headers.get("X-Hub-Signature-256") or headers.get("x-hub-signature-256")
    if not sig or not sig.startswith("sha256="):
        return False
    expected = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(sig, expected)


# ── Stripe ────────────────────────────────────────────────────────────────

def _verify_stripe(body: bytes, headers: Mapping[str, str], secret: str,
                    *, max_age_seconds: int = 300) -> bool:
    header = headers.get("Stripe-Signature") or headers.get("stripe-signature")
    if not header:
        return False
    parts = dict(p.split("=", 1) for p in header.split(",") if "=" in p)
    ts = parts.get("t")
    v1 = parts.get("v1")
    if not ts or not v1:
        return False
    if abs(time.time() - int(ts)) > max_age_seconds:
        return False
    signed = f"{ts}.".encode() + body
    expected = hmac.new(secret.encode(), signed, hashlib.sha256).hexdigest()
    return hmac.compare_digest(v1, expected)


# ── Slack ─────────────────────────────────────────────────────────────────

def _verify_slack(body: bytes, headers: Mapping[str, str], secret: str,
                   *, max_age_seconds: int = 300) -> bool:
    sig = headers.get("X-Slack-Signature") or headers.get("x-slack-signature")
    ts = headers.get("X-Slack-Request-Timestamp") or headers.get("x-slack-request-timestamp")
    if not sig or not ts:
        return False
    try:
        if abs(time.time() - int(ts)) > max_age_seconds:
            return False
    except ValueError:
        return False
    base = f"v0:{ts}:".encode() + body
    expected = "v0=" + hmac.new(secret.encode(), base, hashlib.sha256).hexdigest()
    return hmac.compare_digest(sig, expected)


# ── Twilio ────────────────────────────────────────────────────────────────

def _verify_twilio(body: bytes, headers: Mapping[str, str], secret: str,
                    *, url: str | None = None,
                    form_params: Mapping[str, str] | None = None) -> bool:
    sig = headers.get("X-Twilio-Signature") or headers.get("x-twilio-signature")
    if not sig or not url:
        return False
    base = url
    if form_params:
        for k in sorted(form_params):
            base += k + form_params[k]
    digest = hmac.new(secret.encode(), base.encode(), hashlib.sha1).digest()
    expected = base64.b64encode(digest).decode()
    return hmac.compare_digest(sig, expected)


# ── dispatcher ────────────────────────────────────────────────────────────

def verify(provider: str, body: bytes, headers: Mapping[str, str], *,
            secrets: list[str], **kw) -> bool:
    """Return True if body+headers are validly signed under any of `secrets`."""
    impl: dict[str, callable] = {
        "retell":  lambda b, h, s: _verify_hmac_sha256_hex(b, h, s, header_name="X-Retell-Signature"),
        "vapi":    lambda b, h, s: _verify_hmac_sha256_hex(b, h, s, header_name="X-Vapi-Signature"),
        "github":  _verify_hub_signature_256,
        "stripe":  lambda b, h, s: _verify_stripe(b, h, s),
        "slack":   lambda b, h, s: _verify_slack(b, h, s),
        "twilio":  lambda b, h, s: _verify_twilio(b, h, s, url=kw.get("url"),
                                                  form_params=kw.get("form_params")),
        "segment": _verify_hmac_sha256_hex,
        "generic": _verify_hmac_sha256_hex,
    }
    fn = impl.get(provider.lower())
    if not fn:
        raise ValueError(f"unsupported provider: {provider}")
    for secret in secrets:
        if secret and fn(body, headers, secret):
            return True
    return False


# ── tiny self-test ────────────────────────────────────────────────────────

if __name__ == "__main__":
    body = b'{"event":"call.completed"}'
    secret = "shh"
    sig = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    assert verify("retell", body, {"X-Retell-Signature": sig}, secrets=[secret])
    assert not verify("retell", body, {"X-Retell-Signature": "deadbeef"}, secrets=[secret])
    print("ok")
