# Contributing to healthcare-skills

Every skill in this pack maps to a real production incident. We accept skills that meet the same bar.

## What makes a good skill

- **Tied to a real incident** — "We got paged at 2 AM because X" beats "Best practice says Y."
- **Crisp activation** — the `description` and `when_to_use` fields make it obvious when the agent should reach for this skill.
- **Plug-and-play** — works in Claude Code, Cursor, Codex CLI, and Gemini CLI with the same body.
- **No client data / no PHI** — examples must use synthetic or public data only.
- **Offline-first** — any network call must degrade gracefully when keys / connectivity are missing.

## Adding a new skill — 5-minute guide

```bash
cp -r skills/_template skills/<your-skill-name>
cd skills/<your-skill-name>
$EDITOR SKILL.md          # fill in frontmatter + body
# add before/after examples
mkdir -p examples
echo "..." > examples/before.txt
echo "..." > examples/after.txt
# (optional) drop a runnable helper into scripts/
# lint
../../scripts/validate.sh
```

## Required SKILL.md frontmatter

```yaml
---
name: <kebab-case>
description: <one-line summary>. Use when <trigger 1>, <trigger 2>, <trigger 3>.
when_to_use: |
  Activate when the user:
  - <concrete trigger>
  - <concrete trigger>
allowed-tools: [Read, Grep, Edit, Bash]
license: MIT
tags: [healthcare, hipaa, fhir, ...]
incident: |
  <one-paragraph description of the production incident this prevents>
---
```

## Body structure

Every SKILL.md must include:

1. **When to use** — explicit trigger phrases.
2. **How it works** — numbered step-by-step instructions written *to the agent*.
3. **Example** — before / after pair the agent can pattern-match.
4. **Edge cases & common mistakes** — the failure modes that prompted the skill.
5. **References** — links to relevant standards (HIPAA, HL7, FHIR R4, ONC, NIST).

## PR checklist

- [ ] `./scripts/validate.sh` passes
- [ ] At least one example in `examples/`
- [ ] README skill table updated
- [ ] If the skill ships executable code, it has a doctest or smoke-test
- [ ] Commit message describes the incident, not just the change
