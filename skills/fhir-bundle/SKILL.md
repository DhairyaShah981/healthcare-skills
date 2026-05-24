---
name: fhir-bundle
description: |
  Generate a valid FHIR R4 transaction or collection Bundle from a natural-language
  clinical description. Use when the user asks to "build a FHIR bundle", "make a
  Patient + Encounter + Observation", "create a FHIR resource for X", "give me a
  Bundle JSON for a 65-year-old with hypertension", or pastes clinical notes and
  asks for FHIR.
when_to_use: |
  Activate when the user:
  - Asks to construct any FHIR resource (Patient, Encounter, Observation, Condition,
    MedicationRequest, AllergyIntolerance, Procedure, DiagnosticReport, Bundle)
  - Pastes a clinical scenario and asks to model it as FHIR
  - Wants to seed a development EHR with synthetic patients
  - Asks "what's the FHIR shape for X?", "give me an example Observation", etc.
  - Is integrating with an EHR sandbox and needs a starter payload
allowed-tools: [Read, Write, Edit, Bash]
license: MIT
tags: [fhir, healthcare, interop]
incident: |
  In one production system the only existing FHIR-construction code was scattered
  across multiple endpoints, each with subtly different `meta.profile` handling
  and divergent identifier-system URLs. New developers wrote bundles by copy-paste
  and got "valid FHIR" that the receiver rejected. This skill centralises the
  shape so the bundle is always valid against US Core 6.1.0.
---

# fhir-bundle

> Generate valid FHIR R4 Bundles from a clinical description. US Core 6.1.0 conformant.

## When to use

- The user describes a clinical scenario ("65-year-old man with poorly-controlled hypertension, just had an annual visit") and wants the FHIR representation.
- The user is building a test fixture, an EHR sandbox seed, or an integration payload.
- The user asks for one specific resource ("what does an Observation for an HbA1c look like?").
- The user is debugging a bundle that's being rejected by a receiver.

## How it works

1. **Pin the version.** Default to **FHIR R4 (4.0.1)** and **US Core 6.1.0** unless the user specifies otherwise. Bundle resources should set `meta.profile` to the relevant US Core profile URL (e.g. `http://hl7.org/fhir/us/core/StructureDefinition/us-core-patient`).

2. **Pick the Bundle type.**
   - `transaction` — when the receiver should process the entries atomically and assign IDs. Each entry needs a `request` block.
   - `batch` — independent operations, partial failures allowed.
   - `collection` — a static set of resources; no server processing. Best for fixtures.
   - When in doubt: ask the user, or default to `collection` for fixtures and `transaction` for live EHR writes.

3. **Use synthetic data only.** Names, DOBs, MRNs in examples must come from the synthetic patient set ("John Synthea", "Jane Doe", DOB year-only) — never real-looking PII. If the user pastes real-looking patient data, suggest running `phi-redact` first.

4. **Generate stable references inside the bundle.** Use `urn:uuid:` style for the `fullUrl` of each entry and reference resources by that URN. This makes the bundle valid even before the server assigns canonical IDs.

5. **Always include `identifier` for Patient.** Use a clear `system` URL (e.g. `http://hospital.example.org/mrn`) and a `value`. Without an identifier the receiver typically can't deduplicate.

6. **Set `subject` (or `patient`) reference on every clinical resource.** Observation, Condition, MedicationRequest, Encounter all reference the Patient by `urn:uuid:…`. Verify the referenced UUID exists in the same bundle.

7. **Bind coded values to a `system`.** Never put a raw code in `Coding.code` without a `Coding.system`. Common systems:
   - SNOMED CT: `http://snomed.info/sct`
   - LOINC: `http://loinc.org`
   - ICD-10-CM: `http://hl7.org/fhir/sid/icd-10-cm`
   - RxNorm: `http://www.nlm.nih.gov/research/umls/rxnorm`
   - CPT: `http://www.ama-assn.org/go/cpt`

   Need a mapping? Hand off to the `icd-snomed-map` skill.

8. **Validate.** When the user has `fhir-validator` (HL7 Java validator) or `node-fhir-validator` available, run it. Otherwise do a structural check: every reference resolves, every coded value has both `system` and `code`, every required field per US Core is present.

9. **Emit the bundle as pretty-printed JSON** (`indent=2`) and include a short summary table showing each entry's `resourceType`, `id`/`fullUrl`, and primary code/value.

## Example

**Input (user prompt):**
> *Build a FHIR bundle for an annual physical: 65-year-old male, established patient, hypertension and type-2 diabetes, lab order for HbA1c, vitals captured today (BP 142/91, HR 78, BMI 28.4).*

**Output (abbreviated):**
```json
{
  "resourceType": "Bundle",
  "type": "collection",
  "entry": [
    {
      "fullUrl": "urn:uuid:patient-1",
      "resource": {
        "resourceType": "Patient",
        "meta": {"profile": ["http://hl7.org/fhir/us/core/StructureDefinition/us-core-patient"]},
        "identifier": [{"system": "http://hospital.example.org/mrn", "value": "MRN-SYN-0001"}],
        "name": [{"family": "Synthea", "given": ["John"]}],
        "gender": "male",
        "birthDate": "1960"
      }
    },
    {
      "fullUrl": "urn:uuid:encounter-1",
      "resource": {
        "resourceType": "Encounter",
        "status": "finished",
        "class": {"system": "http://terminology.hl7.org/CodeSystem/v3-ActCode", "code": "AMB"},
        "subject": {"reference": "urn:uuid:patient-1"},
        "period": {"start": "2026-05-24"}
      }
    },
    {
      "fullUrl": "urn:uuid:condition-htn",
      "resource": {
        "resourceType": "Condition",
        "meta": {"profile": ["http://hl7.org/fhir/us/core/StructureDefinition/us-core-condition-encounter-diagnosis"]},
        "clinicalStatus": {"coding": [{"system": "http://terminology.hl7.org/CodeSystem/condition-clinical", "code": "active"}]},
        "code": {"coding": [{"system": "http://hl7.org/fhir/sid/icd-10-cm", "code": "I10", "display": "Essential (primary) hypertension"}]},
        "subject": {"reference": "urn:uuid:patient-1"},
        "encounter": {"reference": "urn:uuid:encounter-1"}
      }
    },
    {
      "fullUrl": "urn:uuid:obs-bp",
      "resource": {
        "resourceType": "Observation",
        "meta": {"profile": ["http://hl7.org/fhir/us/core/StructureDefinition/us-core-blood-pressure"]},
        "status": "final",
        "category": [{"coding": [{"system": "http://terminology.hl7.org/CodeSystem/observation-category", "code": "vital-signs"}]}],
        "code": {"coding": [{"system": "http://loinc.org", "code": "85354-9", "display": "Blood pressure panel"}]},
        "subject": {"reference": "urn:uuid:patient-1"},
        "effectiveDateTime": "2026-05-24",
        "component": [
          {"code": {"coding": [{"system": "http://loinc.org", "code": "8480-6"}]}, "valueQuantity": {"value": 142, "unit": "mmHg"}},
          {"code": {"coding": [{"system": "http://loinc.org", "code": "8462-4"}]}, "valueQuantity": {"value": 91, "unit": "mmHg"}}
        ]
      }
    }
  ]
}
```

Full versions in [`examples/encounter-bundle.json`](./examples/encounter-bundle.json) and [`examples/observation-bundle.json`](./examples/observation-bundle.json).

## Edge cases

- **Don't invent codes.** If you don't know the LOINC/SNOMED/ICD code for something, pick the most specific code you *do* know, mark it `display`-only, and tell the user to verify. Never silently emit a made-up code.
- **`birthDate` granularity.** US Core allows year-only (`"1960"`) — prefer that for fixtures (Safe Harbor §164.514(b)(2)(i)(C)).
- **`status` is required on most resources.** Observation needs `status`, Encounter needs `status`, Condition needs `clinicalStatus`. Missing status is the #1 reason a bundle is rejected by an EHR.
- **Empty `name.family` or `name.given`.** US Core allows missing `given` if `family` is present (and vice versa) but at least one name component is required.
- **References that don't resolve.** Every `reference` inside the bundle must match the `fullUrl` of another entry. Run a cross-check before emitting.
- **`request` block for transactions only.** A `collection` bundle with `request` blocks is technically invalid and some servers reject it; a `transaction` bundle without them won't be processed.
- **Vital-signs profile is special.** US Core blood-pressure requires `component` with systolic + diastolic LOINC codes, not a single value.
- **`MedicationRequest.medication[x]` polymorphism.** Use `medicationCodeableConcept` for ordering by code (RxNorm), `medicationReference` to a contained `Medication` for compound drugs.

## References

- [FHIR R4 Specification (4.0.1)](https://hl7.org/fhir/R4/)
- [US Core Implementation Guide 6.1.0](http://hl7.org/fhir/us/core/STU6.1/)
- [FHIR R4 cheatsheet](./references/fhir-r4-cheatsheet.md) — common resources at a glance
- [US Core profiles](./references/us-core-profiles.md) — which profile URLs to set on `meta.profile`
- HL7 IG Publisher / validator: <https://www.hl7.org/fhir/validation.html>
- Public terminology server (no auth): `https://tx.fhir.org/r4`
