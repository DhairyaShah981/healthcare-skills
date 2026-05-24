# AuditEvent — schema and migration

A single, append-only table that records every PHI-touching action. The schema is designed to:
- Carry **no PHI** in the row itself (only hashed argument digests + opaque IDs)
- Be **indexed for the two queries that matter** (actor-over-time, resource-over-time)
- Map cleanly to FHIR R4 [`AuditEvent`](https://www.hl7.org/fhir/R4/auditevent.html) when audit data needs to be exchanged

## SQL — PostgreSQL

```sql
CREATE TABLE audit_event (
    id              TEXT PRIMARY KEY,                  -- ULID, sortable by time
    ts              TIMESTAMPTZ NOT NULL DEFAULT now(),
    actor_id        TEXT NOT NULL,                     -- "user:42" / "service:appointments-worker"
    actor_type      TEXT NOT NULL,                     -- 'user' | 'service' | 'system'
    on_behalf_of    TEXT,                              -- optional impersonation chain
    action          TEXT NOT NULL,                     -- "patient.read", "lab.export", "appointment.create"
    resource_type   TEXT,                              -- "Patient", "Encounter", "Observation"
    resource_id     TEXT,                              -- "patient:9981" (opaque)
    args_hash       TEXT,                              -- SHA-256 hex of stringified PHI args (+ salt)
    args_verbose    JSONB,                             -- ONLY populated when AUDIT_VERBOSE=true (debug)
    outcome         TEXT NOT NULL,                     -- 'success' | 'failure' | 'partial'
    error           TEXT,                              -- error class + message (PHI-scrubbed)
    duration_ms     INTEGER,
    trace_id        TEXT,                              -- correlate to observability backend
    span_id         TEXT,
    ip              INET,
    user_agent      TEXT,
    request_id      TEXT,
    deployment      TEXT,                              -- 'prod' | 'staging' | 'local'

    -- integrity (optional, see §164.312(c)(2))
    prev_hash       TEXT,                              -- hash of immediately prior row's signed_hash
    signed_hash     TEXT                               -- HMAC(prev_hash + row fields, AUDIT_HMAC_KEY)
);

CREATE INDEX audit_event_actor_ts_idx     ON audit_event (actor_id, ts DESC);
CREATE INDEX audit_event_resource_ts_idx  ON audit_event (resource_type, resource_id, ts DESC);
CREATE INDEX audit_event_action_ts_idx    ON audit_event (action, ts DESC);
CREATE INDEX audit_event_trace_idx        ON audit_event (trace_id);

-- prevent UPDATE / DELETE (Postgres-specific; pair with app-level enforcement)
REVOKE UPDATE, DELETE ON audit_event FROM PUBLIC;
```

## Alembic migration

```python
"""create audit_event"""
from alembic import op
import sqlalchemy as sa

revision = "audit_event_v1"               # ≤32 chars, see alembic-guard skill
down_revision = "<prior>"

def upgrade() -> None:
    op.create_table(
        "audit_event",
        sa.Column("id", sa.Text, primary_key=True),
        sa.Column("ts", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("actor_id", sa.Text, nullable=False),
        sa.Column("actor_type", sa.Text, nullable=False),
        sa.Column("on_behalf_of", sa.Text),
        sa.Column("action", sa.Text, nullable=False),
        sa.Column("resource_type", sa.Text),
        sa.Column("resource_id", sa.Text),
        sa.Column("args_hash", sa.Text),
        sa.Column("args_verbose", sa.dialects.postgresql.JSONB),
        sa.Column("outcome", sa.Text, nullable=False),
        sa.Column("error", sa.Text),
        sa.Column("duration_ms", sa.Integer),
        sa.Column("trace_id", sa.Text),
        sa.Column("span_id", sa.Text),
        sa.Column("ip", sa.dialects.postgresql.INET),
        sa.Column("user_agent", sa.Text),
        sa.Column("request_id", sa.Text),
        sa.Column("deployment", sa.Text),
        sa.Column("prev_hash", sa.Text),
        sa.Column("signed_hash", sa.Text),
    )
    op.create_index("audit_event_actor_ts_idx", "audit_event", ["actor_id", "ts"])
    op.create_index("audit_event_resource_ts_idx", "audit_event", ["resource_type", "resource_id", "ts"])
    op.create_index("audit_event_action_ts_idx", "audit_event", ["action", "ts"])
    op.create_index("audit_event_trace_idx", "audit_event", ["trace_id"])

def downgrade() -> None:
    # Auditors do not allow audit tables to be silently dropped.
    raise RuntimeError("audit_event is append-only; downgrade not supported")
```

## SQLite minimal variant (for local dev)

```sql
CREATE TABLE audit_event (
    id            TEXT PRIMARY KEY,
    ts            TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    actor_id      TEXT NOT NULL,
    actor_type    TEXT NOT NULL,
    action        TEXT NOT NULL,
    resource_type TEXT,
    resource_id   TEXT,
    args_hash     TEXT,
    outcome       TEXT NOT NULL,
    error         TEXT,
    trace_id      TEXT
);
CREATE INDEX audit_event_actor_ts_idx ON audit_event (actor_id, ts);
CREATE INDEX audit_event_resource_ts_idx ON audit_event (resource_type, resource_id, ts);
```

## FHIR mapping (if you need to export)

| AuditEvent column | FHIR `AuditEvent` path |
|---|---|
| `ts` | `recorded` |
| `actor_id` | `agent[0].who.identifier.value` |
| `actor_type` | `agent[0].type.coding.code` (`110150` Application, `humanuser`, etc.) |
| `action` | `type.code` + `subtype.code` |
| `resource_type` + `resource_id` | `entity[0].what.reference` |
| `outcome` | `outcome` (`0` success, `4` minor, `8` serious, `12` major) |
| `error` | `outcomeDesc` |
| `ip` | `agent[0].network.address` |

Most internal audit shouldn't be FHIR-formatted (too heavyweight); convert only when an external system needs it.
