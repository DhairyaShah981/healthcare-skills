# Architecture

## Skill anatomy

```
skills/<skill-name>/
├── SKILL.md             # required — YAML frontmatter + Markdown body
├── references/          # optional — schemas, regex catalogs, code-system URIs
├── examples/            # optional — before/after pairs the agent pattern-matches
└── scripts/             # optional — runnable helpers the agent can Bash directly
```

The agent loads `SKILL.md` into context when the `description` / `when_to_use` triggers fire. `references/`, `examples/`, and `scripts/` are referenced **by relative path** from inside `SKILL.md` and loaded lazily on demand.

## SKILL.md frontmatter (canonical)

```yaml
---
name: phi-redact                       # required, kebab-case
description: |                         # required — drives auto-invocation
  Detect and redact PHI from any text/code/log/diff before it leaves your machine.
  Use when the user asks to "scrub", "redact PHI", "de-identify a log",
  "check this for HIPAA leaks", or pastes patient-shaped text.
when_to_use: |                         # required — explicit triggers
  Activate when the user:
  - Pastes any text/log/JSON containing patient-shaped data
  - Asks "is this safe to share?", "does this leak PHI?"
  - Is about to commit a file containing fixtures or sample data
  - Wants to review logging/telemetry code for PHI exposure
allowed-tools: [Read, Grep, Edit, Bash]
license: MIT
tags: [hipaa, phi, security, healthcare]
incident: |                            # required — the real-world story
  Structlog redaction rules were documented in CLAUDE.md but never enforced;
  a processor could silently leak patient names into logs. PHI in a log is
  a notifiable breach under HIPAA Breach Notification Rule.
---
```

Required body sections (in order):

1. `## When to use` — bullet list of trigger phrases
2. `## How it works` — numbered, written *to the agent*
3. `## Example` — before / after pair
4. `## Edge cases` — common mistakes, gotchas
5. `## References` — links to standards & helper files

## Cross-IDE mapping

| IDE | Where files land | Format adaptation |
|---|---|---|
| Claude Code | `~/.claude/skills/<name>/` | Copy SKILL.md + sibling files verbatim |
| Cursor | `.cursor/rules/<name>.mdc` | YAML frontmatter → `.mdc` frontmatter; body unchanged |
| Codex CLI | `AGENTS.md` includes block | Top-level `AGENTS.md` references each `SKILL.md` |
| Gemini CLI | `GEMINI.md` extensions | Same SKILL.md content embedded under `## Extensions` |

`install.sh` does the appropriate per-IDE translation. Body content is identical across IDEs; only the wrapper / frontmatter shape differs.

## Validation

`scripts/validate.sh` (also wired into CI as `.github/workflows/validate-skills.yml`):

1. Every `skills/*/SKILL.md` has all required frontmatter keys
2. `name` matches the directory name
3. `description` mentions at least three trigger phrases ("Use when …, …, …")
4. Body has the five required H2 sections
5. Every `examples/*` is referenced from the body
6. Every `scripts/*` is referenced from the body
7. Tags are from the allowed taxonomy (`hipaa`, `fhir`, `hl7`, `phi`, `eval`, `audit`, `consent`, `voice`, `db`, `migration`, `security`, `linter`, `multi-tenancy`, `terminology`)

## Design principles

1. **Incident-driven** — every skill maps to a real production failure.
2. **Self-contained** — skills don't depend on each other; you can install one or all 17.
3. **Offline-first** — no required network calls; opt-in only via `.env`.
4. **Editable** — a junior engineer should be able to read and modify any SKILL.md.
5. **Standard-referenced** — link to HIPAA / HL7 / FHIR / ONC / NIST specs, don't restate them.
