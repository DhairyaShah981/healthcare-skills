# HL7 v2 segment cheatsheet

Segments most commonly encountered in ADT / ORU / SIU / ORM message types. Field numbering is 1-based (HL7 convention). All fields shown are HL7 v2.5.1.

## MSH — Message Header

| Field | Name | Notes |
|---|---|---|
| MSH-1 | Field separator | Always `|`; defined by position |
| MSH-2 | Encoding characters | Usually `^~\&` |
| MSH-3 | Sending application | `HOSPITAL` |
| MSH-4 | Sending facility | `CARDIO` |
| MSH-5 | Receiving application | |
| MSH-6 | Receiving facility | |
| MSH-7 | Date/time of message | YYYYMMDDHHMMSS |
| MSH-9 | Message type | `ADT^A01` |
| MSH-10 | Message control ID | Unique per sender |
| MSH-11 | Processing ID | `P` prod, `T` test, `D` debug |
| MSH-12 | Version ID | `2.5.1` |

## PID — Patient Identification

| Field | Name | Notes |
|---|---|---|
| PID-3 | Patient identifier list | Repeats with `~`; each `ID^^^assigning-authority^id-type` |
| PID-5 | Patient name | `family^given^middle^suffix^prefix^degree` |
| PID-6 | Mother's maiden name | |
| PID-7 | Date of birth | YYYYMMDD |
| PID-8 | Sex | M / F / O / U |
| PID-10 | Race | Coded |
| PID-11 | Address | Repeats with `~` |
| PID-13 | Home phone | |
| PID-14 | Business phone | |
| PID-22 | Ethnic group | |

## PV1 — Patient Visit

| Field | Name | Notes |
|---|---|---|
| PV1-2 | Patient class | I inpatient, O outpatient, E emergency, P preadmit |
| PV1-3 | Assigned location | `point-of-care^room^bed^facility` |
| PV1-7 | Attending doctor | XCN data type |
| PV1-9 | Consulting doctor | |
| PV1-10 | Hospital service | |
| PV1-19 | Visit number | |
| PV1-44 | Admit date/time | YYYYMMDDHHMMSS |
| PV1-45 | Discharge date/time | YYYYMMDDHHMMSS |

## OBX — Observation/Result

| Field | Name | Notes |
|---|---|---|
| OBX-2 | Value type | `NM` numeric, `ST` string, `TX` text, `CE` coded |
| OBX-3 | Observation identifier | `code^display^system` (often LOINC) |
| OBX-5 | Observation value | |
| OBX-6 | Units | UCUM preferred |
| OBX-7 | Reference range | `low-high` |
| OBX-8 | Abnormal flags | `H`, `L`, `HH`, `LL`, `N` |
| OBX-11 | Observation result status | `F` final, `P` preliminary, `C` corrected |
| OBX-14 | Date/time of observation | |

## OBR — Observation Request

| Field | Name | Notes |
|---|---|---|
| OBR-2 | Placer order number | |
| OBR-3 | Filler order number | |
| OBR-4 | Universal service ID | The lab test code |
| OBR-7 | Observation date/time | |
| OBR-25 | Result status | |

## DG1 — Diagnosis

| Field | Name | Notes |
|---|---|---|
| DG1-3 | Diagnosis code | `code^display^system` (`I10` or `ICD-10`) |
| DG1-6 | Diagnosis type | `A` admitting, `W` working, `F` final |

## SCH — Scheduling Activity Information

| Field | Name | Notes |
|---|---|---|
| SCH-2 | Filler appointment ID | |
| SCH-7 | Appointment type | |
| SCH-11.4 | Start date/time | |
| SCH-25 | Filler status | `Booked`, `Cancelled`, `NoShow`, `Started`, `Completed` |

## EVN — Event Type

| Field | Name | Notes |
|---|---|---|
| EVN-1 | Event type | `A01`, `A03`, `A08` |
| EVN-2 | Recorded date/time | |
| EVN-6 | Event occurred | |

## Encoding characters

| Char | Purpose | Escape sequence |
|---|---|---|
| `|` | Field separator | `\F\` |
| `^` | Component separator | `\S\` |
| `&` | Sub-component separator | `\T\` |
| `~` | Repetition separator | `\R\` |
| `\` | Escape character | `\E\` |

## Common message types

| Type | Trigger | Meaning |
|---|---|---|
| ADT | A01 | Admit / visit notification |
| ADT | A02 | Transfer a patient |
| ADT | A03 | Discharge / end visit |
| ADT | A04 | Register a patient |
| ADT | A05 | Pre-admit a patient |
| ADT | A08 | Update patient information |
| ADT | A28 | Add person information |
| ADT | A31 | Update person information |
| ORM | O01 | General order |
| ORU | R01 | Unsolicited observation result |
| SIU | S12 | Notification of new appointment |
| SIU | S14 | Notification of appointment modification |
| SIU | S15 | Notification of appointment cancellation |
| MDM | T02 | Original document with content |
| ACK | -- | Acknowledgement |
| BAR | P01 | Add patient accounts |
| DFT | P03 | Post detail financial transaction |

## v2 → FHIR resource summary

| Segment | FHIR resource |
|---|---|
| MSH | MessageHeader |
| EVN | (informational only — sets MessageHeader.event) |
| PID | Patient |
| PD1 | Patient extensions, generalPractitioner |
| PV1 | Encounter |
| PV2 | Encounter (additional fields) |
| OBR | DiagnosticReport, ServiceRequest |
| OBX | Observation (typically multiple per OBR) |
| DG1 | Condition (with Encounter.diagnosis link) |
| AL1 | AllergyIntolerance |
| RXA | Immunization, MedicationAdministration |
| RXE | MedicationRequest |
| ORC | (drives status; not a resource by itself) |
| SCH | Appointment |
| AIG / AIL / AIP / AIS | Appointment participants and slots |
| MSA | OperationOutcome (for ACKs) |
| NTE | Annotation, embedded into prior resource |
