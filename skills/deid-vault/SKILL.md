---
name: deid-vault
description: |
  Reversible PHI pseudonymization with a keyed HMAC vault. Same input → same
  pseudonym (deterministic), nobody can re-identify without the key, and every
  re-identification call is audited. Use when the user asks to "pseudonymize",
  "tokenize patients", "de-identify for analytics but keep joinable", "build a
  re-identifiable test fixture", or wants Safe Harbor de-id with a back-door
  for forensics.
when_to_use: |
  Activate when the user:
  - Asks to pseudonymize / tokenize patient identifiers
  - Wants de-identified data that can still be joined back to source (for
    debugging or research)
  - Needs to share data with a sub-processor under a BAA
  - References HMAC-based pseudonymization, "tokenization vault", or
    "re-identifiable de-id"
  - Is building eval / staging fixtures that must look real but never expose PHI
allowed-tools: [Read, Write, Edit, Bash]
license: MIT
tags: [hipaa, phi, deid, security, vault]
incident: |
  Plain `phi-redact` is a one-way operation; useful for logs but useless when
  you need to *trace* a finding back to the original patient ("which de-id'd
  record corresponds to the patient who complained?"). Without a vault,
  engineers were copy-pasting plain MRNs into "private" channels — a worse
  outcome than a controlled, audited vault would have been. This skill
  encodes the keyed-vault pattern from fhir-mcp/deid: HMAC-SHA256 pseudonyms,
  audited re-identification, key in env not source.
---

# deid-vault

> Deterministic, reversible-with-a-key pseudonymization. Safe by default; re-id is gated and audited.

## When to use

- The user wants data de-identified for downstream use (analytics, ML, partner sharing) but reversibly so support / forensics can re-identify when needed.
- The user is building staging / eval fixtures from real patient flows and needs each fixture to map back to its source.
- The user mentions "tokenization", "pseudonymization", "HMAC vault", "re-identifiable de-id", or distinguishes their need from one-shot `phi-redact`.

## How it works

1. **Pick the identifier kinds to pseudonymize.** Common ones:
   - `MRN`
   - `patient_id` / `chart_id`
   - `name` (compound; usually pseudonymize the whole record, not individual name parts)
   - `phone`, `email`
   - `appointment_id`, `encounter_id` (item 18 — internal codes)
   - Provider names

2. **Derive a deterministic pseudonym.** For each `(kind, original)` pair:
   ```
   token = "PT_" + base32(HMAC-SHA256(key, kind || "\x00" || original))[:12]
   ```
   - **Deterministic**: same input → same pseudonym, enables joins.
   - **One-way without key**: no rainbow table possible at scale.
   - **Per-kind namespace**: `Patient/123` and `Encounter/123` pseudonymize differently.

3. **Store the mapping in a vault table.** Schema:
   ```sql
   CREATE TABLE deid_vault (
       pseudonym  TEXT PRIMARY KEY,
       original   TEXT NOT NULL,
       kind       TEXT NOT NULL,
       created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
       UNIQUE (kind, original)
   );
   ```
   This is a *deeply* sensitive table — apply field-level encryption to `original`, restrict access by IAM, audit every read.

4. **Pseudonymize an entire bundle in one pass.** Walk every PHI-bearing field, replace in place, rewrite cross-resource references (`Patient/123` → `Patient/PT_a1b2c3d4`). The fhir-mcp `deidentify_resource()` is a good reference.

5. **Gate re-identification behind a feature flag + key.**
   ```python
   if not os.environ.get("DEID_ENABLE_REID") == "true":
       raise PermissionError("re-id disabled in this deployment")
   ```
   Production data services should default `DEID_ENABLE_REID=false`. Re-id is unlocked only in support / forensics tooling.

6. **Audit every re-id.** Each call to `vault.reidentify(pseudonym)` must write an audit row including the trace ID, the actor, and the reason (a free-text justification the user typed). Quarterly review of re-id rows is mandatory.

7. **Encrypt the vault at rest.** Field-level encryption (e.g. `EncryptedType` with a per-deployment key, or pgcrypto `pgp_sym_encrypt`). The vault key (`DEID_VAULT_KEY`) lives in a secret manager, not in env files committed to disk.

8. **Run the leak scanner after pseudonymization.** Take the original PHI you removed, and grep the output for any verbatim match. Zero matches required. (This is the same `scan_for_phi_leaks()` pattern as fhir-mcp.)

## Example

**Before**
```json
{
  "resourceType": "Patient",
  "id": "12345",
  "identifier": [{"system": "http://hospital.example.org/mrn", "value": "MRN8829340"}],
  "name": [{"family": "Hernandez", "given": ["Maria"]}],
  "telecom": [{"system": "phone", "value": "415-555-0173"}],
  "birthDate": "1962-04-11"
}
```

**After (deid-vault one pass)**
```json
{
  "resourceType": "Patient",
  "id": "PT_a1b2c3d4e5f6",
  "identifier": [{"system": "http://hospital.example.org/mrn", "value": "PT_a1b2c3d4e5f6"}],
  "name": [{"family": "PT_a1b2c3d4e5f6", "given": ["PT_a1b2c3d4e5f6"]}],
  "telecom": [{"system": "phone", "value": "PT_a1b2c3d4e5f6"}],
  "birthDate": "1962"
}
```

Internally the vault now holds:
```
pseudonym=PT_a1b2c3d4e5f6  kind=PatientID  original=12345
pseudonym=PT_a1b2c3d4e5f6  kind=MRN        original=MRN8829340
pseudonym=PT_a1b2c3d4e5f6  kind=name.family original=Hernandez
…
```

(Note: in practice you'll generate *different* pseudonyms per `(kind, original)` so they don't collide. The example shows compressed output for brevity. See [`scripts/deid_vault.py`](./scripts/deid_vault.py) for the working implementation.)

**Re-id (only inside the gated support tool):**
```python
$ python -m deid_vault reidentify PT_a1b2c3d4e5f6 --reason="support ticket #4421"
12345
# audit row written: actor=support_eng:rosemary, action=deid.reidentify,
# args_hash=sha256:af..., reason="support ticket #4421"
```

## Edge cases

- **Don't reuse the same vault across deployments.** Each environment (prod, staging) needs its own key, otherwise staging tokens could be used to re-identify production data.
- **Pseudonymization is NOT Safe Harbor de-identification.** A keyed pseudonym is *still PHI* under HIPAA because the entity holds the means to re-identify. Use this skill for **internal** de-id workflows (analytics, support); use `phi-redact` plus Expert Determination or Safe Harbor for actual disclosure to third parties.
- **Birth dates need date generalization.** Even pseudonymized, "1962-04-11" can re-identify a small population. Reduce to year (see `phi-redact`).
- **Cross-resource references must be rewritten consistently.** If `Encounter.subject` points to `Patient/123`, the encounter's `subject.reference` must become `Patient/PT_xxx`.
- **Don't store `original` plaintext.** Encrypt it at rest. Compromising the vault DB without the key should still be useless.
- **Free-text fields slip through.** A clinical note that says "Mrs. Hernandez reports feeling better" can survive pseudonymization unless you also run NER over free text. Compose with `phi-redact`.
- **Pseudonym collisions.** Truncating HMAC output to 12 chars is fine at the scale of one health system (<10^7 distinct values); at higher scale, extend the token length.
- **Forgetting the leak scanner.** Always run the post-condition: grep the output for any original value. Any hit is a bug.

## References

- HIPAA Safe Harbor + Expert Determination: 45 CFR §164.514
- HIPAA limited data sets: §164.514(e) — pseudonymization is *closer* to a limited data set than to full de-id
- NIST SP 800-188 — De-Identifying Government Datasets
- [`references/safe-harbor-tests.md`](./references/safe-harbor-tests.md) — what to assert after pseudonymization
- [`scripts/deid_vault.py`](./scripts/deid_vault.py) — working Python implementation
- fhir-mcp `deid/vault.py` — production reference (HMAC + per-deployment key + Langfuse audit)
