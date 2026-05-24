# Voice-agent rule reference (RTL-001 — RTL-017)

For each rule: the failure mode, the production incident that motivated it, and the fix.

## RTL-001 — `conversationFlow.is_transfer_cf` missing
**Failure**: At call start, the Retell client SDK reads `is_transfer_cf` unconditionally. Missing → JS reference error `Cannot read properties of undefined (reading 'is_transfer_cf')`. Call drops within 50ms of pickup.

**Incident**: Three separate Iris-clinic agents were uploaded without this field. Each took ~12 hours to diagnose because the import succeeds and the Retell dashboard says "ready."

**Fix**: Add `"is_transfer_cf": false` to the `conversationFlow` root. (Use `true` only for transfer flows.)

---

## RTL-002 — Empty `tool.parameters.required`
**Failure**: Retell rejects upload with HTTP 400: *"parameters.required must be a non-empty array."*

**Incident**: A router-agent's `transfer_to_subagent` tool shipped with `required: []`. The agent linted cleanly in pre-merge review but failed at upload.

**Fix**: List every parameter that the function genuinely needs. If a parameter is truly optional, move it out of `required` and the tool will still work.

---

## RTL-003 — Dangling `tool_id` on a function node
**Failure**: Silent. The agent runs, the function node fires, but the tool never invokes. No error in the dashboard.

**Incident**: A copy-paste agent referenced `tool_id: "check_insurance"` from a parent template. The actual tool was named `verify_insurance`. The "agent doesn't ask about insurance" bug took two weeks to root-cause.

**Fix**: Cross-check every function-node `tool_id` against the `tools[]` array at the top level.

---

## RTL-004 — Unresolved `destination_node_id`
**Failure**: At runtime, the conversation reaches the edge, can't resolve the destination, and the call drops.

**Incident**: An agent had an edge pointing at a node that was later renamed; the edge wasn't updated.

**Fix**: For every edge, verify `destination_node_id` exists in `nodes[]`. Build a set first; check in O(1).

---

## RTL-005 — Duplicate node IDs
**Failure**: Retell picks one non-deterministically. Sometimes works, sometimes doesn't.

**Fix**: Node IDs must be unique within `conversationFlow.nodes[]`. Use UUIDs or a `nN_purpose` convention.

---

## RTL-006 — Missing or unresolved `start_node_id`
**Failure**: The agent never says anything. Calls connect and then go silent.

**Fix**: `conversationFlow.start_node_id` must be present and reference a node that exists.

---

## RTL-007 — Invalid `post_call_analysis_data[].type`
**Failure**: Allowed values are `string`, `number`, `boolean`, `enum`. Anything else is silently dropped from the post-call payload.

**Incident**: A `date` type was set for an "appointment_time" field; downstream automation expected a date string but got `undefined`.

**Fix**: Map to the closest allowed type (usually `string` with explicit format guidance in the description).

---

## RTL-008 — Non-BCP-47 language code
**Failure**: Retell silently defaults to `en-US`.

**Incident**: A Spanish-speaking clinic shipped `language: "spanish"`; agent spoke English for two weeks.

**Fix**: Use BCP-47 (`en-US`, `es-MX`, `es-419` for Latin-American Spanish, `hi-IN`, etc.).

---

## RTL-009 — Non-HTTPS tool URL
**Failure**: Retell rejects upload.

**Fix**: Use `https://` for all tool URLs. If you don't have HTTPS in dev, use a tunneling service that provides HTTPS (e.g. ngrok's HTTPS endpoint).

---

## RTL-010 — Top-level key shape mismatch (informational)
**Failure**: None directly; informational alert that the agent doesn't match the canonical shape (newer fields added, older ones removed).

**Fix**: Periodically regenerate against the latest reference template.

---

## RTL-011 — Tool parameter missing `description`
**Failure**: Retell HTTP 400.

**Fix**: Every parameter in `parameters.properties` must have a one-sentence description. Be specific — "date" is bad; "date of the desired appointment in ISO YYYY-MM-DD format" is good.

---

## RTL-012 — Invalid parameter `type`
**Failure**: Retell HTTP 400.

**Fix**: Use one of `string`, `number`, `integer`, `boolean`, `array`, `object`. JSON Schema-compatible.

---

## RTL-013 — Duplicate edge IDs
**Failure**: Retell rejects upload.

**Fix**: Edge IDs must be globally unique within `conversationFlow.edges[]`.

---

## RTL-014 — `tool_id` null/empty on function node
**Failure**: Like RTL-003 but caught earlier (at upload, not at runtime).

**Fix**: Every function node must reference a real tool.

---

## RTL-015 — KB referenced but empty
**Failure**: The agent will respond "I don't have any information about that" indefinitely.

**Incident**: A Stockton clinic agent referenced KB `stockton-services-v1` in the system prompt; the KB had been deleted during a cleanup. Agent ran in production for ~5 days saying "I don't know that" to every clinical question.

**Fix**: Either populate the KB or remove the reference.

---

## RTL-016 — ngrok / localhost / `*.local` URL
**Failure**: Works until the dev laptop sleeps; then production calls hit a dead endpoint.

**Incident**: Six separate Eva-scheduling agents shipped to production with `*.ngrok.io` URLs. Each broke the moment the developer closed their laptop on a Friday.

**Fix**: Use `<<PLACEHOLDER>>` tokens in committed JSON and substitute from GCP / AWS Secret Manager at deploy time (see `secrets-placeholder` skill).

---

## RTL-017 — Plaintext webhook secret
**Failure**: Anyone with read access to the repo can authenticate as the agent's backend.

**Fix**: Use the placeholder pattern; substitute secrets at deploy time.

---

## Severity policy

- `ERROR` rules block deploy. CI should fail.
- `WARN` rules pass deploy but should be tracked in an issue.
- Rules can be escalated/de-escalated via a per-repo `.voice-lint.yaml` config.
