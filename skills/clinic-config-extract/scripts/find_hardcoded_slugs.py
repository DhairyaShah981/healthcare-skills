#!/usr/bin/env python3
"""
find_hardcoded_slugs.py — find hardcoded clinic slugs across the codebase.

Reads clinics.yaml (or a --slugs list), greps every source file (excluding
allowlist paths), and categorises findings as:
  CCE-001 bare literal
  CCE-002 conditional branch on the literal
  CCE-003 default-to-X pattern

Usage:
    python find_hardcoded_slugs.py --clinics-yaml clinics.yaml app/ web/
    python find_hardcoded_slugs.py --slugs redding,ent_sd .
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

DEFAULT_EXEMPT = {"clinics.yaml", "tests/fixtures", ".clinic-slugs.deny", "node_modules", ".venv"}


def load_slugs(path: Path | None, inline: str | None) -> list[str]:
    if inline:
        return [s.strip() for s in inline.split(",") if s.strip()]
    if path and path.exists():
        slugs: list[str] = []
        in_clinics = False
        for line in path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if stripped == "clinics:":
                in_clinics = True
                continue
            if in_clinics and re.match(r"^  [A-Za-z][A-Za-z0-9_]*:\s*$", line):
                slugs.append(stripped.rstrip(":"))
        return slugs
    return []


def scan(root: Path, slugs: list[str], exempt: set[str]) -> list[tuple[Path, int, str, str, str]]:
    if not slugs:
        return []
    alt = "|".join(re.escape(s) for s in slugs)
    lit_re   = re.compile(rf"""["']({alt})["']""")
    cond_re  = re.compile(rf"""(?:if|elif)\s+[^=\n]*==\s*["']({alt})["']""")
    deflt_re = re.compile(rf"""or\s+["']({alt})["']""")
    out: list[tuple[Path, int, str, str, str]] = []
    for f in root.rglob("*"):
        if not f.is_file():
            continue
        if any(part in exempt for part in f.parts):
            continue
        if f.suffix not in {".py", ".ts", ".tsx", ".js", ".jsx", ".yaml", ".yml", ".json", ".sql", ".html"}:
            continue
        try:
            text = f.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for i, line in enumerate(text.splitlines(), 1):
            if m := cond_re.search(line):
                out.append((f, i, "CCE-002", "ERROR",
                            f"branch on slug \"{m.group(1)}\": {line.strip()[:120]}"))
            elif m := deflt_re.search(line):
                out.append((f, i, "CCE-003", "ERROR",
                            f"default-to-slug \"{m.group(1)}\": {line.strip()[:120]}"))
            elif m := lit_re.search(line):
                out.append((f, i, "CCE-001", "ERROR",
                            f"bare literal \"{m.group(1)}\": {line.strip()[:120]}"))
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("roots", nargs="*", default=["."])
    ap.add_argument("--clinics-yaml", type=Path, default=Path("clinics.yaml"))
    ap.add_argument("--slugs", type=str, default=None,
                    help="comma-separated slug list (overrides --clinics-yaml)")
    ap.add_argument("--exempt", nargs="*", default=list(DEFAULT_EXEMPT))
    args = ap.parse_args()

    slugs = load_slugs(args.clinics_yaml, args.slugs)
    if not slugs:
        print("no slugs to scan (pass --slugs or provide clinics.yaml)", file=sys.stderr)
        return 2

    err = 0
    for root in args.roots:
        for f, ln, rule, sev, msg in scan(Path(root), slugs, set(args.exempt)):
            print(f"{f}:{ln}  {rule} {sev}  {msg}")
            err += 1

    if err:
        print(f"\n{err} finding(s).", file=sys.stderr)
        return 1
    print("clinic-config-extract: clean")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
