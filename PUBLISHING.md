# Publishing — healthcare-skills

Two channels: **GitHub Releases** (handled by the maintainer / CI) and **npm** (one-time auth required).

## GitHub Release

Every push to `main` is a release candidate; an actual release goes out via `gh`:

```bash
# 1. Bump the version in package.json and CHANGELOG.md, commit, tag.
git tag v0.4.0
git push origin v0.4.0

# 2. Build the tarball npm would publish.
npm pack          # emits healthcare-skills-0.4.0.tgz

# 3. Create the release with the tarball attached.
gh release create v0.4.0 \
    --title "v0.4.0 — 3 more TS ports + incident landing pages" \
    --notes-file <(awk '/^## \[/{n++} n==1' CHANGELOG.md) \
    healthcare-skills-0.4.0.tgz
```

## npm

`healthcare-skills` is currently unclaimed on npm (verified with `npm view healthcare-skills` returning 404).
Publishing the first version requires interactive auth on the maintainer's machine **once**:

```bash
# One-time auth (will open a browser).
npm login

# Verify.
npm whoami

# Publish (uses `files` in package.json — see below for what ships).
npm publish --access public
```

After the first publish, downstream installs become:

```bash
npx healthcare-skills add phi-redact --ide claude-code
npx healthcare-skills list
npm install -g healthcare-skills
healthcare-skills doctor
```

## What ships in the npm tarball

`package.json` declares:
```json
"files": ["bin/", "skills/", "install.sh", "LICENSE", "README.md"]
```
- `bin/healthcare-skills.js` — the CLI
- `skills/<every-skill>/SKILL.md + references/ + examples/ + scripts/` — the catalog
- `install.sh` — for users who clone instead of `npx`
- `LICENSE`, `README.md`

Use `npm pack --dry-run` to inspect the exact set before publishing.

## Continuous publish (recommended once npm auth lands)

Add this to `.github/workflows/release.yml`:

```yaml
on:
  push:
    tags: ['v*.*.*']
jobs:
  npm-publish:
    runs-on: ubuntu-latest
    permissions: { contents: write, id-token: write }
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: 20, registry-url: 'https://registry.npmjs.org' }
      - run: npm publish --provenance --access public
        env:
          NODE_AUTH_TOKEN: ${{ secrets.NPM_TOKEN }}
```

Then add the npm token to repo secrets (`NPM_TOKEN`) — `https://www.npmjs.com/settings/<user>/tokens` → "Automation".

## Version bump checklist

- [ ] Update `package.json` `version`
- [ ] Update `CHANGELOG.md` (move Unreleased → new version, add link refs)
- [ ] Update `README.md` skill count if changed
- [ ] Update `docs/ROADMAP.md`
- [ ] Run full test suite: `bash tests/cli.bats && for d in ts/*/; do (cd $d && node --test test/smoke.test.js); done && ./scripts/validate.sh`
- [ ] Commit
- [ ] `git tag v<version>` + `git push --tags`
- [ ] `gh release create v<version>`
- [ ] (if authed) `npm publish --access public`
