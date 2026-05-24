#!/usr/bin/env python3
"""
check_tenant_rls.py — lint Python files for missing tenant predicates on
multi-tenant SQLAlchemy queries.

Heuristic-based: walks the AST, finds `.query(Model)` / `select(Model)` chains
that reference a scoped model, and checks for a `.filter(Model.client_id == ...)`
or `.filter_by(client_id=...)` somewhere in the chain.

Config (.tenant-rls.yaml):
    tenant_column: client_id
    scoped_tables: [patient, encounter, observation, ...]
"""
from __future__ import annotations

import argparse
import ast
import sys
from pathlib import Path

DEFAULT_TENANT_COL = "client_id"
DEFAULT_SCOPED = {
    "Patient", "Encounter", "Observation", "Condition", "Appointment",
    "MedicationRequest", "AuditEvent", "PriorAuth", "ClinicUser",
}


def _load_config(repo_root: Path) -> tuple[str, set[str]]:
    cfg = repo_root / ".tenant-rls.yaml"
    if not cfg.exists():
        return DEFAULT_TENANT_COL, DEFAULT_SCOPED
    text = cfg.read_text(encoding="utf-8")
    tenant_col = DEFAULT_TENANT_COL
    scoped: set[str] = set()
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("tenant_column:"):
            tenant_col = line.split(":", 1)[1].strip()
        elif line.startswith("- "):
            scoped.add(line[2:].strip().title())  # patient → Patient
    return tenant_col, (scoped or DEFAULT_SCOPED)


def _chain_uses_tenant_filter(call: ast.Call, tenant_col: str) -> bool:
    """Walk back through a method chain and see if any link filters on tenant_col."""
    node: ast.AST = call
    while isinstance(node, ast.Call):
        # filter(Model.client_id == ...) — look at Compare nodes
        for arg in node.args + [kw.value for kw in node.keywords]:
            if _expr_references(arg, tenant_col):
                return True
        # filter_by(client_id=...) — look at keyword names
        for kw in node.keywords:
            if kw.arg == tenant_col:
                return True
        # move to predecessor in chain
        if isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Call):
            node = node.func.value
        else:
            break
    return False


def _expr_references(expr: ast.AST, tenant_col: str) -> bool:
    for sub in ast.walk(expr):
        if isinstance(sub, ast.Attribute) and sub.attr == tenant_col:
            return True
        if isinstance(sub, ast.Name) and sub.id == tenant_col:
            return True
    return False


def _query_target_name(call: ast.Call) -> str | None:
    """`.query(Patient)` or `select(Patient)` → 'Patient'."""
    if not call.args:
        return None
    arg = call.args[0]
    if isinstance(arg, ast.Name):
        return arg.id
    if isinstance(arg, ast.Attribute):
        return arg.attr
    return None


def lint_file(path: Path, tenant_col: str, scoped: set[str]) -> list[tuple[int, str, str]]:
    out: list[tuple[int, str, str]] = []
    try:
        tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
    except SyntaxError as e:
        return [(getattr(e, "lineno", 0), "RLS-000", f"{path}: syntax error {e}")]

    for node in ast.walk(tree):
        # bypass annotation
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant):
            continue

        if not isinstance(node, ast.Call):
            continue

        # detect .query(Model) calls
        if isinstance(node.func, ast.Attribute) and node.func.attr in ("query", "select"):
            target = _query_target_name(node)
            if target and target in scoped:
                # walk the chain UP (find the outermost call that uses this as a base)
                # Simpler: check if any later .filter / .filter_by in the same expression
                # by searching for chains that start with this node.
                ancestor = _outermost_chain_containing(tree, node)
                if not _chain_uses_tenant_filter(ancestor, tenant_col):
                    bypass = _has_bypass_comment(path, node.lineno)
                    if not bypass:
                        out.append((
                            node.lineno,
                            "RLS-001",
                            f"query({target}) lacks {tenant_col} predicate",
                        ))

        # detect .get(Model, id) on a session
        if isinstance(node.func, ast.Attribute) and node.func.attr == "get":
            if node.args and isinstance(node.args[0], ast.Name) and node.args[0].id in scoped:
                bypass = _has_bypass_comment(path, node.lineno)
                if not bypass:
                    out.append((node.lineno, "RLS-001",
                                f"session.get({node.args[0].id}, ...) bypasses tenant predicate"))

    return out


def _outermost_chain_containing(tree: ast.AST, target: ast.Call) -> ast.Call:
    """Find the outermost Call whose chain ultimately calls `target`. Approximate: walks parent map."""
    # Quick approach: walk every Call and check if `target` is reachable by walking .func.value chain.
    best = target
    for cand in ast.walk(tree):
        if not isinstance(cand, ast.Call):
            continue
        node: ast.AST = cand
        while isinstance(node, ast.Call):
            if node is target:
                # cand is in same chain; pick the outermost (cand itself, traverse outward in subsequent walks)
                if _depth(cand, target) > _depth(best, target):
                    best = cand
                break
            if isinstance(node.func, ast.Attribute):
                node = node.func.value
            else:
                break
    return best


def _depth(outer: ast.Call, target: ast.Call) -> int:
    d = 0
    node: ast.AST = outer
    while isinstance(node, ast.Call):
        if node is target:
            return d
        if isinstance(node.func, ast.Attribute):
            node = node.func.value
            d += 1
        else:
            break
    return -1


def _has_bypass_comment(path: Path, lineno: int) -> bool:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return False
    for offset in (0, -1, -2):
        idx = lineno - 1 + offset
        if 0 <= idx < len(lines) and "tenant-rls-guard: bypass" in lines[idx]:
            return True
    return False


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("path", nargs="?", default="app")
    ap.add_argument("--config-dir", default=".")
    ap.add_argument("--files", nargs="*", default=None)
    args = ap.parse_args()

    tenant_col, scoped = _load_config(Path(args.config_dir))

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
        findings = lint_file(f, tenant_col, scoped)
        if not findings:
            continue
        print(f"\n{f}")
        for ln, rule, msg in findings:
            print(f"  line {ln}: {rule} ERROR  {msg}")
            err += 1

    if err:
        print(f"\n{err} ERROR finding(s). Block commit.", file=sys.stderr)
        return 1
    print("\ntenant-rls-guard: clean")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
