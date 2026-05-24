# Install — Claude Code

## One-liner

```bash
./install.sh --ide claude-code
```

This copies every skill into `~/.claude/skills/<skill-name>/`. Claude Code picks them up at the start of the next session; no restart of any daemon is required.

## What "auto-detect" sees

`./install.sh` with no `--ide` flag picks Claude Code if `~/.claude` exists. So if Claude Code is your default IDE, plain `./install.sh` is enough.

## Install only one skill

```bash
./install.sh --ide claude-code --skill phi-redact
```

## Verify

```bash
ls ~/.claude/skills | grep healthcare        # may not match — skills aren't prefixed
ls ~/.claude/skills | wc -l                  # should show ≥17 more directories than before
```

Open Claude Code, start a new chat, and type:

> *"Use phi-redact to scrub this log:"* followed by any patient-shaped paste.

The agent should respond by running the skill's `## How it works` steps.

## Upgrade

`git pull && ./install.sh --ide claude-code` is idempotent — re-running overwrites existing skill files in place.

## Uninstall

```bash
for d in skills/*/; do rm -rf "$HOME/.claude/skills/$(basename "$d")"; done
```
