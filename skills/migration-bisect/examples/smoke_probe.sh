#!/usr/bin/env bash
# smoke_probe.sh — example smoke probe for migration-bisect.
#
# Exits 0 when the DB is "working" (the row that should exist does);
# non-zero when "broken". Stubbing the smoke is half the engineering
# of a useful bisect.

set -euo pipefail

# 1. Schema-shape probe: the column we expect should exist
psql "$DATABASE_URL" -tAc \
  "SELECT column_name FROM information_schema.columns
     WHERE table_name='patient_consent' AND column_name='signed_hash'" \
  | grep -qx signed_hash || { echo "column missing"; exit 1; }

# 2. Data probe: index exists and is valid
psql "$DATABASE_URL" -tAc \
  "SELECT indexname FROM pg_indexes WHERE indexname='patient_consent_signed_hash_idx'" \
  | grep -qx patient_consent_signed_hash_idx || { echo "index missing"; exit 1; }

# 3. Application probe: a representative query the app runs
psql "$DATABASE_URL" -tAc \
  "EXPLAIN SELECT signed_hash FROM patient_consent WHERE recipient = 'x' LIMIT 1" \
  >/dev/null || { echo "query plan failed"; exit 1; }

exit 0
