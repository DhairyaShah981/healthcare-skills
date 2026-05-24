#!/usr/bin/env python3
"""
check_async_blocking.py — detect synchronous IO calls inside `async def` bodies.

Walks the AST of every Python file under a path (default: app/), enters each
AsyncFunctionDef, and looks for calls to the known-blocking modules /
functions. Exempts calls wrapped in `run_in_executor` or `asyncio.to_thread`.
"""
from __future__ import annotations

import argparse
import ast
import sys
from pathlib import Path

BLOCKING_MODULES = {
    "requests", "urllib", "urllib3", "smtplib", "paramiko",
    "psycopg2", "ftplib", "telnetlib", "subprocess",
}
BLOCKING_CALLS = {
    ("time", "sleep"):                   ("ASB-003", "await asyncio.sleep(...)"),
    ("requests", "get"):                 ("ASB-001", "httpx.AsyncClient().get(...)"),
    ("requests", "post"):                ("ASB-001", "httpx.AsyncClient().post(...)"),
    ("requests", "put"):                 ("ASB-001", "httpx.AsyncClient().put(...)"),
    ("requests", "delete"):              ("ASB-001", "httpx.AsyncClient().delete(...)"),
    ("requests", "patch"):               ("ASB-001", "httpx.AsyncClient().patch(...)"),
    ("requests", "request"):             ("ASB-001", "httpx.AsyncClient().request(...)"),
    ("urllib.request", "urlopen"):       ("ASB-002", "httpx.AsyncClient().get(...)"),
    ("subprocess", "run"):               ("ASB-006", "asyncio.create_subprocess_exec(...)"),
    ("subprocess", "check_call"):        ("ASB-006", "asyncio.create_subprocess_exec(...)"),
    ("subprocess", "check_output"):      ("ASB-006", "asyncio.create_subprocess_exec(...)"),
    ("smtplib", "SMTP"):                 ("ASB-004", "aiosmtplib.SMTP(...)"),
    ("psycopg2", "connect"):             ("ASB-004", "psycopg.AsyncConnection.connect(...) or asyncpg"),
}


def _call_qualname(call: ast.Call) -> tuple[str, str] | None:
    """Return (module-or-base, attr) for a Call like a.b.c()."""
    f = call.func
    if isinstance(f, ast.Attribute):
        if isinstance(f.value, ast.Name):
            return (f.value.id, f.attr)
        if isinstance(f.value, ast.Attribute) and isinstance(f.value.value, ast.Name):
            return (f"{f.value.value.id}.{f.value.attr}", f.attr)
    if isinstance(f, ast.Name):
        return ("", f.id)
    return None


def _inside_executor(call: ast.Call) -> bool:
    """True if this call is the argument to `run_in_executor` or `asyncio.to_thread`."""
    # We approximate by looking at the immediate parent in the AST via a simple field-walk.
    return False  # parent-detection is non-trivial in pure ast; suppress when used as a callable arg below.


def _exempt_via_threadpool(parent_call: ast.Call) -> bool:
    qn = _call_qualname(parent_call)
    if not qn:
        return False
    base, attr = qn
    return attr in ("run_in_executor", "to_thread") or base == "asyncio"


def lint_file(path: Path) -> list[tuple[int, str, str, str]]:
    text = path.read_text(encoding="utf-8", errors="replace")
    try:
        tree = ast.parse(text)
    except SyntaxError as e:
        return [(getattr(e, "lineno", 0), "ASB-000", "ERROR", f"syntax error {e}")]

    findings: list[tuple[int, str, str, str]] = []

    for outer in ast.walk(tree):
        if not isinstance(outer, ast.AsyncFunctionDef):
            continue
        for node in ast.walk(outer):
            if not isinstance(node, ast.Call):
                continue
            # exempt: outer call is run_in_executor / to_thread, current node passed as arg
            # detection: scan for run_in_executor in the outer function body
            pass

            qn = _call_qualname(node)
            if not qn:
                continue
            base, attr = qn

            # check exact (module, function) pairs
            if (base, attr) in BLOCKING_CALLS:
                rule, fix = BLOCKING_CALLS[(base, attr)]
                if not _is_inside_threadpool(node, outer):
                    findings.append((node.lineno, rule, "ERROR",
                                     f"{base}.{attr}(...) inside async def {outer.name}() → use {fix}"))

            # generic: module-level call (e.g. `requests.session()`)
            elif base in BLOCKING_MODULES:
                if not _is_inside_threadpool(node, outer):
                    findings.append((node.lineno, "ASB-001", "ERROR",
                                     f"{base}.{attr}(...) inside async def {outer.name}() — sync module"))

    return findings


def _is_inside_threadpool(target: ast.Call, fn: ast.AsyncFunctionDef) -> bool:
    """Detect whether `target` is passed as a callable to run_in_executor / to_thread."""
    for cand in ast.walk(fn):
        if not isinstance(cand, ast.Call):
            continue
        qn = _call_qualname(cand)
        if not qn:
            continue
        _, attr = qn
        if attr in ("run_in_executor", "to_thread"):
            for arg in cand.args:
                if arg is target:
                    return True
                # passing the function reference, not call (sync func ref → executor)
                if isinstance(arg, ast.Attribute):
                    if hasattr(target.func, "value") and getattr(target.func, "attr", None) == arg.attr:
                        return True
    return False


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("path", nargs="?", default="app")
    ap.add_argument("--files", nargs="*", default=None)
    args = ap.parse_args()

    files: list[Path]
    if args.files:
        files = [Path(p) for p in args.files]
    else:
        root = Path(args.path)
        if not root.exists():
            print(f"{root}: no such directory", file=sys.stderr)
            return 2
        files = sorted(root.rglob("*.py"))

    err = 0
    for f in files:
        findings = lint_file(f)
        if not findings:
            continue
        print(f"\n{f}")
        for ln, rule, sev, msg in findings:
            print(f"  line {ln}: {rule} {sev}  {msg}")
            if sev == "ERROR":
                err += 1

    if err:
        print(f"\n{err} ERROR finding(s). Block commit.", file=sys.stderr)
        return 1
    print("\nasync-blocking-lint: clean")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
