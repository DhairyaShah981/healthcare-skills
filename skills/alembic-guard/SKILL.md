---
name: alembic-guard
description: |
  Enforce safe Alembic migration practice: revision IDs ≤32 chars, linear chain
  (no parallel-branch divergence), explicit downgrade behaviour, no PHI in
  comments. Use when the user runs `alembic revision`, writes / reviews a
  migration, or hits an Alembic-related production error.
when_to_use: |
  Activate when the user:
  - Runs / mentions `alembic revision`, `alembic upgrade`, `alembic merge`
  - Writes or reviews a new migration file
  - Hits an error like "string longer than 32 chars" on `alembic_version`
  - Mentions migration conflict, divergent heads, or branch merge in DB context
  - Asks "is this migration safe?"
allowed-tools: [Read, Grep, Edit, Bash]
license: MIT
tags: [db, migration, alembic, linter]
incident: |
  Three separate production deploys crashed on Postgres because the Alembic
  revision ID exceeded 32 characters — `alembic_version.version_num` is
  `varchar(32)` by default. The crash happens at `alembic upgrade head`
  after deploy, leaving the DB in a half-migrated state. This linter catches
  the IDs before commit and also catches the second common Alembic disaster:
  parallel feature branches creating divergent migration chains that require
  manual merge.
---

# alembic-guard

> Catch the migration failures that take down deploys. Five rules, pre-commit, ten seconds.

## When to use

- The user runs `alembic revision` or commits a migration file.
- The user mentions Alembic, `alembic_version`, divergent heads, or migration merge.
- A deploy fails with "version_num too long" or "Multiple head revisions are present".
- The user asks how to safely add / rebase / squash migrations.

## How it works

Walk `alembic/versions/` and apply five rules. Each rule has an ID (`ALG-XXX`), a severity, and either a mechanical fix or a clear remediation.

### ALG-001 — Revision ID ≤ 32 chars (ERROR)

The default `alembic_version.version_num` column is `VARCHAR(32)`. Alembic stamps the column with whatever string is in `revision = "..."` at the top of a migration. Anything longer crashes at upgrade time on PostgreSQL (`ERROR:  value too long for type character varying(32)`).

**Check**: For every file in `alembic/versions/`, parse out `revision = "..."` and `down_revision = "..."`. Both must be ≤32 characters.

**Fix**: If the user wrote a descriptive ID (`"add_patient_consent_revocation_table_v2"` — 41 chars), suggest a hash-style ID with a comment:
```python
revision = "a4f2b9c1d7e3"        # add_patient_consent_revocation_table_v2
```

### ALG-002 — Linear chain (ERROR)

Multiple branches in `alembic/versions/` is fine *during* development, but only one `head` should exist on `main`. Detect:

```bash
alembic heads     # should return exactly one ID
```

**Fix**: If two heads exist, an `alembic merge -m "merge branches" <head1> <head2>` migration is required, and the merge must be committed before merge to main.

### ALG-003 — Explicit downgrade behaviour (WARN)

Every migration must have a `downgrade()` function. For irreversible operations (dropping data, schema changes that can't be rolled back), explicitly raise:

```python
def downgrade() -> None:
    raise RuntimeError("audit_event is append-only; downgrade not supported")
```

**Fix**: Generate a `downgrade()` skeleton; the human writes the real revert or the explicit `raise`.

### ALG-004 — No PHI in migration comments (ERROR)

Migrations sometimes describe what data they touch in comments or docstrings ("backfill SSN for patient #4421"). These comments end up in git history forever.

**Check**: Apply the `phi-redact` regex catalogue over every migration file. Any finding is a blocker.

**Fix**: Reword in non-identifying terms ("backfill SSN for one historical patient").

### ALG-005 — Data migrations use batching (WARN)

A bare `UPDATE patient SET … WHERE …` over a large table locks the table and blocks the application for the duration. Detect bare `UPDATE` / `DELETE` in `op.execute(...)` calls and recommend the chunked / cursor pattern:

```python
conn = op.get_bind()
while True:
    n = conn.execute(text("""
        UPDATE patient SET x = y WHERE id IN (
          SELECT id FROM patient WHERE x IS NULL LIMIT 1000
        )
    """)).rowcount
    if n == 0:
        break
```

## Example

**Input:** `alembic/versions/add_patient_consent_revocation_table_v2_with_signed_hash.py`
```python
"""add patient consent revocation table v2 with signed hash"""
revision = "add_patient_consent_revocation_table_v2_with_signed_hash"
down_revision = "abc123"
# Backfilling for patient Maria Hernandez (account 998812) per support ticket #4421
```

**Output:**
```
alembic-guard — add_patient_consent_revocation_table_v2_with_signed_hash.py
───────────────────────────────────────────────────────────────────────────
ALG-001  ERROR  revision is 54 chars (max 32)
   → revision = "add_consent_rev_v2"   # add_patient_consent_revocation_table_v2_with_signed_hash

ALG-004  ERROR  PHI in comment (NAME: "Maria Hernandez", ACCT: "998812")
   → reword: "Backfilling one historical patient row per support ticket #4421"

ALG-003  WARN   no downgrade() body
   → add a real downgrade or `raise RuntimeError("…")`

3 findings — 2 ERROR, 1 WARN
Verdict: BLOCK COMMIT
```

## Edge cases

- **`version_num` length isn't always 32.** Some projects override the column to `varchar(255)`. Detect via env config (`ALEMBIC_VERSION_NUM_LEN`); fall back to 32.
- **MySQL has a different limit.** MySQL's `varchar(32)` works the same way; SQLite has no limit but the lint still applies for cross-DB compatibility.
- **Auto-generated IDs.** Alembic's default IDs (`a1b2c3d4e5f6`) are 12 chars — never trip ALG-001 if you use the auto-gen.
- **Branch labels.** `branch_labels = ("clinic-os",)` lets you intentionally maintain parallel chains; ALG-002 should respect labelled branches.
- **Merge migrations.** Skip ALG-001 for files with `revises = (...)` (multiple parents); these are inherently merge migrations.
- **Long migration runs.** Anything that's not a fast metadata change should run in a release-train job, not in the boot path. Flag any migration with `op.execute(...)` over a large table.

## References

- Alembic docs: <https://alembic.sqlalchemy.org/en/latest/>
- The 32-char limit: `alembic.script.revision` module sets `LABEL_MAXLEN = 32`
- [`scripts/check_revision.py`](./scripts/check_revision.py) — pre-commit check
- [`examples/good-migration.py`](./examples/good-migration.py)
- [`examples/bad-migration.py`](./examples/bad-migration.py)
- ANSI SQL `VARCHAR` width compatibility — relevant when porting migrations cross-engine
