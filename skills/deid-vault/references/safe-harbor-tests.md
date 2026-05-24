# Post-pseudonymization assertions

After `deid-vault` rewrites a payload, run these checks. Every assertion that fails is a bug.

## A1. Structural removal of the 18 identifiers

For each Safe Harbor identifier (see `phi-redact/references/safe-harbor-18.md`), assert it does not appear verbatim in the output:

```python
def assert_structural(original_phi: set[str], output: str) -> None:
    leaked = {p for p in original_phi if p in output}
    assert not leaked, f"verbatim PHI leak: {leaked}"
```

## A2. Regex leakage

Apply the regex catalogue from `phi-redact/references/regex-patterns.md`. Output must produce **zero** matches:

```python
RE_LEAKAGE_PATTERNS = [
    ("SSN",   re.compile(r"\b\d{3}-\d{2}-\d{4}\b")),
    ("PHONE", re.compile(r"\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b")),
    ("EMAIL", re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")),
    ("DOB",   re.compile(r"\b(19|20)\d{2}-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])\b")),
    ("MRN",   re.compile(r"(?i)\bMRN[:\s#]*[A-Z]?\d{6,10}\b")),
]
```

## A3. Reference graph still intact

If `Patient/123` was rewritten to `Patient/PT_xxx`, every `subject.reference` and `patient.reference` in other resources must use the *same* `PT_xxx`. Walk the bundle and assert:

```python
def assert_refs_resolve(bundle):
    ids = {e["resource"].get("id") for e in bundle["entry"]}
    for e in bundle["entry"]:
        for ref in find_refs(e["resource"]):
            target_id = ref.split("/")[-1]
            assert target_id in ids, f"dangling reference: {ref}"
```

## A4. Date generalization

Birth dates and any clinical date used in narrative must be year-only or month-only — never the full ISO date. Detect:

```python
DATE_RE = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")
assert not DATE_RE.search(output), "full date in output (use year-only)"
```

The exception: dates carried in structured fields meant for clinical timing (Observation.effectiveDateTime) may need to remain full. Document the per-field decision.

## A5. Free-text NER sweep

Run a NER model over all free-text fields (`Observation.note`, `Condition.code.text`, etc.) and assert no `PERSON` / `LOCATION` entities survive:

```python
from spacy import load
nlp = load("en_core_web_lg")

def assert_no_named_entities(text: str) -> None:
    doc = nlp(text)
    leaked = [ent for ent in doc.ents if ent.label_ in {"PERSON", "GPE", "LOC"}]
    assert not leaked, f"NER leak: {[ent.text for ent in leaked]}"
```

## A6. Determinism

Run the pseudonymization twice; outputs must be byte-identical:

```python
def assert_deterministic(input_payload):
    a = vault.pseudonymize(input_payload)
    b = vault.pseudonymize(input_payload)
    assert a == b, "pseudonymization is non-deterministic"
```

Non-determinism breaks downstream joins.

## A7. Reversibility within the vault

For every pseudonym in the output, `vault.reidentify(pseudonym)` must return the original (when re-id is enabled):

```python
def assert_reversible(input_payload, output):
    pseudonyms = find_all_pseudonyms(output)
    for ps in pseudonyms:
        original = vault.reidentify(ps, reason="post-deid test")
        assert original is not None, f"vault missing entry for {ps}"
```

## A8. Audit row for every re-id

Every `vault.reidentify()` call must produce an `audit_event` row with `action="deid.reidentify"`, an actor, a `reason`, and a `trace_id`. Test the audit table after the eval.

## A9. Cross-environment isolation

`vault.reidentify(prod_pseudonym)` in staging must return `None` (or raise) — staging vault has a different key, can't reverse prod tokens. Add a smoke test that confirms this.

## A10. Leak scanner as CI gate

Wire all A1–A9 into a single test that runs in CI on every PR touching `deid_vault.py` or any FHIR builder. Fail closed.
