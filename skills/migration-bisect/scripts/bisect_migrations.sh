#!/usr/bin/env bash
# bisect_migrations.sh — apply Alembic revisions one at a time, run a smoke
# probe after each, stop on the first failure.
#
# Usage:
#   ./bisect_migrations.sh <from-rev> <to-rev> <smoke-command>
#
# Example:
#   export DATABASE_URL=postgresql://postgres:p@localhost:5433/postgres
#   ./bisect_migrations.sh a1b2c3d4 head 'psql "$DATABASE_URL" -c "SELECT 1 FROM patient_consent"'

set -uo pipefail

FROM_REV="${1:?from-rev}"
TO_REV="${2:?to-rev}"
SMOKE="${3:?smoke command}"

if [[ -z "${DATABASE_URL:-}" ]]; then
  echo "DATABASE_URL not set" >&2; exit 2
fi

echo "Resetting DB to revision $FROM_REV..."
alembic downgrade "$FROM_REV" || { echo "downgrade failed"; exit 2; }

# List revisions between FROM_REV (exclusive) and TO_REV (inclusive)
mapfile -t REVS < <(alembic history -r "${FROM_REV}:${TO_REV}" --rev-range \
  | awk '/^Rev:/ {print $2}' | tac)

echo "Bisecting ${#REVS[@]} revisions..."
for rev in "${REVS[@]}"; do
  echo -n "  $rev: applying... "
  if ! alembic upgrade "$rev" >/dev/null 2>&1; then
    echo "FAIL (upgrade)"
    echo "    First failing revision: $rev (alembic upgrade failed)"
    exit 1
  fi
  echo -n "smoke... "
  if ! bash -c "$SMOKE" >/dev/null 2>&1; then
    echo "FAIL"
    echo "    First failing revision: $rev (smoke probe failed)"
    echo "    Run: bash -c \"$SMOKE\" to see stderr"
    exit 1
  fi
  echo "PASS"
done

echo "All ${#REVS[@]} revisions pass. No bisect culprit found in this range."
