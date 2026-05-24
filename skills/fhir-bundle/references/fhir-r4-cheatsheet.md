# FHIR R4 cheatsheet

Quick reference for the resources most healthcare engineering work touches. For each: minimal required fields and the gotchas.

## Patient
```json
{
  "resourceType": "Patient",
  "identifier": [{"system": "http://hospital.example.org/mrn", "value": "MRN-001"}],
  "name": [{"family": "Synthea", "given": ["John"]}],
  "gender": "male",                          // male | female | other | unknown
  "birthDate": "1960"                        // year-only allowed; prefer for fixtures
}
```
Gotchas: at least one of `name.family` / `name.given` required by US Core. `gender` is biological sex (not gender identity — that's `us-core-genderIdentity` extension).

## Encounter
```json
{
  "resourceType": "Encounter",
  "status": "finished",                      // planned | arrived | triaged | in-progress | onleave | finished | cancelled
  "class": {"system": "http://terminology.hl7.org/CodeSystem/v3-ActCode", "code": "AMB"},
  "subject": {"reference": "Patient/123"},
  "period": {"start": "2026-05-24", "end": "2026-05-24"}
}
```
Gotchas: `class` is a `Coding` (singular), not `CodeableConcept`. Common classes: `AMB` (ambulatory), `EMER` (emergency), `IMP` (inpatient), `HH` (home health), `VR` (virtual).

## Observation (lab)
```json
{
  "resourceType": "Observation",
  "status": "final",                         // registered | preliminary | final | amended | corrected | cancelled | entered-in-error | unknown
  "category": [{"coding": [{"system": "http://terminology.hl7.org/CodeSystem/observation-category", "code": "laboratory"}]}],
  "code": {"coding": [{"system": "http://loinc.org", "code": "4548-4", "display": "Hemoglobin A1c"}]},
  "subject": {"reference": "Patient/123"},
  "effectiveDateTime": "2026-05-24",
  "valueQuantity": {"value": 7.2, "unit": "%", "system": "http://unitsofmeasure.org", "code": "%"}
}
```
Gotchas: `valueQuantity.code` should be a UCUM code, not the display unit.

## Observation (blood pressure)
Uses `component[]` for systolic + diastolic, both with LOINC codes:
```json
{
  "code": {"coding": [{"system": "http://loinc.org", "code": "85354-9"}]},
  "component": [
    {"code": {"coding": [{"system": "http://loinc.org", "code": "8480-6"}]}, "valueQuantity": {"value": 142, "unit": "mmHg"}},
    {"code": {"coding": [{"system": "http://loinc.org", "code": "8462-4"}]}, "valueQuantity": {"value": 91, "unit": "mmHg"}}
  ]
}
```

## Condition
```json
{
  "resourceType": "Condition",
  "clinicalStatus": {"coding": [{"system": "http://terminology.hl7.org/CodeSystem/condition-clinical", "code": "active"}]},
  "verificationStatus": {"coding": [{"system": "http://terminology.hl7.org/CodeSystem/condition-ver-status", "code": "confirmed"}]},
  "code": {"coding": [{"system": "http://hl7.org/fhir/sid/icd-10-cm", "code": "I10", "display": "Essential hypertension"}]},
  "subject": {"reference": "Patient/123"}
}
```
Gotchas: `clinicalStatus` ≠ `verificationStatus`. Don't confuse "active" (the condition is currently present) with "confirmed" (a clinician has verified it).

## MedicationRequest
```json
{
  "resourceType": "MedicationRequest",
  "status": "active",
  "intent": "order",
  "medicationCodeableConcept": {
    "coding": [{"system": "http://www.nlm.nih.gov/research/umls/rxnorm", "code": "314076", "display": "lisinopril 10 MG"}]
  },
  "subject": {"reference": "Patient/123"},
  "authoredOn": "2026-05-24",
  "dosageInstruction": [{"text": "1 tablet by mouth daily"}]
}
```

## AllergyIntolerance
```json
{
  "resourceType": "AllergyIntolerance",
  "clinicalStatus": {"coding": [{"system": "http://terminology.hl7.org/CodeSystem/allergyintolerance-clinical", "code": "active"}]},
  "verificationStatus": {"coding": [{"system": "http://terminology.hl7.org/CodeSystem/allergyintolerance-verification", "code": "confirmed"}]},
  "code": {"coding": [{"system": "http://www.nlm.nih.gov/research/umls/rxnorm", "code": "7980", "display": "Penicillin"}]},
  "patient": {"reference": "Patient/123"}
}
```
Gotchas: this resource uses `patient`, not `subject`. Many builders get this wrong.

## Bundle
```json
{
  "resourceType": "Bundle",
  "type": "collection",                      // document | message | transaction | batch | history | searchset | collection
  "entry": [
    {"fullUrl": "urn:uuid:p1", "resource": {...}},
    {"fullUrl": "urn:uuid:e1", "resource": {...}}
  ]
}
```
For `transaction`/`batch`, every `entry` needs a `request` block:
```json
{"request": {"method": "POST", "url": "Patient"}}
```

## Common coded-value systems

| Domain | System URL |
|---|---|
| SNOMED CT | `http://snomed.info/sct` |
| LOINC | `http://loinc.org` |
| ICD-10-CM | `http://hl7.org/fhir/sid/icd-10-cm` |
| ICD-10 (intl) | `http://hl7.org/fhir/sid/icd-10` |
| RxNorm | `http://www.nlm.nih.gov/research/umls/rxnorm` |
| CPT | `http://www.ama-assn.org/go/cpt` |
| NDC | `http://hl7.org/fhir/sid/ndc` |
| HCPCS | `https://www.cms.gov/Medicare/Coding/HCPCSReleaseCodeSets` |
| UCUM | `http://unitsofmeasure.org` |
| Encounter class | `http://terminology.hl7.org/CodeSystem/v3-ActCode` |
| Observation category | `http://terminology.hl7.org/CodeSystem/observation-category` |
| Condition clinical | `http://terminology.hl7.org/CodeSystem/condition-clinical` |
| Condition verification | `http://terminology.hl7.org/CodeSystem/condition-ver-status` |
