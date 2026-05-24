# Skill-pack composition — `extends:`

> Status: documented pattern. The `install.sh` and `bin/healthcare-skills.js` already support per-skill overrides via the SKILL.md frontmatter, and the layout below is the conventional way to host a private overlay on top of the public pack.

A team often needs healthcare-skills **plus** a small set of org-specific rules: clinic identifiers, internal API base URLs, audit table column names, a custom prompt overlay. The way to do this without forking is **pack composition**.

## Layout

```
my-org/
├── healthcare-skills/                       # the public pack, cloned or git submoduled
└── healthcare-skills-overlay/               # your private overlay repo
    ├── overlay.yaml                         # declares: extends: healthcare-skills@0.4.0
    └── skills/
        ├── audit-trail/                     # overrides for an existing public skill
        │   ├── SKILL.md.overlay             # appended to the public SKILL.md body
        │   └── references/audit-event-schema.md   # REPLACES the public file (by path)
        └── my-custom-skill/                 # a brand-new skill, private to the org
            └── SKILL.md
```

## `overlay.yaml`

```yaml
extends: healthcare-skills@0.4.0       # exact public version this overlay tracks
license: proprietary                   # downstream files inherit unless overridden
notes: |
  Acme Health's internal overlay. Adds tenant-id column rename, internal
  audit retention, and three private specialty templates.

overrides:
  audit-trail:
    references/audit-event-schema.md: replace   # private schema with renamed columns
    SKILL.md: append                            # add an "Internal addendum" section
  consent-gate:
    SKILL.md: append

additions:
  - my-custom-skill                            # new skill names in skills/
```

## Resolution rules

1. **Path-level merge.** For each path under `skills/<name>/`:
   - If the path exists in the overlay only → add it
   - If it exists in both with `replace` → overlay wins
   - If it exists in both with `append` → overlay body is appended to the public file
   - If it exists in the public pack only → keep the public version
2. **No cross-skill imports.** Each skill stays self-contained — composition is per-skill.
3. **Versioning.** `overlay.yaml#extends` pins the public version. CI in the overlay repo asserts the public version hasn't drifted (or runs the overlay's tests against newer public versions).

## Building a composed install

```bash
# from inside the overlay repo
./scripts/compose.sh \
    --public ../healthcare-skills \
    --overlay . \
    --out ../merged

# the merged tree is what you pass to install.sh or `npx healthcare-skills`
../healthcare-skills/install.sh --skills-root ../merged/skills --ide claude-code
```

`scripts/compose.sh` is intentionally not yet shipped in this repo — it's expected to be a ~50-line bash script per the rules above, and most teams want to author it themselves so they can wire in their own secret-manager substitutions (see `secrets-placeholder` skill) at compose time.

## Why not just fork?

A fork:
- decouples you from upstream improvements
- forces a manual sync each time the public pack ships a new skill
- bundles your private code with public mirroring (you can't easily contribute back)

Composition keeps the two surfaces separate. Public bug fixes flow automatically; private business logic stays out of the public repo.

## Future: making this first-class

If there's appetite, v0.6 could ship:
- `healthcare-skills compose <overlay-path>` subcommand
- a JSON Schema for `overlay.yaml`
- CI helper that asserts overlay-vs-public compatibility on every PR

For now, the pattern is documented; teams can adopt it without waiting on tooling.
