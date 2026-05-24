# Install — Codex CLI

## One-liner

```bash
./install.sh --ide codex
```

This writes an `AGENTS.md` at the current directory that `@includes` each skill's `SKILL.md`. Codex CLI loads `AGENTS.md` automatically when started in this directory.

## Install only one skill

Codex's AGENTS.md is monolithic — every install rewrites it. To restrict, use `--skill`:

```bash
./install.sh --ide codex --skill audit-trail
```

## Verify

```bash
head -20 AGENTS.md
codex                                # start codex in this dir
> use audit-trail on the get_patient function in app/routes/patients.py
```

## Notes

- Codex CLI's resolution of `@include` is path-relative to `AGENTS.md`, so don't move `AGENTS.md` away from the repo root.
- If you maintain a project-level `AGENTS.md` already, run `./install.sh --ide codex --dry-run` first to see the generated content, then merge by hand.
