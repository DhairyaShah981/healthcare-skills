# US Core 6.1.0 profile URLs

The `meta.profile` field signals to receivers which Implementation Guide the resource claims to conform to. Set it explicitly — receivers may apply stricter validation when it's present.

Base URL prefix: `http://hl7.org/fhir/us/core/StructureDefinition/`

| Resource | Profile |
|---|---|
| Patient | `us-core-patient` |
| Practitioner | `us-core-practitioner` |
| PractitionerRole | `us-core-practitionerrole` |
| Organization | `us-core-organization` |
| Location | `us-core-location` |
| Encounter | `us-core-encounter` |
| Condition (problem) | `us-core-condition-problems-health-concerns` |
| Condition (dx) | `us-core-condition-encounter-diagnosis` |
| AllergyIntolerance | `us-core-allergyintolerance` |
| MedicationRequest | `us-core-medicationrequest` |
| Medication | `us-core-medication` |
| Immunization | `us-core-immunization` |
| Procedure | `us-core-procedure` |
| DiagnosticReport (lab) | `us-core-diagnosticreport-lab` |
| DiagnosticReport (note) | `us-core-diagnosticreport-note` |
| DocumentReference | `us-core-documentreference` |
| Observation (lab) | `us-core-observation-lab` |
| Observation (smoking status) | `us-core-smokingstatus` |
| Observation (vital signs) | `us-core-vital-signs` |
| Observation (blood pressure) | `us-core-blood-pressure` |
| Observation (heart rate) | `us-core-heart-rate` |
| Observation (body weight) | `us-core-body-weight` |
| Observation (body height) | `us-core-body-height` |
| Observation (BMI) | `us-core-bmi` |
| Observation (respiratory rate) | `us-core-respiratory-rate` |
| Observation (body temperature) | `us-core-body-temperature` |
| Observation (pulse oximetry) | `us-core-pulse-oximetry` |
| Observation (head circumference) | `us-core-head-circumference` |
| Observation (clinical result) | `us-core-observation-clinical-result` |
| Observation (sexual orientation) | `us-core-observation-sexual-orientation` |
| Observation (occupation) | `us-core-observation-occupation` |
| Observation (pregnancy status) | `us-core-observation-pregnancystatus` |
| Observation (pregnancy intent) | `us-core-observation-pregnancyintent` |
| ServiceRequest | `us-core-servicerequest` |
| Goal | `us-core-goal` |
| CareTeam | `us-core-careteam` |
| CarePlan | `us-core-careplan` |
| Provenance | `us-core-provenance` |
| RelatedPerson | `us-core-relatedperson` |
| QuestionnaireResponse | `us-core-questionnaireresponse` |
| Coverage | `us-core-coverage` |

## Must-Support vs Required

US Core distinguishes:
- **Required** — must be present (per FHIR R4 base or US Core profile)
- **Must-Support** — receivers MUST be able to handle it if sent; senders SHOULD send when known

Engineers often confuse these — Must-Support is a server-capability statement, not a "you must always send this." Senders should populate Must-Support fields whenever data is available, and omit them when not.

## Patient-must-support shortlist

- `identifier` (with `system` + `value`)
- `name` (`family` or `given`)
- `gender`
- `birthDate`
- `address` (state at minimum)
- `telecom` (phone or email)
- `communication.language` (preferred language, BCP-47)
- `extension`: race (`us-core-race`), ethnicity (`us-core-ethnicity`), birth sex (`us-core-birthsex`)
