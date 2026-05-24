---
name: audit-trail
description: |
  Add HIPAA-compliant audit logging to any function that reads, writes, or
  exports patient data. Use when the user asks to "add audit logging", "track
  who accessed this patient", "make this HIPAA-auditable", or works on a function
  that touches PHI without an existing audit decorator.
when_to_use: |
  Activate when the user:
  - Asks to add audit logging, access logging, or "track who did what"
  - Is writing a route handler, service method, or background job that touches PHI
  - References §164.312(b) (HIPAA audit controls) or asks how to satisfy it
  - Is responding to a security review finding about missing audit trail
  - Wants to add a Provenance / AuditEvent FHIR resource
allowed-tools: [Read, Write, Edit, Bash]
license: MIT
tags: [hipaa, audit, healthcare, compliance, fhir]
incident: |
  Without a per-function audit trail, post-incident forensics required ad-hoc
  structlog grep across multiple services and PHI got bled into raw logs to
  "make grep work better." The result was both bad forensics AND bad
  log-hygiene. This skill installs a single `@audited()` decorator + an
  AuditEvent table that gives forensics by trace ID without leaking PHI.
---

# audit-trail

> One decorator, one table, full HIPAA §164.312(b) coverage. PHI never enters the audit row.

## When to use

- The user is adding (or reviewing) a function that reads, writes, exports, or shares patient data.
- The user asks how to satisfy HIPAA §164.312(b) "audit controls" in code.
- A security review flagged "no audit trail" on a patient endpoint.
- The user mentions Provenance, AuditEvent, or HHS-style activity logs.

## How it works

1. **Install once: AuditEvent table.** Add the canonical audit schema (or its existing equivalent) to the project. Schema and migration in [`references/audit-event-schema.md`](./references/audit-event-schema.md).

2. **Wrap functions with `@audited`.** Apply the decorator to *every* function that touches PHI — route handlers, service methods, background jobs, exporters. Argument shape:
   ```python
   @audited(action="patient.read", phi_args=("patient_id",))
   def get_patient(patient_id: str, *, current_user: User, ...): ...
   ```

3. **Never log PHI into audit rows.** The decorator's `phi_args` list names parameters whose values are PHI. Those parameters are **hashed** (SHA-256, optionally with a per-deployment salt) into `args_hash`, never stored raw. The audit row carries the *fact of access*, not the *content of access*.

4. **Capture the actor every time.** Every audit row needs:
   - `actor_id` — the authenticated user / service that initiated the action
   - `actor_type` — `user`, `service`, `system`
   - `on_behalf_of` — when an admin acts as a clinician acting for a patient (rare but real)
   The decorator extracts this from a thread-local / contextvar / request context — never trust a passed argument for actor identity.

5. **Correlate to a trace ID.** Every row carries `trace_id` (and optionally `span_id`) so an investigator can join the audit table to whatever observability backend the org uses (Honeycomb, Langfuse, Datadog).

6. **Append-only.** Never `UPDATE` or `DELETE` from the audit table. If a row is wrong, append a correcting row. This is required for evidentiary integrity (§164.312(c)).

7. **Retain for 6 years.** HIPAA retention is six years from creation. Move old rows to cold storage; don't delete.

8. **Index for the right access patterns.** The two queries auditors actually run:
   - "Everything user X did in the last 24 hours" → index on `(actor_id, ts)`
   - "Who accessed patient Y?" → index on `(resource_id, ts)`

## Example

**Before**
```python
# app/routes/patients.py
@router.get("/{patient_id}")
def get_patient(patient_id: str, current_user: User = Depends(auth), db: Session = Depends(get_db)):
    return db.query(Patient).filter_by(id=patient_id).first()
```

**After**
```python
# app/routes/patients.py
from healthcare_skills.audit_trail import audited

@router.get("/{patient_id}")
@audited(action="patient.read", phi_args=("patient_id",))
def get_patient(patient_id: str, current_user: User = Depends(auth), db: Session = Depends(get_db)):
    return db.query(Patient).filter_by(id=patient_id).first()
```

The resulting audit row:
```json
{
  "id": "01HF7T9X3K4P5VWQGN2EBAR8M0",
  "ts": "2026-05-24T08:14:22.183Z",
  "actor_id": "user:42",
  "actor_type": "user",
  "action": "patient.read",
  "resource_type": "Patient",
  "resource_id": "patient:9981",
  "args_hash": "sha256:af2b…",
  "trace_id": "01HF7T9X3K4P5VWQGN2EBAR8M0",
  "outcome": "success",
  "error": null,
  "ip": "10.42.0.117",
  "user_agent": "Mozilla/5.0 …"
}
```

Note what's **absent**: the patient's name, DOB, MRN, or any field value. The row records that user 42 read patient 9981; the patient's *content* lives in the application DB.

The full decorator implementation is in [`examples/audited_decorator.py`](./examples/audited_decorator.py) (Python / FastAPI) and `examples/audited_express.ts` (TypeScript / Express, sketch).

## Edge cases

- **Background jobs are still PHI access.** A cron job that emails appointment reminders reads patient data — wrap it with `@audited("appointment.reminder.sent")`.
- **Bulk operations.** An exporter that touches 5,000 patients should emit 5,000 audit rows, not one. The decorator should iterate over the patient set, not collapse them.
- **Failed reads still audit.** Authorization denials, 404s, and exceptions all produce a row with `outcome=failure`. "I tried to read patient X and was denied" is an important forensic signal.
- **Don't double-audit.** If `get_patient` calls `_load_patient_from_db`, only the outermost (public-facing) function should be `@audited`. Internal helpers shouldn't emit rows.
- **Service-to-service calls.** When service A calls service B with a patient ID, service B's audit row should record the *human* who initiated the chain via the trace context, not just "service A".
- **Audit log integrity itself matters.** Consider HMAC chaining or hashing each row with the prior row's hash to make tampering detectable (§164.312(c)(2)).
- **Don't audit synthetic data the same way.** When the deployment is `staging` or `local` and PHI is synthetic, you may relax retention / forensic requirements — but make this explicit via a `ENVIRONMENT` env var the decorator reads.

## References

- HIPAA §164.312(b) — audit controls
- HIPAA §164.312(c) — integrity
- FHIR R4 [Provenance](https://www.hl7.org/fhir/R4/provenance.html) and [AuditEvent](https://www.hl7.org/fhir/R4/auditevent.html) resources (use these when audit data needs to be exchanged with other systems)
- [`references/audit-event-schema.md`](./references/audit-event-schema.md) — SQL schema + Alembic migration
- [`examples/audited_decorator.py`](./examples/audited_decorator.py) — full Python decorator
- DICOM Audit Trail and Node Authentication (ATNA): the source of FHIR's AuditEvent design
- IHE [BALP profile](https://profiles.ihe.net/ITI/BALP/) — Basic Audit Log Patterns
