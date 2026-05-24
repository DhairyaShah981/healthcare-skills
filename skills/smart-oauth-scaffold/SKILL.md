---
name: smart-oauth-scaffold
description: |
  Scaffold a SMART on FHIR app launch: authorization endpoint, token exchange,
  Fernet-encrypted token storage, scope handling, and refresh-token rotation.
  Works against Epic, Cerner, Athena, Allscripts, Meditech, and the SMART
  Health IT sandbox. Use when the user asks to "add SMART on FHIR auth",
  "wire up Epic OAuth", "store refresh tokens safely", or builds a clinical
  app that launches from an EHR.
when_to_use: |
  Activate when the user:
  - Asks to add SMART on FHIR / Epic / Cerner OAuth to their app
  - Needs to handle EHR launch context (`launch`, `iss`, `aud`, patient context)
  - Wants to encrypt refresh tokens at rest
  - Is building a clinician-facing app that EHRs launch via OAuth
  - References standalone vs EHR launch, SMART scopes, or `fhir-url`
allowed-tools: [Read, Write, Edit, Bash]
license: MIT
tags: [smart, oauth, healthcare, fhir, security]
incident: |
  Epic OAuth implementations end up scattered across services with subtly
  different Fernet key handling, no refresh-rotation hygiene, and token rows
  stored plaintext in dev DBs that get snapshotted to staging. The same six
  endpoints get re-implemented per project, each with one or two bugs. This
  skill scaffolds the canonical shape once: `/launch`, `/callback`, encrypted
  storage, scope-checked endpoints, refresh on 401.
---

# smart-oauth-scaffold

> SMART on FHIR launch + token lifecycle, done correctly the first time. Fernet at rest, refresh-on-401, scope-gated.

## When to use

- The user is adding EHR OAuth (Epic, Cerner, Athena, etc.) to a service.
- The user references SMART on FHIR, EHR launch, standalone launch, or `iss`/`aud`.
- The user asks how to safely store refresh tokens.
- The user wants the canonical layout instead of pasting from a vendor doc.

## How it works

1. **Pin the spec.** SMART App Launch 2.0.0 at <https://hl7.org/fhir/smart-app-launch/STU2/>. Most US EHRs support 1.0; many support 2.0 partially. Default to 1.0 patterns + opt-in 2.0 where the EHR supports it.

2. **Decide launch type.**
   - **EHR launch** — EHR opens your app with `iss` (FHIR base) and `launch` (opaque). You fetch `.well-known/smart-configuration` from `iss`, redirect to `authorize`, exchange code for token.
   - **Standalone launch** — your app starts the flow itself; user picks a sandbox / patient.

3. **Generate the six endpoints + storage.**
   ```
   GET  /smart/launch          # entry: store iss+launch, redirect to authorize
   GET  /smart/callback        # exchange code → access+refresh+id_token
   GET  /smart/me              # introspect: who am I, what scopes, what patient
   POST /smart/refresh         # explicit refresh (auto-refresh on 401 preferred)
   POST /smart/logout          # revoke + clear local row
   GET  /.well-known/jwks.json # for asymmetric client auth (SMART 2.0)

   table  smart_session:
     id, user_id, iss, patient_id, scopes, fhir_url,
     access_token_enc, refresh_token_enc, expires_at, created_at, updated_at
   ```

4. **Encrypt tokens at rest with Fernet.** Use a per-deployment key in Secret Manager (see `secrets-placeholder`). Never store plaintext in dev DBs either — staging dumps from dev *will* leak.
   ```python
   from cryptography.fernet import Fernet
   fernet = Fernet(os.environ["SMART_FERNET_KEY"])
   row.access_token_enc = fernet.encrypt(access_token.encode()).decode()
   ```

5. **Verify `state` and PKCE.** Generate cryptographically-random `state` per launch; verify on callback. Use PKCE (`code_challenge` / `code_verifier`) — required by SMART 2.0, recommended for 1.0.

6. **Bind scopes to endpoints.** Every FHIR-touching endpoint in your app declares the SMART scopes it needs (e.g. `patient/Observation.read`); a middleware checks the session has them. Compose with the `consent-gate` skill's `require_smart_scope` dependency.

7. **Auto-refresh on 401.** Wrap your FHIR client so a 401 from the EHR triggers a refresh-token exchange and retry once. After the retry, persist the new tokens and update `expires_at`. On second 401, treat as session-expired and force re-launch.

8. **Rotate refresh tokens.** Many EHRs issue a new refresh token on each refresh. Store the new one immediately; an old refresh token is single-use.

9. **Log without leaking.** Audit `who.launched` / `who.refreshed` events (use `audit-trail`); never log the access / refresh / id token values, not even a prefix.

## Example — FastAPI sketch

```python
from fastapi import APIRouter, Request, HTTPException
from cryptography.fernet import Fernet
import secrets, httpx, jwt

router = APIRouter(prefix="/smart")
fernet = Fernet(os.environ["SMART_FERNET_KEY"])

@router.get("/launch")
async def launch(request: Request, iss: str, launch: str):
    cfg = (await httpx.AsyncClient().get(f"{iss}/.well-known/smart-configuration")).json()
    state = secrets.token_urlsafe(32)
    verifier = secrets.token_urlsafe(64)
    challenge = pkce_challenge(verifier)
    request.session["state"] = state
    request.session["verifier"] = verifier
    request.session["iss"] = iss
    return RedirectResponse(
        f"{cfg['authorization_endpoint']}?"
        f"response_type=code&client_id={CLIENT_ID}&redirect_uri={REDIRECT_URI}"
        f"&scope={QUOTED_SCOPES}&launch={launch}&aud={iss}"
        f"&state={state}&code_challenge={challenge}&code_challenge_method=S256"
    )

@router.get("/callback")
async def callback(request: Request, code: str, state: str):
    if state != request.session.get("state"):
        raise HTTPException(400, "bad state")
    iss = request.session["iss"]
    cfg = (await httpx.AsyncClient().get(f"{iss}/.well-known/smart-configuration")).json()
    resp = await httpx.AsyncClient().post(cfg["token_endpoint"], data={
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": REDIRECT_URI,
        "client_id": CLIENT_ID,
        "code_verifier": request.session["verifier"],
    })
    tok = resp.json()
    # tok contains: access_token, refresh_token (optional), expires_in,
    # patient (the launched patient), id_token (a JWT identifying the user)
    save_session(
        iss=iss,
        patient_id=tok.get("patient"),
        scopes=tok["scope"].split(),
        access_token_enc=fernet.encrypt(tok["access_token"].encode()).decode(),
        refresh_token_enc=fernet.encrypt(tok.get("refresh_token", "").encode()).decode(),
        expires_at=now() + timedelta(seconds=tok["expires_in"]),
        user_id=jwt.decode(tok["id_token"], options={"verify_signature": False}).get("sub"),
    )
    return RedirectResponse("/")
```

Full scaffold in [`examples/smart_oauth_fastapi.py`](./examples/smart_oauth_fastapi.py).

## Edge cases

- **`aud` parameter is required by some EHRs.** Epic rejects launches without `aud` set to `iss`.
- **EHR-specific quirks.** Cerner requires `Accept-Encoding: identity` on token endpoint in some configurations. Athena disables refresh tokens for sandbox apps. Document per-EHR gotchas in `references/ehr-quirks.md`.
- **Standalone launch without a patient.** When a clinician launches standalone, there's no patient context. Use SMART's `launch/patient` scope to prompt the EHR to pick one, or operate without.
- **PKCE is mandatory in SMART 2.0** and recommended in 1.0; never skip it.
- **Fernet key rotation.** Have a way to re-encrypt all rows when rotating the key — store a key-version with each row.
- **Token-endpoint authentication.** SMART 2.0 supports `private_key_jwt` (asymmetric); preferred over `client_secret` for production.
- **Don't expose `id_token` to the browser.** It contains user identity. Keep it server-side.
- **Refresh-token leakage.** A leaked refresh token = persistent access. Treat with same care as a primary credential.

## References

- SMART App Launch 2.0: <https://hl7.org/fhir/smart-app-launch/STU2/>
- SMART 1.0: <https://hl7.org/fhir/smart-app-launch/1.0.0/>
- SMART scopes: <https://hl7.org/fhir/smart-app-launch/scopes-and-launch-context.html>
- Epic on FHIR: <https://fhir.epic.com>
- Cerner FHIR: <https://fhir.cerner.com>
- SMART Health IT sandbox: <https://launch.smarthealthit.org/>
- 21st Century Cures Act §170.315(g)(10) — patient access API
- Compose with: `consent-gate` (scope enforcement), `audit-trail` (session events), `secrets-placeholder` (Fernet key)
- [`examples/smart_oauth_fastapi.py`](./examples/smart_oauth_fastapi.py)
- [`references/ehr-quirks.md`](./references/ehr-quirks.md)
