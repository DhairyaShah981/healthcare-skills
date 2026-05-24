# Install — Cursor

## One-liner

```bash
./install.sh --ide cursor
```

This writes one `.mdc` file per skill into `.cursor/rules/` of the current project. The SKILL.md body is preserved verbatim; the YAML frontmatter is compatible with Cursor's MDC format.

## Project-level vs global

Cursor scopes rules per project. Run `./install.sh --ide cursor` **from inside the project repo** where you want the skills active. To make them global, copy the resulting `.cursor/rules/*.mdc` into `~/.cursor/rules/`.

## Install only one skill

```bash
./install.sh --ide cursor --skill fhir-bundle
```

## Verify

```bash
ls .cursor/rules/                       # should list every skill as <name>.mdc
```

Reload the Cursor window (Cmd/Ctrl-Shift-P → "Developer: Reload Window") and chat:

> *"Use fhir-bundle to generate a bundle for a 65-year-old with hypertension."*

## Notes

- Cursor doesn't yet support skill-level `allowed-tools`; tool access is governed by Cursor's global settings.
- `references/` and `examples/` files are not copied automatically by the `.mdc` route; if a skill needs them, copy the whole `skills/<name>/` folder into the project too.
