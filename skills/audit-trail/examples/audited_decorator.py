"""
audited_decorator.py — reference implementation for the audit-trail skill.

Drop-in @audited() decorator that:
- Records the fact of every wrapped call into an append-only AuditEvent table
- Hashes PHI-tagged arguments (never stores them raw)
- Captures actor identity from a contextvar (or framework-provided current_user)
- Correlates rows by trace_id

This is a reference implementation. Copy and adapt to your stack
(SQLAlchemy + FastAPI shown; works the same for Django, Flask, Litestar).
"""
from __future__ import annotations

import contextvars
import functools
import hashlib
import inspect
import json
import os
import time
import traceback
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Iterable

# ── context ────────────────────────────────────────────────────────────────

# Populate this from your auth middleware on every request.
current_actor: contextvars.ContextVar["Actor | None"] = contextvars.ContextVar("current_actor", default=None)
current_trace: contextvars.ContextVar["str | None"] = contextvars.ContextVar("current_trace", default=None)


@dataclass(frozen=True)
class Actor:
    id: str               # "user:42" / "service:appointments-worker"
    type: str             # "user" | "service" | "system"
    on_behalf_of: str | None = None


# ── audit row ──────────────────────────────────────────────────────────────

@dataclass
class AuditRow:
    id: str
    ts: str
    actor_id: str
    actor_type: str
    on_behalf_of: str | None
    action: str
    resource_type: str | None
    resource_id: str | None
    args_hash: str | None
    outcome: str
    error: str | None
    duration_ms: int
    trace_id: str | None


# ── persistence ────────────────────────────────────────────────────────────

# Hook this up to your project's SessionLocal / db / orm.
def write_audit(row: AuditRow) -> None:
    """Persist an audit row. Default: stderr JSON line. Replace with your DB writer."""
    import sys
    sys.stderr.write(json.dumps(row.__dict__) + "\n")


# ── PHI hashing ────────────────────────────────────────────────────────────

_SALT = os.environ.get("AUDIT_ARG_HASH_SALT", "").encode("utf-8")


def _hash_args(args_map: dict[str, Any]) -> str:
    serialised = json.dumps(args_map, sort_keys=True, default=str).encode("utf-8")
    return "sha256:" + hashlib.sha256(_SALT + serialised).hexdigest()


# ── decorator ──────────────────────────────────────────────────────────────

def audited(
    *,
    action: str,
    phi_args: Iterable[str] = (),
    resource_arg: str | None = None,
    resource_type: str | None = None,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """
    Wrap a function so every call records an AuditEvent row.

    Args:
        action: dotted action name, e.g. "patient.read", "lab.export".
        phi_args: names of arguments whose values are PHI; their values are
                  hashed into `args_hash` instead of recorded raw.
        resource_arg: name of the argument that identifies the primary resource
                  (e.g. "patient_id"); recorded into `resource_id`.
        resource_type: FHIR resource type for the primary resource ("Patient",
                  "Encounter"); recorded into `resource_type`.
    """
    phi_args_set = set(phi_args)

    def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
        sig = inspect.signature(fn)
        is_coro = inspect.iscoroutinefunction(fn)

        def _bind(args: tuple, kwargs: dict) -> dict[str, Any]:
            try:
                bound = sig.bind_partial(*args, **kwargs)
                bound.apply_defaults()
                return dict(bound.arguments)
            except TypeError:
                return {}

        def _build_row(bound: dict[str, Any], outcome: str, error: str | None,
                       started: float) -> AuditRow:
            actor = current_actor.get() or Actor(id="anonymous", type="system")
            phi_map = {k: v for k, v in bound.items() if k in phi_args_set}
            args_hash = _hash_args(phi_map) if phi_map else None
            resource_id = (
                str(bound.get(resource_arg)) if resource_arg and bound.get(resource_arg) is not None else None
            )
            return AuditRow(
                id=str(uuid.uuid7()) if hasattr(uuid, "uuid7") else str(uuid.uuid4()),
                ts=datetime.now(tz=timezone.utc).isoformat(timespec="milliseconds"),
                actor_id=actor.id,
                actor_type=actor.type,
                on_behalf_of=actor.on_behalf_of,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                args_hash=args_hash,
                outcome=outcome,
                error=error,
                duration_ms=int((time.perf_counter() - started) * 1000),
                trace_id=current_trace.get(),
            )

        if is_coro:
            @functools.wraps(fn)
            async def awrapper(*args: Any, **kwargs: Any) -> Any:
                started = time.perf_counter()
                bound = _bind(args, kwargs)
                try:
                    result = await fn(*args, **kwargs)
                    write_audit(_build_row(bound, "success", None, started))
                    return result
                except Exception as exc:
                    err = f"{type(exc).__name__}: {exc}"
                    write_audit(_build_row(bound, "failure", err, started))
                    raise
            return awrapper

        @functools.wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            started = time.perf_counter()
            bound = _bind(args, kwargs)
            try:
                result = fn(*args, **kwargs)
                write_audit(_build_row(bound, "success", None, started))
                return result
            except Exception as exc:
                err = f"{type(exc).__name__}: {exc}"
                write_audit(_build_row(bound, "failure", err, started))
                raise
        return wrapper

    return decorator


# ── demo ───────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # Simulate an authenticated request
    current_actor.set(Actor(id="user:42", type="user"))
    current_trace.set("01HF7T9X3K4P5VWQGN2EBAR8M0")

    @audited(action="patient.read", phi_args=("patient_id",),
             resource_arg="patient_id", resource_type="Patient")
    def get_patient(patient_id: str) -> dict[str, Any]:
        return {"id": patient_id, "name": "[REDACTED]"}

    get_patient("patient:9981")
