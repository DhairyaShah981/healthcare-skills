---
name: migration-bisect
description: |
  Bisect a chain of Alembic / Django / Drizzle migrations to find the one
  that broke a deploy: run upgrades one at a time against an ephemeral DB,
  run a smoke probe after each, and report the first migration whose
  upgrade or smoke fails. Use when a deploy fails on `alembic upgrade
  head`, a table ends up in an unexpected state, or the user asks
  "which migration broke this?".
when_to_use: |
  Activate when the user:
  - Reports a deploy failed at the migration step
  - Asks "which migration broke X?"
  - Has a chain of N migrations and only one of them is suspect
  - Mentions schema drift, half-applied migrations, or `alembic downgrade`
    + re-upgrade debugging
allowed-tools: [Read, Write, Edit, Bash]
license: MIT
tags: [db, migration, alembic, debugging]
incident: |
  A deploy went out with eight new Alembic revisions; the production DB
  ended up in a half-migrated state and the team spent a day reading
  migration files to find the culprit. With a bisect harness, the answer
  is automated: spin up an ephemeral DB, run upgrades one-by-one with a
  smoke probe (the failing query or feature flag), and the first failing
  step is your bug.
---

# migration-bisect

> `git bisect` for migrations. Spin up an ephemeral DB; run upgrades one at a time; first failing step wins.

## When to use

- A deploy failed on `alembic upgrade head` and the chain includes multiple new revisions.
- A schema looks wrong after a deploy and the user needs to attribute it.
- The user has a smoke probe (a query, a feature flag, a test) that distinguishes "broken" from "working".

## How it works

1. **Spin up an ephemeral DB.** Docker is easiest:
   ```bash
   docker run -d --name pg-bisect -e POSTGRES_PASSWORD=p -p 5433:5432 postgres:16
   export DATABASE_URL=postgresql://postgres:p@localhost:5433/postgres
   ```
   For SQLite, just a temp file. The point: an isolated DB that can be reset between iterations.

2. **List the candidate revisions.** From the last known-good revision to the suspected-broken head:
   ```bash
   alembic history -r <last_good>:head --rev-range
   ```

3. **Define a smoke probe.** A bash command (or Python function) that exits 0 when the DB is "working" and non-zero when "broken". Examples:
   - Run a specific query that should succeed: `psql "$DATABASE_URL" -c "SELECT 1 FROM patient_consent LIMIT 1"`
   - Run a small Python script that imports the model and queries it
   - Run a single pytest case that hits the affected code path

4. **Walk the chain.** For each revision in order:
   ```bash
   alembic -c alembic.ini upgrade <rev>      # apply just this revision
   bash smoke_probe.sh                       # exit 0 → continue; exit ≠ 0 → STOP
   ```
   The first revision where smoke fails is the culprit.

5. **Report.** Output:
   ```
   migration-bisect — 8 revisions tested
   ─────────────────────────────────────
   a1b2c3d4   PASS   add_patient_consent
   d4e5f6a1   PASS   add_audit_event
   f1a2b3c4   PASS   add_referral_status
   c4d5e6f1   FAIL   add_consent_index           ← first failure
                   smoke: psql exit 1 — relation "patient_consent" does not exist
                          (likely: this migration's CREATE INDEX references a column the
                          previous migration didn't add)
   ```

6. **Don't auto-fix.** Bisect identifies; the human fixes. Suggested next steps:
   - Open the failing revision file
   - Check it doesn't reference a relation/column added by a *later* revision (out-of-order chain bug)
   - Check ALG-001..005 (compose with `alembic-guard`)

## Example

```bash
# from your repo root
python -m migration_bisect \
    --alembic-ini alembic.ini \
    --from a1b2c3d4 \
    --to head \
    --smoke 'psql "$DATABASE_URL" -c "SELECT 1 FROM patient_consent LIMIT 1"' \
    --ephemeral-db docker

# output:
# Spinning up ephemeral postgres on :5433...
# Applying a1b2c3d4 (add_patient_consent)...      PASS
# Applying d4e5f6a1 (add_audit_event)...          PASS
# Applying f1a2b3c4 (add_referral_status)...      PASS
# Applying c4d5e6f1 (add_consent_index)...        FAIL
#   smoke exit=1 stderr=ERROR: relation "patient_consent" does not exist
#
# First failing revision: c4d5e6f1 (add_consent_index)
# Suggested next step: open alembic/versions/c4d5e6f1_*.py
```

## Edge cases

- **Some smoke probes need seed data.** Run seeds in a `--pre-smoke` step before the first migration, not between every migration.
- **Migrations that take minutes to run.** Bisect linearly is O(N) on the chain length; for very long chains, true bisect-halving is faster but only works when the smoke is deterministic.
- **Branch / merge migrations.** A merge revision combines multiple parents; bisect treats it as a single step.
- **Down-migrations that aren't safe.** Some `downgrade()` functions destroy data. The harness always starts from a fresh ephemeral DB, never downgrades.
- **Smoke probes that read from external services.** Stub external calls; the smoke probe should fail only because of schema, not because of a flapping API.
- **CI environment differences.** Run bisect in the same Postgres version as production; some bugs only manifest on specific minor versions.

## References

- Alembic operations: <https://alembic.sqlalchemy.org/en/latest/ops.html>
- `git bisect` documentation (the inspiration)
- [`scripts/bisect_migrations.sh`](./scripts/bisect_migrations.sh) — bash harness
- [`scripts/bisect_migrations.py`](./scripts/bisect_migrations.py) — Python harness with Postgres/SQLite support
- Compose with: `alembic-guard` (pre-commit catches some of these), `jsonb-pydantic-pair` (schema-shape checks)
