# Install — Gemini CLI

## One-liner

```bash
./install.sh --ide gemini
```

This concatenates all skill bodies into a single `GEMINI.md` at the current directory, with each skill under a `## Skill: <name>` header. Gemini CLI loads `GEMINI.md` automatically when started in this directory.

## Install only one skill

```bash
./install.sh --ide gemini --skill consent-gate
```

## Verify

```bash
grep '^## Skill:' GEMINI.md            # should list 17 skills
gemini
> use consent-gate to protect the /patients/{id} endpoint
```

## Notes

- Gemini CLI doesn't yet support per-skill `allowed-tools` — the union of all `allowed-tools` is granted by Gemini's session settings.
- For best results, edit `GEMINI.md` after generation to put your most-used skills first; Gemini's loading order matters when context budget is tight.
