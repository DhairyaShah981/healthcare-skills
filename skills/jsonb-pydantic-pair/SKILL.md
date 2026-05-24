---
name: jsonb-pydantic-pair
description: |
  Lint SQLAlchemy models to enforce: every `Column(JSONB)` (or `Column(JSON)`)
  must have a paired Pydantic schema declared next to it, used as the runtime
  validator on read / write. Use when the user adds a JSONB column, reviews a
  model file, or asks "is this JSONB schema safe?".
when_to_use: |
  Activate when the user:
  - Adds or modifies a `Column(JSONB)` / `Column(JSON)` in a SQLAlchemy model
  - Reviews an existing model that uses JSONB
  - Hits a runtime `KeyError` from a JSONB blob
  - Asks "how do I validate this JSONB shape?"
  - Is auditing data integrity in a healthcare DB schema
allowed-tools: [Read, Grep, Edit, Bash]
license: MIT
tags: [db, linter, healthcare, sqlalchemy, pydantic]
incident: |
  A legacy schema accumulated 26+ `Column(JSONB)` columns with no Pydantic
  wrappers. Refactors became impossible because any change risked breaking an
  unknown consumer reading a specific key. Runtime `KeyError`s on missing
  fields showed up in patient-facing UI weeks after a backend change. This
  linter enforces the rule: a JSONB column without a Pydantic schema is a
  liability.
---

# jsonb-pydantic-pair

> JSONB without Pydantic is a footgun. Lint enforces the pairing.

## When to use

- The user adds a `Column(JSONB)` / `Column(JSON)` to a SQLAlchemy model.
- The user reviews a healthcare schema with JSONB columns.
- The user encounters `KeyError` / unexpected `None` from a JSONB blob.
- The user mentions "schemaless", "blob storage", or "we'll figure out the shape later".

## How it works

Walk every Python file under `app/models/` (or the configured model path) and find SQLAlchemy column declarations of `JSONB` / `JSON`. For each, verify a Pydantic schema is declared in the **same file** (or imported and referenced via a class attribute / `__schema__` marker).

### Rules

| ID | Severity | Rule |
|---|---|---|
| JBP-001 | ERROR | Every `Column(JSONB)` / `Column(JSON)` must have a paired Pydantic class in the same file. |
| JBP-002 | WARN | The Pydantic class should be referenced from the model via `__schemas__ = {"column": ClassName}` for runtime discoverability. |
| JBP-003 | ERROR | The Pydantic class must use `BaseModel` (not `TypedDict`, not plain `dict`). Pydantic gives validation + Field constraints. |
| JBP-004 | WARN | The model's `__init__` / property setter should validate via `Schema.model_validate(...)` on every write — not just at API ingress. |
| JBP-005 | WARN | Avoid `extra="allow"` on a healthcare JSONB schema — silently accepting unknown keys defeats the purpose. |

### Procedure

1. Parse each file as Python AST (`ast.parse`).
2. Find every `Column(...)` call where one of the positional args is `JSONB` / `JSON` (or the type is `JSONB()` / `JSON()`).
3. For that column's name, look for a Pydantic `class <Name>Schema(BaseModel)` in the same file.
4. If absent → JBP-001 ERROR.
5. Look for an `__schemas__` class attribute on the model mapping column-name → Pydantic class. If absent → JBP-002 WARN.
6. Check the Pydantic class itself: `BaseModel` parentage, `model_config`, presence of `extra="allow"`.

## Example

**Input (bad):**
```python
# app/models/encounter.py
class Encounter(Base):
    __tablename__ = "encounter"
    id = Column(Text, primary_key=True)
    patient_id = Column(Text, nullable=False)
    triage_data = Column(JSONB, nullable=False)        # ← naked JSONB
    metadata = Column(JSONB)
```

**Output:**
```
jsonb-pydantic-pair — app/models/encounter.py
─────────────────────────────────────────────
JBP-001  ERROR  triage_data: Column(JSONB) has no paired Pydantic schema
JBP-001  ERROR  metadata:    Column(JSONB) has no paired Pydantic schema
JBP-002  WARN   no __schemas__ mapping on Encounter
2 ERROR, 1 WARN
```

**Input (good):**
```python
# app/models/encounter.py
from pydantic import BaseModel, Field

class TriageDataSchema(BaseModel):
    urgency: str = Field(pattern=r"^(EMERGENT|URGENT|ROUTINE|SELF-CARE)$")
    rationale: str
    captured_at: datetime
    chief_complaints: list[str]

class EncounterMetadataSchema(BaseModel):
    source_system: str
    ingested_at: datetime
    integration_version: str

class Encounter(Base):
    __tablename__ = "encounter"
    id = Column(Text, primary_key=True)
    patient_id = Column(Text, nullable=False)
    triage_data = Column(JSONB, nullable=False)
    metadata = Column(JSONB)

    __schemas__ = {"triage_data": TriageDataSchema, "metadata": EncounterMetadataSchema}

    def __setattr__(self, name, value):
        schema = type(self).__schemas__.get(name) if hasattr(type(self), "__schemas__") else None
        if schema and value is not None and isinstance(value, dict):
            value = schema.model_validate(value).model_dump()
        super().__setattr__(name, value)
```

## Edge cases

- **`Column(JSON)` for tiny blobs.** Even a 3-field config blob should have a schema; the cost of writing one is trivial compared to the cost of a runtime `KeyError` in production.
- **Polymorphic JSONB** (e.g. an `event_data` column where shape varies by `event_type`). Use a `Union` Pydantic model or a discriminated union (`Field(discriminator="type")`).
- **`__schemas__` discovery.** Some teams use a separate `schemas/` directory; the lint should be configurable via `.jsonb-pair.yaml` to look in alternate paths.
- **JSON Schema generation.** `BaseModel.model_json_schema()` gives you the JSON Schema for the column for free; useful for Postgres `CHECK (jsonb_valid(triage_data, '...'))` constraints.
- **Don't lint test fixtures.** Files in `tests/` are exempt from JBP-002.
- **`Mapped[JSONB]` in SQLAlchemy 2.0 syntax** — detect that form too: `triage_data: Mapped[dict] = mapped_column(JSONB)`.

## References

- Pydantic v2 docs: <https://docs.pydantic.dev/2.0/>
- SQLAlchemy JSON / JSONB: <https://docs.sqlalchemy.org/en/20/dialects/postgresql.html#json-types>
- Postgres `jsonb_path_match`: useful for CHECK constraints
- [`scripts/check_jsonb_pairs.py`](./scripts/check_jsonb_pairs.py) — runnable linter
- [`examples/good_model.py`](./examples/good_model.py) / [`examples/bad_model.py`](./examples/bad_model.py)
