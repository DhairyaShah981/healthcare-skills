---
name: tenant-rls-guard
description: |
  Detect SQLAlchemy / ORM queries that read tenant-scoped tables without an
  explicit `client_id` / `tenant_id` / `org_id` predicate, even when Postgres
  RLS is also in place. Use when the user writes a query against a multi-tenant
  healthcare schema, reviews a route handler, or asks "is this query safe in
  multi-tenancy?".
when_to_use: |
  Activate when the user:
  - Writes a query against a tenant-scoped table (patient, encounter, appointment,
    observation, clinic_user, etc.)
  - Reviews a route handler or service method that loads patient data
  - Asks about Postgres RLS, multi-tenancy, or cross-tenant safety
  - Mentions "one tenant saw another tenant's data" (worst-case incident)
allowed-tools: [Read, Grep, Edit, Bash]
license: MIT
tags: [security, multi-tenancy, healthcare, db, linter]
incident: |
  A near-miss: a legacy query against `prior_auth` relied on Postgres RLS for
  tenant isolation, but a code path bypassed the session-context that set the
  RLS variable, opening a window for cross-tenant data exposure. RLS is great
  defense-in-depth but never the only line. This linter enforces explicit
  `client_id`/`tenant_id` predicates in code AND RLS as a belt-and-braces
  second layer.
---

# tenant-rls-guard

> Never trust RLS alone. Every multi-tenant query needs an explicit predicate in code.

## When to use

- The user writes a SQLAlchemy / Drizzle / Prisma / raw-SQL query against a tenant-scoped table.
- The user reviews a route handler that loads patient data.
- The user mentions Postgres RLS, multi-tenancy, or asks "what happens if a tenant ID is missing?".
- A security review flags cross-tenant exposure risk.

## How it works

1. **Inventory tenant-scoped tables.** The linter reads `.tenant-rls.yaml`:
   ```yaml
   tenant_column: client_id        # name used across this codebase
   scoped_tables:
     - patient
     - encounter
     - appointment
     - observation
     - condition
     - medication_request
     - audit_event
     - prior_auth
     - clinic_user
   exempt_tables:
     - migrations
     - alembic_version
     - feature_flag
   ```

2. **Walk every Python file under `app/` (or configured root).** For each SQLAlchemy `query(...)` / `select(...)` chain:
   - If the target table is in `scoped_tables`, verify there's a `.filter(...)` / `.where(...)` clause referencing `tenant_column` (e.g. `Patient.client_id == ...`).
   - For raw SQL (`text("SELECT * FROM patient ...")`), require a `WHERE client_id = :client_id` segment.

3. **Walk every Drizzle / Prisma file under `web/` (TS).** For each `.findMany()` / `.findUnique()` / `db.select().from(...)`:
   - If the target is scoped, verify there's a `where: { clientId: ... }` clause.

4. **Cross-check Postgres RLS is also enabled** on the scoped tables:
   ```sql
   SELECT relname FROM pg_class
   WHERE relname IN (...scoped_tables...)
     AND relrowsecurity = false;
   ```
   Tables with RLS *off* on scoped tables → ERROR. Both layers required.

5. **Detect RLS bypass.** `SECURITY DEFINER` functions, `BYPASSRLS` grants, and `SET ROLE` calls all bypass RLS — flag every appearance.

## Rules

| ID | Severity | Rule |
|---|---|---|
| RLS-001 | ERROR | Query against a tenant-scoped table has no `client_id` / `tenant_id` predicate in code. |
| RLS-002 | ERROR | Postgres RLS is *off* on a tenant-scoped table. Enable it. |
| RLS-003 | WARN | A function or grant uses `BYPASSRLS` / `SECURITY DEFINER` — review case-by-case. |
| RLS-004 | WARN | Raw SQL substitutes the tenant ID via f-string / `%` formatting (SQL-injection risk). |
| RLS-005 | INFO | RLS policy exists but the linter couldn't verify its predicate matches `client_id`. Manual review. |

## Example

**Bad:**
```python
# app/routes/observations.py
def list_observations(patient_id: str, db: Session):
    return db.query(Observation).filter_by(patient_id=patient_id).all()
```

**Output:**
```
tenant-rls-guard — app/routes/observations.py:5
RLS-001 ERROR  query(Observation) has no client_id predicate
   → add: .filter(Observation.client_id == current_client_id)
```

**Good:**
```python
def list_observations(patient_id: str, client_id: str, db: Session):
    return (
        db.query(Observation)
        .filter(Observation.client_id == client_id,
                Observation.patient_id == patient_id)
        .all()
    )
```

## Edge cases

- **System / cross-tenant queries.** Some queries genuinely span tenants (analytics, billing roll-ups). Annotate with a comment `# tenant-rls-guard: bypass=analytics` and the linter respects it (but logs the bypass for audit).
- **Subqueries.** A subquery against a scoped table must also filter by tenant. Walk inner queries too.
- **Joins.** Joining `Patient` to `Encounter` where both are scoped — both sides need the predicate, or the join condition must include the tenant column.
- **`get_by_id` patterns.** `db.get(Patient, patient_id)` doesn't go through the linter's query parser; treat any `db.get(<ScopedModel>, ...)` as RLS-001.
- **Drizzle / Prisma.** TS / JS users get a parallel linter (`scripts/check_tenant_rls.ts` — Tier 0 placeholder for v0.1, real impl in v0.3).
- **`current_setting('app.client_id')` is not enough.** RLS based on a session GUC can be bypassed if any code path forgets to set it. Always have the explicit predicate.

## References

- Postgres Row-Level Security: <https://www.postgresql.org/docs/current/ddl-rowsecurity.html>
- The "belt and braces" pattern (Lawrence Salberg, "Always use both"): explicit predicate + RLS.
- HIPAA §164.308(a)(4) — information access management
- [`scripts/check_tenant_rls.py`](./scripts/check_tenant_rls.py) — runnable linter
- [`examples/bad_query.py`](./examples/bad_query.py) / [`examples/good_query.py`](./examples/good_query.py)
