#!/usr/bin/env python3
"""
check_route_fatness.py — flag fat route handlers (Python frameworks).

Rules:
  RTF-001 body > N lines (default 30)
  RTF-002 > 1 external HTTP call
  RTF-003 > 3 DB queries
  RTF-004 nested branching depth > 2
  RTF-005 try/except wrapping ≥ 20 lines
"""
from __future__ import annotations

import argparse
import ast
import sys
from pathlib import Path

ROUTE_DECORATOR_ATTRS = {"get", "post", "put", "patch", "delete", "head", "options", "route", "websocket"}
HTTP_CALL_NAMES = {"requests", "httpx", "urllib"}
DB_CALL_ATTRS = {"query", "execute", "scalar", "scalars", "first", "all", "one", "one_or_none", "add", "delete", "commit"}


def is_route(fn: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    for dec in fn.decorator_list:
        if isinstance(dec, ast.Call):
            f = dec.func
        else:
            f = dec
        if isinstance(f, ast.Attribute) and f.attr in ROUTE_DECORATOR_ATTRS:
            return True
    return False


def count_http_calls(node: ast.AST) -> list[str]:
    out: list[str] = []
    for sub in ast.walk(node):
        if not isinstance(sub, ast.Call):
            continue
        f = sub.func
        if isinstance(f, ast.Attribute) and isinstance(f.value, ast.Name) and f.value.id in HTTP_CALL_NAMES:
            out.append(f"{f.value.id}.{f.attr}")
    return out


def count_db_queries(node: ast.AST) -> int:
    count = 0
    for sub in ast.walk(node):
        if isinstance(sub, ast.Call) and isinstance(sub.func, ast.Attribute):
            if sub.func.attr in DB_CALL_ATTRS:
                count += 1
    return count


def max_branch_depth(node: ast.AST, depth: int = 0) -> int:
    if isinstance(node, (ast.If, ast.For, ast.AsyncFor, ast.While, ast.With, ast.AsyncWith)):
        depth += 1
    best = depth
    for child in ast.iter_child_nodes(node):
        best = max(best, max_branch_depth(child, depth))
    return best


def big_try_block(fn: ast.AST) -> bool:
    for sub in ast.walk(fn):
        if isinstance(sub, ast.Try):
            start = sub.lineno
            end = max((s.end_lineno for s in sub.body if getattr(s, "end_lineno", None)), default=start)
            if end - start >= 20:
                return True
    return False


def is_exempt(text: str, fn_line: int) -> bool:
    lines = text.splitlines()
    idx = max(0, fn_line - 2)
    return "route-fatness: exempt" in "\n".join(lines[idx:fn_line + 1])


def lint_file(path: Path, max_lines: int) -> list[tuple[int, str, str, str]]:
    text = path.read_text(encoding="utf-8", errors="replace")
    try:
        tree = ast.parse(text)
    except SyntaxError as e:
        return [(getattr(e, "lineno", 0), "RTF-000", "ERROR", f"syntax error {e}")]

    findings: list[tuple[int, str, str, str]] = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if not is_route(node):
            continue
        if is_exempt(text, node.lineno):
            continue
        start = node.body[0].lineno if node.body else node.lineno
        end = max((s.end_lineno for s in node.body if getattr(s, "end_lineno", None)), default=start)
        body_lines = end - start + 1
        if body_lines > max_lines:
            findings.append((node.lineno, "RTF-001", "WARN",
                             f"{node.name}: body is {body_lines} lines (limit {max_lines})"))
        http = count_http_calls(node)
        if len(http) > 1:
            findings.append((node.lineno, "RTF-002", "ERROR",
                             f"{node.name}: {len(http)} external HTTP calls: {http}"))
        db_q = count_db_queries(node)
        if db_q > 3:
            findings.append((node.lineno, "RTF-003", "ERROR",
                             f"{node.name}: {db_q} DB calls (limit 3)"))
        depth = max_branch_depth(node) - 1   # subtract the function body itself
        if depth > 2:
            findings.append((node.lineno, "RTF-004", "WARN",
                             f"{node.name}: branch depth {depth} (limit 2)"))
        if big_try_block(node):
            findings.append((node.lineno, "RTF-005", "WARN",
                             f"{node.name}: try/except wraps ≥ 20 lines"))
    return findings


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("path", nargs="?", default="app")
    ap.add_argument("--max-lines", type=int, default=30)
    ap.add_argument("--files", nargs="*", default=None)
    args = ap.parse_args()

    files: list[Path]
    if args.files:
        files = [Path(p) for p in args.files]
    else:
        root = Path(args.path)
        if not root.exists():
            print(f"{root}: no such directory", file=sys.stderr); return 2
        files = sorted(root.rglob("*.py"))

    err = 0
    for f in files:
        findings = lint_file(f, args.max_lines)
        if not findings:
            continue
        print(f"\n{f}")
        for ln, rule, sev, msg in findings:
            print(f"  line {ln}: {rule} {sev}  {msg}")
            if sev == "ERROR":
                err += 1

    if err:
        print(f"\n{err} ERROR finding(s).", file=sys.stderr)
        return 1
    print("\nroute-fatness: clean")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
