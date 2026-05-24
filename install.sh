#!/usr/bin/env bash
# install.sh — one-command installer for healthcare-skills.
#
# Detects the IDE (or honours --ide) and copies / adapts every skill into
# the right place for that IDE. Idempotent: re-running updates in place.

set -euo pipefail

REPO_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)"
SKILLS_DIR="$REPO_ROOT/skills"

# ── arg parse ────────────────────────────────────────────────────────────
IDE=""
DRY_RUN=0
SKILL_FILTER=""

usage() {
  cat <<EOF
healthcare-skills installer

Usage: ./install.sh [--ide <claude-code|cursor|codex|gemini|all>] [--skill <name>] [--dry-run]

Without --ide, auto-detects from \$HOME (Claude Code first, then Cursor, then Codex).
--skill installs only one skill. --dry-run prints what would happen without writing.

Examples:
  ./install.sh                            # auto-detect
  ./install.sh --ide claude-code          # explicit IDE
  ./install.sh --ide cursor --skill phi-redact
  ./install.sh --ide all                  # install everywhere we can find
EOF
  exit 0
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --ide)       IDE="$2"; shift 2 ;;
    --skill)     SKILL_FILTER="$2"; shift 2 ;;
    --dry-run)   DRY_RUN=1; shift ;;
    -h|--help)   usage ;;
    *)           echo "Unknown arg: $1" >&2; exit 1 ;;
  esac
done

# ── auto-detect IDE ──────────────────────────────────────────────────────
if [[ -z "$IDE" ]]; then
  if   [[ -d "$HOME/.claude" ]]; then IDE="claude-code"
  elif [[ -d "$HOME/.cursor" ]]; then IDE="cursor"
  elif [[ -d "$HOME/.codex"  ]]; then IDE="codex"
  elif [[ -d "$HOME/.gemini" ]]; then IDE="gemini"
  else
    echo "Could not auto-detect IDE. Pass --ide explicitly." >&2; exit 1
  fi
  echo "Auto-detected IDE: $IDE"
fi

# ── paths per IDE ────────────────────────────────────────────────────────
case "$IDE" in
  claude-code) TARGET="$HOME/.claude/skills" ;;
  cursor)      TARGET="$PWD/.cursor/rules" ;;
  codex)       TARGET="$PWD" ;;            # AGENTS.md lives at repo root
  gemini)      TARGET="$PWD" ;;            # GEMINI.md lives at repo root
  all)
    for one in claude-code cursor codex gemini; do
      "$0" --ide "$one" ${SKILL_FILTER:+--skill "$SKILL_FILTER"} ${DRY_RUN:+--dry-run}
    done
    exit 0
    ;;
  *) echo "Unsupported IDE: $IDE" >&2; exit 1 ;;
esac

run() {
  if [[ "$DRY_RUN" -eq 1 ]]; then echo "DRY: $*"; else eval "$@"; fi
}

# ── pick skills ──────────────────────────────────────────────────────────
SKILLS=()
if [[ -n "$SKILL_FILTER" ]]; then
  SKILLS+=("$SKILLS_DIR/$SKILL_FILTER")
else
  while IFS= read -r d; do
    SKILLS+=("$d")
  done < <(find "$SKILLS_DIR" -mindepth 1 -maxdepth 1 -type d -not -name '_*' | sort)
fi

echo "Installing ${#SKILLS[@]} skill(s) → $TARGET (IDE: $IDE)"

# ── install per IDE ──────────────────────────────────────────────────────
case "$IDE" in
  claude-code)
    run "mkdir -p \"$TARGET\""
    for sk in "${SKILLS[@]}"; do
      name="$(basename "$sk")"
      run "rm -rf \"$TARGET/$name\""
      run "cp -R \"$sk\" \"$TARGET/$name\""
      echo "  ✓ $name"
    done
    ;;

  cursor)
    run "mkdir -p \"$TARGET\""
    for sk in "${SKILLS[@]}"; do
      name="$(basename "$sk")"
      out="$TARGET/$name.mdc"
      # convert SKILL.md → .mdc (frontmatter compatible)
      run "cp \"$sk/SKILL.md\" \"$out\""
      echo "  ✓ $name → $out"
    done
    ;;

  codex)
    agents="$TARGET/AGENTS.md"
    run "echo '# AGENTS.md — healthcare-skills' > \"$agents\""
    run "echo '' >> \"$agents\""
    for sk in "${SKILLS[@]}"; do
      name="$(basename "$sk")"
      rel="${sk#$REPO_ROOT/}"
      run "echo '## '$name >> \"$agents\""
      run "echo '@include '$rel'/SKILL.md' >> \"$agents\""
      run "echo '' >> \"$agents\""
      echo "  ✓ $name → AGENTS.md"
    done
    ;;

  gemini)
    gemini="$TARGET/GEMINI.md"
    run "echo '# GEMINI.md — healthcare-skills' > \"$gemini\""
    run "echo '' >> \"$gemini\""
    for sk in "${SKILLS[@]}"; do
      name="$(basename "$sk")"
      rel="${sk#$REPO_ROOT/}"
      run "echo '## Skill: '$name >> \"$gemini\""
      run "cat \"$sk/SKILL.md\" >> \"$gemini\""
      run "echo '' >> \"$gemini\""
      echo "  ✓ $name → GEMINI.md"
    done
    ;;
esac

echo
echo "Done. Restart your IDE if it doesn't pick up the new skills."
