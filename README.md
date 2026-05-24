# healthcare-skills

> Production-grade Claude Code / Cursor / Codex CLI / Gemini CLI skills for engineers building healthcare and other regulated software.

**17 skills. Real incidents. Plug-and-play.**

Every skill in this pack maps to a documented production incident from real healthcare engineering — Alembic migration crashes, ngrok URLs baked into voice agents, PHI silently leaking into structlog, JSONB schemas drifting from their Pydantic models, multi-tenant queries missing `client_id` predicates. The skills encode the fix so you (or your AI pair) never re-discover the same trap.

Built in the [mattpocock/skills](https://github.com/mattpocock/skills) `SKILL.md` format. Works with **Claude Code**, **Cursor**, **Codex CLI**, and **Gemini CLI**.

---

## 30-second install

```bash
git clone https://github.com/DhairyaShah981/healthcare-skills.git
cd healthcare-skills
./install.sh                 # detects your IDE; or pass --ide claude-code|cursor|codex|gemini
```

That's it. Open a new chat in your IDE and ask:

> *"Use phi-redact to scrub this log."*
> *"Use fhir-bundle to generate a Patient + Encounter + Observation bundle for hypertension follow-up."*
> *"Use hipaa-review on the current diff."*

> A 30-second install demo lives at [`docs/install.gif`](docs/install.gif) (recorded with [asciinema](https://asciinema.org)).

---

## The 17 skills

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
