# HIPAA-REVIEW — `app/routes/patients.py`

| # | Section                  | Verdict |
|---|--------------------------|---------|
| 1 | Encryption at rest       | —       |
| 2 | Encryption in transit    | —       |
| 3 | Access control           | **FAIL** |
| 4 | Audit controls           | **FAIL** |
| 5 | Authentication           | —       |
| 6 | Integrity                | —       |
| 7 | Minimum necessary        | **FAIL** |
| 8 | Breach risk              | **FAIL** |

## Findings

### [§164.312(a)(1) FAIL] line 26 — missing access-control check
`get_patient` looks up any `patient_id` the caller passes without verifying the caller is authorized to view that patient.

→ Add an authorization check before the query, e.g.
```python
verify_caller_has_access(current_user, patient_id)
```
→ See `consent-gate` for a reusable FastAPI dependency.

### [§164.312(b) FAIL] line 26 — no audit trail
Reading a patient must be recorded in an immutable audit log.

→ Apply `@audited("patient.read", phi_args=("patient_id",))`.
→ See `audit-trail`.

### [§164.404 FAIL] line 28 — PHI in application log
`logger.info` interpolates `first_name`, `last_name`, and `dob` directly into a log line. If application logs ship to any vendor (Datadog, Sentry, Cloud Logging) without that data being scrubbed, this is a reportable breach.

→ Replace with structured logging:
```python
logger.info("patient.loaded", patient_id=patient_id)
```
→ Run `phi-redact` over recent log archives to confirm prior bleeds.

### [§164.502(b) WARN] line 29 — minimum-necessary
`return patient` exposes the entire `Patient` row, including fields the caller likely doesn't need.

→ Return a `PatientReadResponse` Pydantic schema with only the fields the API contract requires.

### [§164.312(a)(1) FAIL] line 33 — `export_patient_csv` raw SQL with string interpolation
SQL injection: `patient_id` is interpolated directly into the query string.

→ Use parameterised queries: `db.execute(text("SELECT * FROM patients WHERE id = :pid"), {"pid": patient_id})`.

### [§164.502(b) FAIL] line 33 — `SELECT *` on patients
Returns every column including SSN, full address, insurance — far beyond minimum necessary for a CSV export.

→ Enumerate explicit columns; align with the data-use contract for the export consumer.

### [§164.312(b) FAIL] line 33 — bulk export with no audit
A bulk patient export must record:
- who initiated the export
- the patient set involved
- the destination

→ Wrap with `@audited("patient.export", phi_args=("patient_id",))` and log the byte size + row count.

## Top-line verdict

**REQUEST CHANGES — 6 FAIL, 1 WARN.** Block merge until access-control, audit, SQL-injection, and logging issues are addressed.
