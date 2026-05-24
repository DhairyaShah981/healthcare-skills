# healthcare-skills

> Production-grade Claude Code / Cursor / Codex CLI / Gemini CLI skills for engineers building healthcare and other regulated software.

**27 skills. Real incidents. Plug-and-play. CLI + web discovery.**

Every skill in this pack maps to a documented production incident from real healthcare engineering — Alembic migration crashes, ngrok URLs baked into voice agents, PHI silently leaking into structlog, JSONB schemas drifting from their Pydantic models, multi-tenant queries missing `client_id` predicates. The skills encode the fix so you (or your AI pair) never re-discover the same trap.

Built in the [mattpocock/skills](https://github.com/mattpocock/skills) `SKILL.md` format. Works with **Claude Code**, **Cursor**, **Codex CLI**, and **Gemini CLI**.

---

## 30-second install

Three ways. Pick one.

```bash
# ── option A: clone + install.sh ───────────────────────────────────
git clone https://github.com/DhairyaShah981/healthcare-skills.git
cd healthcare-skills
./install.sh                 # auto-detects IDE; or --ide claude-code|cursor|codex|gemini

# ── option B: npx (no clone) ───────────────────────────────────────
npx healthcare-skills add-all --ide claude-code
npx healthcare-skills add phi-redact --ide cursor
npx healthcare-skills list
npx healthcare-skills search hipaa

# ── option C: browse the catalog visually ─────────────────────────
# https://dhairyashah981.github.io/healthcare-skills (GitHub Pages)
# search, filter by tag, see which skills have runnable code
```

Then open a new chat in your IDE and ask:

> *"Use phi-redact to scrub this log."*
> *"Use fhir-bundle to generate a Patient + Encounter + Observation bundle for hypertension follow-up."*
> *"Use hipaa-review on the current diff."*

---

## The 27 skills

### Tier 0 — Universal, drop-in
| Skill | What it does |
|---|---|
| [`phi-redact`](skills/phi-redact/SKILL.md) | Detect & redact PHI from text, code, logs, or diffs (Safe Harbor 18 identifiers). |
| [`fhir-bundle`](skills/fhir-bundle/SKILL.md) | Generate valid FHIR R4 bundles (Patient + Encounter + Observation + …) from a clinical description. |
| [`hipaa-review`](skills/hipaa-review/SKILL.md) | Review a git diff for HIPAA Security Rule violations (encryption-at-rest, audit logging, access control). |

### Tier 1 — Core healthcare engineering
| Skill | What it does |
|---|---|
| [`clinical-eval`](skills/clinical-eval/SKILL.md) | Scaffold reproducible eval suites for clinical AI (Synthea fixtures + LLM-as-judge). |
| [`audit-trail`](skills/audit-trail/SKILL.md) | Wrap any function handling patient data with `@audited()` + `AuditEvent` table. |
| [`consent-gate`](skills/consent-gate/SKILL.md) | Add a patient-consent verification gate to FastAPI / Express endpoints. |
| [`deid-vault`](skills/deid-vault/SKILL.md) | Reversible HMAC pseudonymization with a keyed vault + leak scanner. |
| [`hl7-transform`](skills/hl7-transform/SKILL.md) | Parse HL7v2 (ADT, ORU, SIU) and roundtrip to / from FHIR R4. |
| [`cds-hook`](skills/cds-hook/SKILL.md) | Scaffold CDS Hooks 1.0 services (patient-view, medication-prescribe, order-select). |
| [`icd-snomed-map`](skills/icd-snomed-map/SKILL.md) | Map between ICD-10, SNOMED-CT, CPT, LOINC, RxNorm (offline + `tx.fhir.org` fallback). |

### Tier 2 — From real production incidents
These are skills you didn't know you needed until a 2 AM Slack notification taught you otherwise.
| Skill | What it does | The incident |
|---|---|---|
| [`voice-agent-lint`](skills/voice-agent-lint/SKILL.md) | 17 production-failure rules for Retell / Vapi voice-agent JSONs. | Missing `is_transfer_cf` → import 500s in three Iris agents. |
| [`alembic-guard`](skills/alembic-guard/SKILL.md) | Enforce ≤32-char revision IDs + linear chain pre-commit. | Three production crashes — `alembic_version.version_num` is `varchar(32)`. |
| [`jsonb-pydantic-pair`](skills/jsonb-pydantic-pair/SKILL.md) | Every `Column(JSONB)` must have a matching Pydantic schema. | 26+ unmodeled JSONB columns → untraceable KeyErrors at runtime. |
| [`tenant-rls-guard`](skills/tenant-rls-guard/SKILL.md) | Detect missing `.where(Model.client_id == ...)` in multi-tenant queries. | One missing predicate from a cross-tenant data leak. |
| [`async-blocking-lint`](skills/async-blocking-lint/SKILL.md) | Flag `requests` / `urllib` calls inside `async def`. | Event loop blocked under call-burst load. |
| [`secrets-placeholder`](skills/secrets-placeholder/SKILL.md) | Scaffold placeholder-token + Secret Manager substitution. | 6× ngrok URLs baked into committed production agent JSON. |
| [`synthea-fixture`](skills/synthea-fixture/SKILL.md) | Generate frozen Synthea-style FHIR bundles for deterministic evals. | Eval suite drifted because patient fixtures regenerated each run. |

### Tier 3 — v0.2 + v0.3 additions
Incident backlog plus the most-asked-for healthcare workflows.
| Skill | What it does |
|---|---|
| [`smart-oauth-scaffold`](skills/smart-oauth-scaffold/SKILL.md) | Scaffold SMART on FHIR launch + Fernet-encrypted token storage + refresh-on-401 for Epic / Cerner / Athena. |
| [`prior-auth-fhir`](skills/prior-auth-fhir/SKILL.md) | Build Da Vinci PAS / CRD / DTR payloads — `CoverageEligibilityRequest`, PAS `Claim`, `QuestionnaireResponse`. |
| [`route-fatness`](skills/route-fatness/SKILL.md) | Lint fat route handlers — line count, external calls, DB queries, branch depth — and suggest the service-layer extraction. |
| [`clinic-config-extract`](skills/clinic-config-extract/SKILL.md) | Find hardcoded clinic / tenant slugs across the codebase and refactor them into a single YAML config. |
| [`migration-bisect`](skills/migration-bisect/SKILL.md) | `git bisect` for Alembic migrations: ephemeral DB, apply one at a time, smoke probe between each. |
| [`webhook-verify`](skills/webhook-verify/SKILL.md) | Constant-time HMAC verification for Retell / Vapi / Twilio / Stripe / Slack / GitHub webhooks with replay-window enforcement. |
| [`phi-log-filter`](skills/phi-log-filter/SKILL.md) | Continuous PHI-scrubbing processor for structlog / Python logging / loguru / winston / pino — every log call gets the scrub. |
| [`specialty-scaffold`](skills/specialty-scaffold/SKILL.md) | Scaffold a new clinical specialty (cardiology / ENT / GI / derm / peds / …) on top of a shared base — overrides only, no copy-paste. |
| [`epic-sandbox-bootstrap`](skills/epic-sandbox-bootstrap/SKILL.md) | 12-step Epic on FHIR sandbox onboarding checklist + runnable smoke-test that exercises Patient.read / Observation.search. |
| [`cds-hook-tester`](skills/cds-hook-tester/SKILL.md) | Golden-fixture regression for a CDS Hooks 1.0 service — discovery check + per-hook subset-match. |

---

## CLI, TypeScript impls, and the web catalog

**CLI** — `npx healthcare-skills <cmd>` or `node bin/healthcare-skills.js <cmd>` from a checkout.
| Subcommand | Does |
|---|---|
| `list` | List every skill |
| `info <name>` | Print frontmatter + incident for one skill |
| `add <name>` | Install one skill into the detected IDE (`--ide` to override) |
| `add-all` | Install every skill |
| `search <q>` | Search names / descriptions / tags |
| `tags` | Show every tag with counts |
| `doctor` | Sanity-check the install (IDE detection, frontmatter) |

Flags: `--ide`, `--skills-root`, `--dry-run`, `--json`.

**TypeScript reference implementations** — 7 zero-dep Node packages, all tested with `node --test`:
- [`ts/phi-log-filter`](ts/phi-log-filter/) — pino + winston redactor (4 tests)
- [`ts/webhook-verify`](ts/webhook-verify/) — HMAC verifiers for 7 providers (9 tests)
- [`ts/audit-trail`](ts/audit-trail/) — `audited()` wrapper + Express middleware (3 tests)
- [`ts/consent-gate`](ts/consent-gate/) — SMART scope + FHIR Consent middleware (10 tests)
- [`ts/deid-vault`](ts/deid-vault/) — reversible HMAC pseudonymization vault (6 tests)
- [`ts/tenant-rls-guard`](ts/tenant-rls-guard/) — TS / JS multi-tenant query linter (8 tests)
- [`ts/voice-agent-lint`](ts/voice-agent-lint/) — RTL-001..017 in TS (8 tests)

**Web catalog** — the static site under [`docs/site/`](docs/site/) auto-deploys to GitHub Pages. Every card opens a dedicated [incident landing page](docs/site/incident.html?skill=phi-redact) with the full incident, when-to-use bullets, tier, runnable-code indicators, and an `npx` install command. Live at <https://dhairyashah981.github.io/healthcare-skills>.

**Skill-pack composition** — extend the public pack with private overlays per [`docs/COMPOSITION.md`](docs/COMPOSITION.md).

---

## Why "skills"?

A **skill** is a focused, model-agnostic instruction set the AI loads on demand. Unlike a system prompt (loaded for every turn) or a tool (a single function call), a skill bundles:

- **When to activate** — explicit trigger phrases & file globs
- **What to do** — step-by-step instructions
- **Reference material** — schemas, regex catalogs, code-system URIs
- **Examples** — before/after pairs the model can pattern-match against
- **Optional runnable code** — `scripts/` the agent can `Bash` directly

Skills travel with the repo. They're version-controlled, reviewable in PRs, and portable across IDEs. Healthcare engineering has unusually high "you should have known" cost — skills are the lowest-friction way to encode that institutional knowledge so a junior engineer (or AI pair) doesn't re-learn it the hard way.

---

## Cross-IDE support

| IDE | Native format | How to install |
|---|---|---|
| Claude Code | `~/.claude/skills/<name>/SKILL.md` | `./install.sh --ide claude-code` → [docs](docs/install/claude-code.md) |
| Cursor | `.cursor/rules/<name>.mdc` | `./install.sh --ide cursor` → [docs](docs/install/cursor.md) |
| Codex CLI | `AGENTS.md` includes | `./install.sh --ide codex` → [docs](docs/install/codex-cli.md) |
| Gemini CLI | `GEMINI.md` extensions | `./install.sh --ide gemini` → [docs](docs/install/gemini-cli.md) |

---

## Optional API keys

All 17 skills work fully **offline**. Three skills have optional online integrations — see [`.env.example`](.env.example):

- `ANTHROPIC_API_KEY` / `OPENAI_API_KEY` — only used by `clinical-eval` for LLM-as-judge scoring
- `UMLS_API_KEY` — only used by `icd-snomed-map` for the full SNOMED-CT vocabulary
- `tx.fhir.org` — public terminology fallback, no key required, on by default

---

## Contributing

Found a healthcare-engineering trap that should be a skill? PRs welcome.

1. Copy `skills/_template/` to `skills/<your-skill>/`.
2. Fill in `SKILL.md` (the [template](skills/_template/SKILL.md) lists every required frontmatter field).
3. Add at least one `examples/` before/after pair.
4. Run `./scripts/validate.sh` — it lints frontmatter + checks examples render.
5. Open a PR with: the real-world incident that motivated the skill, a unit-test fixture, and a one-line README addition.

See [CONTRIBUTING.md](CONTRIBUTING.md) for the full guide.

---

## Used by

*Placeholder — if you ship something with this pack, open a PR adding your org here.*

- *(your org could be here)*

---

## License

[MIT](LICENSE) — use freely, modify freely, ship freely.

---

## Acknowledgements

Patterns and incidents drawn from production work on the Trifetch healthcare platform (clinic-os, voice-service, fhir-mcp, voice-eval-harness, retell-agents-engine). No PHI, no proprietary code, no client data appears in this repo — only the lessons.
