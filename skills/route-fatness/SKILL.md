---
name: route-fatness
description: |
  Enforce thin route handlers in FastAPI / Express / Flask / Django: warn when
  any route function exceeds ~30 lines, has more than one nested branching
  concern, or directly orchestrates business logic instead of delegating to
  a service layer. Use when the user reviews a route handler, adds a new
  endpoint, or asks how to refactor a "monster" handler.
when_to_use: |
  Activate when the user:
  - Adds or reviews a route handler in FastAPI / Express / Flask / Django
  - Writes a route function that mixes auth, DB, external calls, business
    rules, and response shaping
  - Asks to refactor a long endpoint
  - Mentions "service layer", "clean architecture", or "extract method"
allowed-tools: [Read, Grep, Edit, Bash]
license: MIT
tags: [architecture, linter, healthcare, refactor]
incident: |
  A single route handler grew to 135 lines spanning four concerns: patient
  lookup, creation, approval, ECW queueing, and fax dispatch. It became
  untestable (no place to mock without monkey-patching), unrefactorable
  (every change risked one of the four flows), and the source of three
  separate production bugs. Rule: routes should be glue, not logic — auth,
  validation, call-the-service, shape-response, return. Anything else
  belongs in a service module.
---

# route-fatness

> Routes are glue. Anything ≥ 30 lines is a service waiting to be born.

## When to use

- The user adds a new route / endpoint.
- The user reviews a route handler with multiple branches, DB calls, and external API calls.
- The user asks "how should I split this up?".
- A code review flags a fat handler.

## How it works

1. **Walk every Python file** under `app/routes/` / `app/api/` / `web/routes/` (or configured roots).

2. **Identify route handlers.** Patterns:
   - FastAPI / Starlette: `@router.<method>(...)`, `@app.<method>(...)`
   - Flask: `@app.route(...)`, `@blueprint.route(...)`
   - Django: `class <Name>View`, `def <name>(request, ...)`
   - Express (TS): `app.<method>(path, async (req, res) => {...})`, `router.<method>(...)`

3. **Run five checks per handler.**

| ID | Severity | Rule |
|---|---|---|
| RTF-001 | WARN | Handler body > 30 lines (configurable, default 30). |
| RTF-002 | ERROR | Handler makes > 1 external HTTP call (`requests.*`, `httpx.*`, `fetch`, `axios`). |
| RTF-003 | ERROR | Handler issues > 3 DB queries (`db.query`, `db.execute`, `Model.objects.*`). |
| RTF-004 | WARN | Handler has nested branching depth > 2 (an `if` inside a `for` inside an `if`). |
| RTF-005 | WARN | Handler has a try/except wrapping ≥ 20 lines (likely hiding multiple concerns). |

4. **Suggest the extraction.** Output:
   ```
   route-fatness — app/routes/referrals.py:35 approve_referral
     RTF-001 WARN  body is 135 lines (limit: 30)
     RTF-002 ERROR external calls: ['requests.post (ECW)', 'fax_client.send']
     RTF-003 ERROR db queries: 6
     Suggested service:
       app/services/referral_approval.py:
         class ApproveReferralService:
             def __init__(self, db, ecw_client, fax_client): ...
             def approve(self, referral_id: str, actor: User) -> ApprovedReferral: ...
     Route becomes:
       @router.post("/{id}/approve")
       @audited(action="referral.approve", resource_arg="id")
       def approve_referral(id: str, ..., svc: ApproveReferralService = Depends()):
           return ApproveResponse.model_validate(svc.approve(id, current_user))
   ```

5. **Don't auto-refactor.** Surface the suggestion; the human extracts.

## Example

**Bad (excerpt):**
```python
@router.post("/{id}/approve")
def approve_referral(id: str, body: ApproveBody, db: Session = Depends(get_db)):
    # 135 lines: lookup, validation, approval, ECW queue, fax dispatch, audit, …
    ref = db.query(Referral).filter_by(id=id).first()
    if not ref: raise HTTPException(404)
    if ref.status != "pending":
        raise HTTPException(400, "not pending")
    pt = db.query(Patient).filter_by(id=ref.patient_id).first()
    if not pt:
        pt = Patient(...)
        db.add(pt); db.flush()
    ref.status = "approved"
    ref.approved_at = now()
    db.commit()
    ecw_payload = {...}                       # 20 lines of ECW shaping
    requests.post(ECW_URL, json=ecw_payload)
    fax_payload = {...}                       # 18 lines of fax shaping
    fax_client.send(fax_payload)
    audit.write(...)
    return {"status": "approved", "fax_id": ...}
```

**Good:**
```python
# app/routes/referrals.py
@router.post("/{id}/approve", response_model=ApproveResponse)
@audited(action="referral.approve", resource_arg="id", resource_type="Referral")
def approve_referral(
    id: str,
    body: ApproveBody,
    current_user: User = Depends(auth),
    svc: ApproveReferralService = Depends(),
) -> ApproveResponse:
    return ApproveResponse.from_domain(svc.approve(id, body, actor=current_user))


# app/services/referral_approval.py
class ApproveReferralService:
    def __init__(self, db: Session, ecw: ECWClient, fax: FaxClient):
        self._db, self._ecw, self._fax = db, ecw, fax

    def approve(self, id: str, body: ApproveBody, *, actor: User) -> Referral:
        ref = self._load_pending(id)
        pt  = self._ensure_patient(ref)
        ref.approve(actor=actor)
        self._db.commit()
        self._ecw.queue(self._build_ecw_payload(ref, pt))
        self._fax.send(self._build_fax_payload(ref, pt))
        return ref
```

Now: testable (mock `ECWClient`, `FaxClient`), refactorable (swap fax for a queue without touching the route), reviewable (each method is a method-sized concern).

## Edge cases

- **Decorator stacking doesn't count toward line budget.** A handler with 5 decorators and a 25-line body is fine.
- **Pydantic schemas at the top of the file don't count.** Only the handler function body itself.
- **Some routes really are 40 lines** (input validation + complex response shape). Configure the threshold per repo via `.route-fatness.yaml`. Default 30 is a hint, not a law.
- **GraphQL resolvers and gRPC handlers are routes too.** Same rules apply.
- **Don't extract a service for a 35-line "list patients" endpoint.** A pure query + response transform is fine in the route. The trigger is *multiple concerns*, not raw line count.
- **Health checks / liveness probes are exempt.** Add a `# route-fatness: exempt` comment.

## References

- Hexagonal architecture / Ports & Adapters (Cockburn)
- Domain-Driven Design — service layer pattern
- "Clean Architecture" (Martin) — the dependency rule
- FastAPI best practices: <https://fastapi.tiangolo.com/tutorial/bigger-applications/>
- [`scripts/check_route_fatness.py`](./scripts/check_route_fatness.py) — runnable linter
- [`examples/bad_route.py`](./examples/bad_route.py) / [`examples/good_route.py`](./examples/good_route.py)
- See also: `tenant-rls-guard`, `audit-trail` (compose at the route layer)
