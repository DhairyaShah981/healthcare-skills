---
name: voice-agent-lint
description: |
  Lint Retell / Vapi voice-agent JSON files for 17 known production-failure
  patterns: missing `is_transfer_cf`, empty `parameters.required`, KB IDs
  referenced but empty, ngrok URLs baked in, duplicate node IDs, unresolved
  edges, BCP-47 language errors, and more. Use when the user pastes a voice
  agent config, asks to "validate this Retell agent", "check before deploy",
  or works in a voice-agent repo.
when_to_use: |
  Activate when the user:
  - Pastes a Retell / Vapi voice-agent JSON file or asks to validate one
  - Is about to upload an agent to Retell / Vapi
  - Mentions `is_transfer_cf`, `conversationFlow`, custom function tools,
    knowledge bases, or node graphs
  - Has a voice agent that "imports but doesn't work" — likely silent runtime
    failures the linter catches
  - Asks "is my voice agent deployable?"
allowed-tools: [Read, Grep, Edit, Bash]
license: MIT
tags: [voice, linter, healthcare, retell, vapi]
incident: |
  Voice agents have an unusually high pre-prod-to-prod failure rate because
  the JSON validates as JSON but fails at Retell/Vapi import or first call.
  17 distinct rules in this skill correspond to documented production
  incidents: missing `is_transfer_cf` ('Cannot read properties of undefined'
  on three separate Iris agents), empty `parameters.required` (HTTP 400
  rejected at upload), ngrok URLs baked into committed prod JSONs (6×),
  knowledge-base IDs referenced in prompts but pointing at empty KBs.
---

# voice-agent-lint

> 17 production-failure rules for Retell / Vapi voice-agent JSON. Lints what JSON validators can't.

## When to use

- The user pastes a Retell or Vapi agent JSON file.
- The user is about to upload an agent to Retell / Vapi.
- The user mentions `conversationFlow`, `is_transfer_cf`, function tools, knowledge bases, or node graphs.
- The user has a voice agent that imports fine but doesn't work in calls.
- The user is reviewing a clinic / specialty's agent before go-live.

## How it works

Run the 17 rules below over every voice-agent JSON. Each rule has an ID (`RTL-XXX`), a severity (`ERROR` blocks deploy, `WARN` doesn't), and a pointer to the field. Output a structured report with PASS / WARN / ERROR per rule and a top-line "ready to deploy" verdict.

### The 17 rules

| ID | Severity | Rule |
|---|---|---|
| RTL-001 | ERROR | `conversationFlow.is_transfer_cf` must be present (bool). Missing → "Cannot read properties of undefined" at first call. |
| RTL-002 | ERROR | Every tool with `parameters` must have non-empty `parameters.required` (array). Empty array → Retell rejects upload with HTTP 400. |
| RTL-003 | ERROR | Every function node's `tool_id` must reference an entry in top-level `tools[]`. Dangling tool_id → silent failure (the tool just never invokes). |
| RTL-004 | ERROR | Every edge `destination_node_id` must resolve to a node in `nodes[]`. Unresolved edge → call drops at that point. |
| RTL-005 | ERROR | Node IDs must be globally unique. Duplicates → Retell picks one non-deterministically. |
| RTL-006 | ERROR | `start_node_id` must be present and resolve. Missing → agent never starts the conversation. |
| RTL-007 | ERROR | `post_call_analysis_data[].type` must be in the allowed set (`string`, `number`, `boolean`, `enum`). Other values silently dropped. |
| RTL-008 | ERROR | Language codes must be BCP-47 (`en-US`, `es-MX`). `english`, `EN`, `en_US` → Retell defaults to `en-US` silently. |
| RTL-009 | ERROR | Tool URLs must be `https://`. Plain `http://` → Retell rejects upload. |
| RTL-010 | WARN | Top-level keys missing vs the reference shape — informational, not strictly required. |
| RTL-011 | ERROR | Every tool parameter must have a `description`. Missing → Retell HTTP 400. |
| RTL-012 | ERROR | Every tool parameter must have a valid `type` (`string`, `number`, `boolean`, `array`, `object`). |
| RTL-013 | ERROR | Edge IDs must be globally unique. Duplicates → Retell rejects upload. |
| RTL-014 | ERROR | `tool_id` referenced from a function node must not be empty/null. |
| RTL-015 | WARN | Knowledge-base IDs referenced in prompts must point to non-empty KB. Empty KB → "I don't have any information about that" forever. |
| RTL-016 | ERROR | Detect ngrok / `*.local` / `localhost` URLs in webhook + tool URLs. These rot the moment the dev machine sleeps. |
| RTL-017 | WARN | Detect plaintext webhook secrets — should be placeholder tokens (see `secrets-placeholder` skill). |

### Procedure

1. **Parse the JSON.** If it doesn't parse, that's RTL-000 (not a numbered rule — just JSON syntax).

2. **Run rules left-to-right.** Each rule walks the relevant part of the document, collects findings, and emits zero or more rows.

3. **Build the report.**
   ```
   voice-agent-lint — eva-scheduling.local.json
   ─────────────────────────────────────────────
   RTL-001  ERROR  conversationFlow.is_transfer_cf missing
       → add "is_transfer_cf": false at root of conversationFlow
   RTL-002  PASS
   RTL-003  PASS
   RTL-016  ERROR  ngrok URL detected in tools[2].url
       → replace with placeholder "<<NGROK_TOOL_URL>>" + substitute at deploy time
   ...
   ─────────────────────────────────────────────
   17 rules, 14 passes, 3 errors, 0 warnings
   Verdict: BLOCK DEPLOY
   ```

4. **Offer fixes when obvious.** RTL-001 and RTL-016 have mechanical fixes; emit them as a unified diff.

5. **Don't auto-apply.** Always show the diff and ask before editing.

## Example

**Input (excerpt):**
```json
{
  "agent_name": "eva-scheduling",
  "conversationFlow": {
    "nodes": [
      {"id": "n1", "type": "start"},
      {"id": "n2", "type": "function", "tool_id": "check_availability"}
    ],
    "edges": [
      {"id": "e1", "source_node_id": "n1", "destination_node_id": "n2"}
    ]
  },
  "tools": [
    {
      "name": "check_availability",
      "url": "https://abc123.ngrok.io/availability",
      "parameters": {"type": "object", "required": [], "properties": {"date": {"type": "string"}}}
    }
  ],
  "language": "en"
}
```

**Output:**
```
voice-agent-lint
─────────────────────────────────────────────
RTL-001  ERROR  conversationFlow.is_transfer_cf is missing
   Fix: add  "is_transfer_cf": false  to conversationFlow root.

RTL-002  ERROR  tools[0] "check_availability": parameters.required is empty
   Fix: list at least one required parameter (likely "date").

RTL-006  ERROR  conversationFlow.start_node_id is missing
   Fix: set start_node_id to "n1".

RTL-008  ERROR  language="en" is not BCP-47
   Fix: use "en-US" (or the appropriate regional variant).

RTL-011  ERROR  tools[0].parameters.properties.date is missing "description"
   Fix: add a one-sentence description.

RTL-016  ERROR  tools[0].url contains ngrok hostname
   Fix: replace with placeholder <<TOOL_URL_CHECK_AVAILABILITY>> and substitute at deploy.

RTL-017  WARN  tools[0] has no webhook secret declared
   Fix: add a verified-webhook-secret reference (see secrets-placeholder).
─────────────────────────────────────────────
17 rules, 10 passes, 6 errors, 1 warning
Verdict: BLOCK DEPLOY
```

## Edge cases

- **Tool URL templating** — some agents intentionally use a placeholder string for tool URLs (e.g. `<<EHR_BASE_URL>>`); the linter should detect the placeholder syntax and mark RTL-016 as PASS, not ERROR.
- **Multi-language agents** — when there are language variants (en-US, es-MX), every variant must pass independently. Don't accept "the English one is fine."
- **`is_transfer_cf` on non-transfer agents** — even agents that don't transfer must set this field (to `false`); the Retell SDK reads it unconditionally.
- **KB ID emptiness is a runtime concern.** Some users intentionally ship an empty KB during development; warn but don't error if a comment field or filename suggests "wip".
- **Test fixtures** — files in `tests/` or with `_test` / `_mock` in the name should be skipped or warned about, not errored on.
- **Vapi shares 90% of the rules but uses different field names.** Detect the platform from a top-level field; route to Retell or Vapi rule variants accordingly.

## References

- Retell function tool reference: <https://docs.retellai.com/build/tools/custom-function>
- Retell conversation flow reference: <https://docs.retellai.com/build/conversation-flow/overview>
- Vapi assistant reference: <https://docs.vapi.ai/assistants>
- BCP-47 language tags: <https://www.rfc-editor.org/rfc/bcp/bcp47.txt>
- [`references/retell-rule-reference.md`](./references/retell-rule-reference.md) — per-rule rationale
- [`scripts/lint_voice_agent.py`](./scripts/lint_voice_agent.py) — runnable linter
- [`examples/broken-agent.json`](./examples/broken-agent.json) — exemplar with multiple failures
