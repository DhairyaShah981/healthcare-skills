#!/usr/bin/env bash
# validate.sh — lint every SKILL.md in the repo.
#
# Used both locally (`./scripts/validate.sh`) and in CI (validate-skills.yml).
# Exits non-zero on any failure so CI fails loudly.

set -euo pipefail

REPO_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." &>/dev/null && pwd)"
SKILLS_DIR="$REPO_ROOT/skills"

REQUIRED_KEYS=(name description when_to_use allowed-tools license tags incident)
REQUIRED_SECTIONS=("## When to use" "## How it works" "## Example" "## Edge cases" "## References")

fail=0

red()    { printf '\033[31m%s\033[0m\n' "$*"; }
green()  { printf '\033[32m%s\033[0m\n' "$*"; }
yellow() { printf '\033[33m%s\033[0m\n' "$*"; }

for skill_dir in "$SKILLS_DIR"/*/; do
  name="$(basename "$skill_dir")"
  [[ "$name" == _* ]] && continue
  md="$skill_dir/SKILL.md"

  if [[ ! -f "$md" ]]; then
    red "✗ $name: missing SKILL.md"; fail=1; continue
  fi

  # frontmatter
  for key in "${REQUIRED_KEYS[@]}"; do
    if ! grep -q "^$key:" "$md"; then
      red "✗ $name: missing frontmatter key '$key'"; fail=1
    fi
  done

  # body sections
  for section in "${REQUIRED_SECTIONS[@]}"; do
    if ! grep -qF "$section" "$md"; then
      red "✗ $name: missing body section '$section'"; fail=1
    fi
  done

  # name matches dir
  declared_name="$(grep -m1 '^name:' "$md" | sed 's/name: *//' | tr -d ' \r\t')"
  if [[ "$declared_name" != "$name" ]]; then
    red "✗ $name: frontmatter name='$declared_name' != directory='$name'"; fail=1
  fi

  if [[ $fail -eq 0 ]]; then
    green "✓ $name"
  fi
done

if [[ $fail -ne 0 ]]; then
  red "Validation failed."
  exit 1
fi

green "All skills valid."
