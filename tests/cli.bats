#!/usr/bin/env bash
# Bash-based CLI smoke harness (no `bats` dependency required, but pretends).
# Run from repo root: `bash tests/cli.bats`
#
# Asserts each subcommand emits the expected output shape.

set -u
CLI="node bin/healthcare-skills.js"
TMP="$(mktemp -d)"
PASS=0
FAIL=0
FAILED_TESTS=()

red()    { printf '\033[31m%s\033[0m' "$*"; }
green()  { printf '\033[32m%s\033[0m' "$*"; }
yellow() { printf '\033[33m%s\033[0m' "$*"; }

ok() { PASS=$((PASS+1)); printf '  %s %s\n' "$(green PASS)" "$1"; }
no() { FAIL=$((FAIL+1)); FAILED_TESTS+=("$1"); printf '  %s %s\n' "$(red FAIL)" "$1"; printf '       %s\n' "$2"; }

assert_contains() {
  local desc="$1" needle="$2" haystack="$3"
  if printf '%s' "$haystack" | grep -qF -- "$needle"; then ok "$desc"; else no "$desc" "missing: $needle"; fi
}

assert_exit() {
  local desc="$1" expected="$2" actual="$3"
  if [[ "$actual" == "$expected" ]]; then ok "$desc"; else no "$desc" "exit=$actual want=$expected"; fi
}

echo "healthcare-skills CLI smoke"
echo "---------------------------"

# ── help / usage ────────────────────────────────────────────────────────

out=$($CLI 2>&1); rc=$?
assert_contains "usage shown when no args"  "Commands:"      "$out"
assert_contains "usage lists 'add'"          "add <name>"    "$out"
assert_contains "usage lists 'doctor'"       "doctor"        "$out"

out=$($CLI --help 2>&1); rc=$?
assert_contains "--help shows usage"         "Commands:"     "$out"

# ── list ───────────────────────────────────────────────────────────────

out=$($CLI list 2>&1); rc=$?
assert_exit     "list exits 0"               "0"             "$rc"
assert_contains "list shows count"           "skills"        "$out"
assert_contains "list shows phi-redact"      "phi-redact"    "$out"
assert_contains "list shows fhir-bundle"     "fhir-bundle"   "$out"
assert_contains "list shows hipaa-review"    "hipaa-review"  "$out"
assert_contains "list shows smart-oauth-scaffold" "smart-oauth-scaffold" "$out"
assert_contains "list shows synthea-fixture" "synthea-fixture" "$out"

out=$($CLI list --json 2>&1); rc=$?
assert_exit     "list --json exits 0"        "0"             "$rc"
assert_contains "list --json valid JSON"     "\"name\":"     "$out"
assert_contains "list --json has phi-redact" "\"phi-redact\"" "$out"

# ── info ───────────────────────────────────────────────────────────────

out=$($CLI info phi-redact 2>&1); rc=$?
assert_exit     "info exits 0"               "0"             "$rc"
assert_contains "info shows name"            "phi-redact"    "$out"
assert_contains "info shows description"     "description:"  "$out"
assert_contains "info shows tags"            "tags:"         "$out"
assert_contains "info shows incident"        "incident:"     "$out"

out=$($CLI info no-such-skill 2>&1); rc=$?
assert_exit     "info on missing exits ≠ 0"  "2"             "$rc"
assert_contains "info on missing emits error" "no skill named" "$out"

# ── search ─────────────────────────────────────────────────────────────

out=$($CLI search hipaa 2>&1); rc=$?
assert_exit     "search exits 0"             "0"             "$rc"
assert_contains "search finds phi-redact"    "phi-redact"    "$out"
assert_contains "search finds hipaa-review"  "hipaa-review"  "$out"
assert_contains "search finds audit-trail"   "audit-trail"   "$out"

out=$($CLI search "this-string-does-not-appear-anywhere" 2>&1); rc=$?
assert_exit     "search no match exits 0"    "0"             "$rc"
assert_contains "search reports 0 matches"   "0 match"       "$out"

# ── tags ───────────────────────────────────────────────────────────────

out=$($CLI tags 2>&1); rc=$?
assert_exit     "tags exits 0"               "0"             "$rc"
assert_contains "tags shows healthcare"      "healthcare"    "$out"
assert_contains "tags shows fhir"            "fhir"          "$out"
assert_contains "tags shows hipaa"           "hipaa"         "$out"

# ── doctor ─────────────────────────────────────────────────────────────

out=$($CLI doctor 2>&1); rc=$?
assert_exit     "doctor exits 0"             "0"             "$rc"
assert_contains "doctor reports skills count" "skills found:" "$out"
assert_contains "doctor reports frontmatter check" "frontmatter:" "$out"
assert_contains "doctor reports IDE detection" "IDE detected:" "$out"

# ── add (dry-run) ──────────────────────────────────────────────────────

out=$($CLI add phi-redact --ide claude-code --dry-run 2>&1); rc=$?
assert_exit     "add --dry-run exits 0"      "0"             "$rc"
assert_contains "add dry-run prints DRY"     "DRY:"          "$out"
assert_contains "add dry-run mentions phi-redact" "phi-redact" "$out"

out=$($CLI add no-such-skill --ide claude-code --dry-run 2>&1); rc=$?
assert_exit     "add missing skill exits 2"  "2"             "$rc"

out=$($CLI add-all --ide cursor --dry-run 2>&1); rc=$?
assert_exit     "add-all --dry-run exits 0"  "0"             "$rc"
assert_contains "add-all dry-run mentions count" "installed"  "$out"

# ── add (real, into temp HOME) ─────────────────────────────────────────

(HOME="$TMP" $CLI add phi-redact --ide claude-code >/dev/null 2>&1)
if [[ -f "$TMP/.claude/skills/phi-redact/SKILL.md" ]]; then ok "add wrote SKILL.md to ~/.claude/skills/"
else no "add wrote SKILL.md to ~/.claude/skills/" "not found"; fi
if [[ -f "$TMP/.claude/skills/phi-redact/scripts/phi_scrubber.py" ]]; then ok "add preserved scripts/"
else no "add preserved scripts/" "scripts/ missing"; fi

# ── summary ────────────────────────────────────────────────────────────

rm -rf "$TMP"
echo
TOTAL=$((PASS + FAIL))
if [[ $FAIL -eq 0 ]]; then
  printf '%s\n' "$(green "All ${TOTAL} CLI tests passed.")"
  exit 0
else
  printf '%s\n' "$(red "${FAIL} of ${TOTAL} CLI tests failed:")"
  for t in "${FAILED_TESTS[@]}"; do printf '  - %s\n' "$t"; done
  exit 1
fi
