#!/usr/bin/env python3
"""
bisect_migrations.py — Python variant of the bisect harness with cleaner
output and optional Docker-managed ephemeral Postgres.

Usage:
    python bisect_migrations.py \
        --from a1b2c3d4 --to head \
        --smoke 'psql "$DATABASE_URL" -c "SELECT 1 FROM patient_consent"' \
        --ephemeral-db docker

Requires `alembic` on PATH and DATABASE_URL set (or --ephemeral-db).
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
import uuid


def _docker_postgres() -> tuple[str, str]:
    """Spin up a throwaway Postgres in Docker; return (container_id, DATABASE_URL)."""
    cid = subprocess.run(
        ["docker", "run", "-d", "--rm",
         "-e", "POSTGRES_PASSWORD=p",
         "-e", "POSTGRES_DB=bisect",
         "-p", "0:5432",
         "postgres:16"],
        check=True, capture_output=True, text=True).stdout.strip()
    port = subprocess.run(
        ["docker", "port", cid, "5432"],
        check=True, capture_output=True, text=True).stdout.strip().rsplit(":", 1)[-1]
    url = f"postgresql://postgres:p@localhost:{port}/bisect"
    # Wait for readiness
    for _ in range(30):
        r = subprocess.run(["docker", "exec", cid, "pg_isready", "-U", "postgres"],
                           capture_output=True, text=True)
        if r.returncode == 0:
            return cid, url
        time.sleep(1)
    raise RuntimeError("postgres didn't become ready")


def list_revs(from_rev: str, to_rev: str) -> list[str]:
    out = subprocess.run(
        ["alembic", "history", "-r", f"{from_rev}:{to_rev}", "--rev-range"],
        check=True, capture_output=True, text=True).stdout
    revs: list[str] = []
    for line in out.splitlines():
        if line.startswith("Rev:"):
            revs.append(line.split()[1])
    return list(reversed(revs))


def run(cmd: list[str] | str, **kw) -> subprocess.CompletedProcess:
    shell = isinstance(cmd, str)
    return subprocess.run(cmd, shell=shell, capture_output=True, text=True, **kw)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--from", dest="from_rev", required=True)
    ap.add_argument("--to", dest="to_rev", default="head")
    ap.add_argument("--smoke", required=True, help="shell command; exit 0 = pass")
    ap.add_argument("--ephemeral-db", choices=["docker", "none"], default="none")
    args = ap.parse_args()

    cid = None
    if args.ephemeral_db == "docker":
        print("Spinning up ephemeral postgres...", file=sys.stderr)
        cid, url = _docker_postgres()
        os.environ["DATABASE_URL"] = url
        print(f"DATABASE_URL={url}", file=sys.stderr)

    try:
        print(f"Downgrading to {args.from_rev}...", file=sys.stderr)
        r = run(["alembic", "downgrade", args.from_rev])
        if r.returncode != 0:
            print("downgrade failed; starting from current state", file=sys.stderr)

        revs = list_revs(args.from_rev, args.to_rev)
        print(f"Bisecting {len(revs)} revisions:", file=sys.stderr)

        for rev in revs:
            up = run(["alembic", "upgrade", rev])
            if up.returncode != 0:
                print(f"  {rev}: FAIL (alembic upgrade)\n     stderr={up.stderr.strip()}")
                return 1
            smk = run(args.smoke)
            tag = "PASS" if smk.returncode == 0 else "FAIL"
            print(f"  {rev}: {tag}")
            if smk.returncode != 0:
                print(f"\nFirst failing revision: {rev}")
                print(f"  smoke stderr: {smk.stderr.strip()[:200]}")
                return 1

        print("All revisions passed; no culprit in range.")
        return 0
    finally:
        if cid:
            subprocess.run(["docker", "rm", "-f", cid], capture_output=True)


if __name__ == "__main__":
    raise SystemExit(main())
