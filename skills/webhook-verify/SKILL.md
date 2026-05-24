---
name: webhook-verify
description: |
  Verify HMAC signatures on inbound webhooks from Retell, Vapi, Twilio,
  Stripe, Slack, Segment, GitHub, and any generic HMAC-SHA256 webhook
  provider. Use when the user wires up a webhook endpoint, asks "how do
  I trust this callback?", or hits a webhook that processes patient data
  without verifying the sender.
when_to_use: |
  Activate when the user:
  - Wires up a webhook receiver endpoint
  - References Retell / Vapi / Twilio / Stripe / Slack signatures
  - Asks how to verify a webhook signature
  - Has a webhook that processes PHI / payments without verifying
  - Mentions HMAC-SHA256, X-Signature, Stripe-Signature, etc.
allowed-tools: [Read, Write, Edit, Bash]
license: MIT
tags: [security, webhooks, healthcare, hmac]
incident: |
  A webhook endpoint that processed appointment confirmations had no
  signature verification — any attacker who guessed the URL could create,
  modify, or cancel appointments. Even with a "secret" path the URL leaks
  via referrer headers, proxy logs, and CDN caches. This skill gives you
  the canonical HMAC verification pattern per provider, with constant-time
  comparison and replay-window enforcement.
---

# webhook-verify

> Constant-time HMAC + replay window. Per-provider quirks captured once.

## When to use

- The user adds a webhook receiver (Retell, Vapi, Twilio, Stripe, custom).
- The user asks how to verify a signature.
- The user has a webhook endpoint that processes patient data or money and skips verification.
- A security review flags an unauthenticated webhook.

## How it works

1. **Identify the provider.** Each has its own header convention and signing payload:

| Provider | Signature header | Signed string |
|---|---|---|
| Retell | `X-Retell-Signature` | `body` (raw bytes) |
| Vapi   | `X-Vapi-Signature` | `body` |
| Twilio | `X-Twilio-Signature` | `url + sorted POST params` (form) / `body` (JSON) |
| Stripe | `Stripe-Signature` | `timestamp.body`, parsed from header |
| Slack  | `X-Slack-Signature` + `X-Slack-Request-Timestamp` | `v0:{ts}:{body}` |
| GitHub | `X-Hub-Signature-256` | `body` |
| Segment | `X-Signature` | `body` |
| Generic | `X-Signature` | `body` (most-common default) |

2. **Read the body as raw bytes before parsing.** If you parse JSON first and then re-serialize, the byte sequence changes and the signature won't match. Always:
   ```python
   raw = await request.body()      # bytes
   if not verify(raw, request.headers):
       raise HTTPException(401)
   payload = json.loads(raw)
   ```

3. **Constant-time comparison.** `hmac.compare_digest(...)` in Python, `crypto.timingSafeEqual(...)` in Node. Never `==`.

4. **Enforce a replay window.** A valid signature on an *old* request is still a replay. Stripe and Slack include a timestamp in the signed string; reject anything > 5 minutes old. For providers that don't include a timestamp, the receiver should track recent request IDs and reject duplicates.

5. **Secret rotation.** Support N≥2 secrets simultaneously so you can rotate without downtime. Try each secret; accept if any matches.

6. **Return 401, not 400.** A failed signature is an *authentication* failure, not a malformed-request error. The provider can distinguish.

7. **Log without leaking.** Audit `webhook.received` and `webhook.rejected`; never log the signature, the body, or the secret prefix.

## Example — FastAPI middleware

```python
from fastapi import APIRouter, Request, HTTPException
from healthcare_skills.webhook_verify import verify

router = APIRouter()

@router.post("/webhooks/retell")
async def retell_webhook(request: Request):
    raw = await request.body()
    if not verify("retell", raw, request.headers, secrets=[settings.RETELL_SECRET]):
        raise HTTPException(401, "invalid signature")
    payload = json.loads(raw)
    # process payload (idempotent — see Edge cases)
    return {"ok": True}
```

`verify(...)` dispatches per-provider:
```python
def verify(provider: str, body: bytes, headers, *, secrets: list[str]) -> bool:
    impl = {"retell": _verify_hmac_sha256_hex,
            "vapi":   _verify_hmac_sha256_hex,
            "github": _verify_hub_signature_256,
            "stripe": _verify_stripe,
            "slack":  _verify_slack,
            "twilio": _verify_twilio,
            }[provider]
    return any(impl(body, headers, s) for s in secrets if s)
```

Full implementation in [`scripts/webhook_verify.py`](./scripts/webhook_verify.py).

## Edge cases

- **Idempotency keys.** A signature is necessary but not sufficient — the provider may legitimately retry. Use `Idempotency-Key` (or `delivery_id` / event ID) and dedupe.
- **JSON vs form-encoded.** Twilio signs the URL + sorted form params for form posts, but the raw body for JSON posts. Implement both.
- **URL canonicalisation matters.** Twilio's signature includes the URL the request hit; if you're behind a proxy that rewrites the path, you'll need to reconstruct the original URL.
- **Reverse proxies and TLS termination.** Don't trust `X-Forwarded-Host`/`X-Forwarded-Proto` blindly when reconstructing the URL.
- **Body bytes preserved through frameworks.** FastAPI / Express don't preserve raw bytes by default after parsing; use `request.body()` (FastAPI), `express.raw()` (Express), or a custom middleware.
- **Replay window enforcement.** Without a timestamp, you need a deduplication store (Redis with TTL). Don't skip this.
- **Secret in env, not in code.** Compose with `secrets-placeholder`.

## References

- Stripe webhook signing: <https://stripe.com/docs/webhooks/signatures>
- Slack request signing: <https://api.slack.com/authentication/verifying-requests-from-slack>
- Twilio validator: <https://www.twilio.com/docs/usage/webhooks/webhooks-security>
- GitHub X-Hub-Signature: <https://docs.github.com/en/webhooks/using-webhooks/validating-webhook-deliveries>
- Retell webhook docs: <https://docs.retellai.com/build/webhooks>
- [`scripts/webhook_verify.py`](./scripts/webhook_verify.py)
- [`examples/fastapi_webhook.py`](./examples/fastapi_webhook.py)
- Compose with: `secrets-placeholder`, `voice-agent-lint` (RTL-017 webhook secrets), `audit-trail`
