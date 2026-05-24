#!/usr/bin/env python3
"""
check_jsonb_pairs.py — lint SQLAlchemy models for paired Pydantic schemas
on every JSONB / JSON column.

Usage:
    python check_jsonb_pairs.py app/models
    python check_jsonb_pairs.py --files a.py b.py
"""
from __future__ import annotations

import argparse
import ast
import sys
from pathlib import Path


def _is_json_call(node: ast.AST) -> bool:
    """Detect `Column(JSONB)`, `Column(JSON)`, `mapped_column(JSONB)`, etc."""
    if isinstance(node, ast.Call):
        for a in node.args:
            if isinstance(a, ast.Name) and a.id in ("JSONB", "JSON"):
                return True
            if isinstance(a, ast.Call) and isinstance(a.func, ast.Name) and a.func.id in ("JSONB", "JSON"):
                return True
        for kw in node.keywords:
            v = kw.value
            if isinstance(v, ast.Name) and v.id in ("JSONB", "JSON"):
                return True
    return False


def find_json_columns(tree: ast.AST) -> list[tuple[str, str]]:
    """Yield (model_class, column_name) for each JSON / JSONB column."""
    found: list[tuple[str, str]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        model_name = node.name
        for stmt in node.body:
            # ColumnName = Column(JSONB)
            if isinstance(stmt, ast.Assign):
                for tgt in stmt.targets:
                    if isinstance(tgt, ast.Name):
                        if isinstance(stmt.value, ast.Call) and getattr(stmt.value.func, "id", "") in ("Column", "mapped_column"):
                            if _is_json_call(stmt.value):
                                found.append((model_name, tgt.id))
            # SQLAlchemy 2.0:  col: Mapped[...] = mapped_column(JSONB)
            if isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name):
                if isinstance(stmt.value, ast.Call) and getattr(stmt.value.func, "id", "") in ("Column", "mapped_column"):
                    if _is_json_call(stmt.value):
                        found.append((model_name, stmt.target.id))
    return found


def find_pydantic_classes(tree: ast.AST) -> set[str]:
    out: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            for base in node.bases:
                if isinstance(base, ast.Name) and base.id == "BaseModel":
                    out.add(node.name)
                if isinstance(base, ast.Attribute) and base.attr == "BaseModel":
                    out.add(node.name)
    return out


def find_schemas_mapping(tree: ast.AST, model_name: str) -> set[str]:
    """Return the set of column names that appear in the model's __schemas__ dict."""
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == model_name:
            for stmt in node.body:
                if isinstance(stmt, ast.Assign):
                    for tgt in stmt.targets:
                        if isinstance(tgt, ast.Name) and tgt.id == "__schemas__":
                            if isinstance(stmt.value, ast.Dict):
                                keys: set[str] = set()
                                for k in stmt.value.keys:
                                    if isinstance(k, ast.Constant) and isinstance(k.value, str):
                                        keys.add(k.value)
                                return keys
    return set()


def lint(path: Path) -> list[tuple[str, str, str]]:
    text = path.read_text(encoding="utf-8", errors="replace")
    try:
        tree = ast.parse(text)
    except SyntaxError as e:
        return [("JBP-000", "ERROR", f"{path}: syntax error {e}")]

    out: list[tuple[str, str, str]] = []
    json_cols = find_json_columns(tree)
    pydantic_classes = find_pydantic_classes(tree)

    for model, col in json_cols:
        # JBP-001 — paired Pydantic schema
        expected = {f"{col.title().replace('_', '')}Schema",
                    f"{model}{col.title().replace('_', '')}Schema"}
        if not (pydantic_classes & expected):
            # broaden: any pydantic class that contains the column name
            if not any(col.replace("_", "").lower() in c.lower() for c in pydantic_classes):
                out.append(("JBP-001", "ERROR",
                            f"{model}.{col}: Column(JSONB) has no paired Pydantic schema (looked for one of {expected})"))

        # JBP-002 — __schemas__ mapping
        schemas_keys = find_schemas_mapping(tree, model)
        if not schemas_keys:
            out.append(("JBP-002", "WARN",
                        f"{model}: no __schemas__ mapping (cannot discover schemas at runtime)"))
        elif col not in schemas_keys:
            out.append(("JBP-002", "WARN",
                        f"{model}.{col} missing from __schemas__"))

    # JBP-005 — extra="allow" on a Pydantic schema is suspicious
    text_lower = text.replace(" ", "").replace("'", '"')
    if 'extra="allow"' in text_lower:
        out.append(("JBP-005", "WARN",
                    "extra=\"allow\" on a JSONB schema silently accepts unknown keys"))

    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("path", nargs="?", default="app/models")
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

    error_count = 0
    for f in files:
        findings = lint(f)
        if not findings:
            continue
        print(f"\n{f}")
        for rule, sev, msg in findings:
            print(f"  {rule}  {sev:<5}  {msg}")
            if sev == "ERROR":
                error_count += 1
    if error_count:
        print(f"\n{error_count} ERROR finding(s). Block commit.", file=sys.stderr)
        return 1
    print("\njsonb-pydantic-pair: clean")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
