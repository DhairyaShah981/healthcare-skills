---
name: hl7-transform
description: |
  Parse HL7 v2.x messages (ADT, ORU, SIU, MDM, ORM) and roundtrip them to and
  from FHIR R4 resources. Use when the user asks to "parse an HL7 message",
  "convert HL7 to FHIR", "build an ADT^A01", "interface with a legacy EHR
  feed", or pastes a pipe-delimited message.
when_to_use: |
  Activate when the user:
  - Pastes an HL7 v2 message (pipe-delimited, starts with `MSH|...`)
  - Asks to convert HL7 v2 ↔ FHIR R4
  - Is building an interface to a legacy hospital information system
  - Mentions specific HL7 segments (PID, PV1, OBX, OBR, SCH, AIG)
  - References HL7 v2.5.1, MLLP, or "the feed from the hospital"
allowed-tools: [Read, Write, Edit, Bash]
license: MIT
tags: [hl7, fhir, healthcare, interop]
incident: |
  HL7 v2 is the dominant integration format inside hospitals and won't be
  replaced for decades. Engineers writing greenfield FHIR services routinely
  have to ingest an HL7 v2 feed (Cerner, Epic interfaces, legacy lab gateways)
  and convert. Without a canonical handler, every team writes its own brittle
  pipe-splitter and gets the field encoding subtly wrong (sub-component
  separators, escape sequences, repeating fields, MSH-specific quirks).
---

# hl7-transform

> HL7 v2 ↔ FHIR R4 conversion. ADT, ORU, SIU first; extensible to ORM, MDM, BAR.

## When to use

- The user pastes an HL7 v2 message (lines starting with `MSH|`, `PID|`, `OBX|`, etc.).
- The user is integrating with a legacy hospital interface engine (Cloverleaf, Rhapsody, Mirth) and needs to translate to / from FHIR.
- The user asks for a specific segment shape ("what does a PV1 look like?", "how do I build an OBX?").
- The user mentions MLLP framing or "the lab feed".

## How it works

1. **Detect the message type.** Read `MSH-9` (the message-type field): `ADT^A01` (admit), `ADT^A03` (discharge), `ADT^A08` (update), `ORU^R01` (observation result), `SIU^S12` (schedule appointment), `ORM^O01` (order), `MDM^T02` (document).

2. **Parse with a real grammar.** Don't hand-split on `|`. Use [`hl7apy`](https://github.com/crs4/hl7apy) (Python) or [`hl7v2`](https://github.com/HumanitarianToolbox/hl7v2) (TS). Pipe-splitting misses sub-components, repetitions, escape sequences (`\F\` = `|`, `\S\` = `^`, `\T\` = `&`, `\R\` = `~`, `\E\` = `\`), and the special MSH escape-character convention.

3. **Map to FHIR via the official maps where they exist.** HL7 publishes [v2-to-FHIR maps](https://hl7.org/fhir/uv/v2mappings/) — use them as the source of truth.

| HL7 v2 | FHIR R4 |
|---|---|
| `ADT^A01` (admit) | `Patient` + `Encounter` (status `in-progress`) + `MessageHeader` |
| `ADT^A03` (discharge) | update `Encounter.status` to `finished` + `Encounter.period.end` |
| `ADT^A08` (update) | upsert `Patient` |
| `ORU^R01` (result) | `DiagnosticReport` + multiple `Observation` |
| `SIU^S12` (sched new) | `Appointment` + `Slot` + linked `Encounter` |
| `ORM^O01` (order) | `ServiceRequest` |
| `MDM^T02` (document) | `DocumentReference` + binary content |

4. **Pay attention to the encoding chars.** `MSH-1` is the field separator (`|`); `MSH-2` declares the rest: `^~\&` = component, repetition, escape, sub-component. Some sites override these. Always parse `MSH-2` before splitting anything.

5. **Build the reverse map.** When converting FHIR → HL7, use `MessageHeader` to determine the message type. Generate timestamps in `YYYYMMDDHHMMSS` (with optional timezone). The control ID (`MSH-10`) must be unique per message; use a ULID or a sequential counter.

6. **Validate after conversion.** Roundtrip an HL7 → FHIR → HL7 transform and diff against the original (allowing for whitespace / control-ID differences). Any structural mismatch is a bug.

7. **Strip PHI before sharing examples.** HL7 messages from real hospitals contain real patient data. Run `phi-redact` over examples before committing to a repo.

## Example

**HL7 v2 ADT^A01 (admit)**
```
MSH|^~\&|HOSPITAL|CARDIO|RECEIVER|ENT|20260524081422||ADT^A01|MSG00001|P|2.5.1
EVN|A01|20260524081422
PID|1||MRN-SYN-0001^^^HOSPITAL^MR||SYNTHEA^JOHN||1960||M
PV1|1|I|ICU^101^A|||||||CARDIO|||||||V|1|||||||||||||||||||||||20260524081422
DG1|1||I10^Essential hypertension^I10|||F
```

**FHIR R4 equivalent (collection Bundle)**
```json
{
  "resourceType": "Bundle",
  "type": "collection",
  "entry": [
    {"fullUrl": "urn:uuid:msg", "resource": {
      "resourceType": "MessageHeader",
      "eventCoding": {"system": "http://terminology.hl7.org/CodeSystem/v2-0003", "code": "A01"},
      "source": {"name": "HOSPITAL", "software": "CARDIO"},
      "destination": [{"name": "RECEIVER"}]
    }},
    {"fullUrl": "urn:uuid:patient-1", "resource": {
      "resourceType": "Patient",
      "identifier": [{"system": "urn:oid:1.2.3.4.5", "value": "MRN-SYN-0001", "type": {"coding": [{"system": "http://terminology.hl7.org/CodeSystem/v2-0203", "code": "MR"}]}}],
      "name": [{"family": "Synthea", "given": ["John"]}],
      "gender": "male",
      "birthDate": "1960"
    }},
    {"fullUrl": "urn:uuid:encounter-1", "resource": {
      "resourceType": "Encounter",
      "status": "in-progress",
      "class": {"system": "http://terminology.hl7.org/CodeSystem/v3-ActCode", "code": "IMP"},
      "subject": {"reference": "urn:uuid:patient-1"},
      "location": [{"location": {"display": "ICU 101 A"}}],
      "period": {"start": "2026-05-24T08:14:22"},
      "diagnosis": [{"condition": {"reference": "urn:uuid:cond-htn"}, "use": {"coding": [{"system": "http://terminology.hl7.org/CodeSystem/diagnosis-role", "code": "AD"}]}}]
    }},
    {"fullUrl": "urn:uuid:cond-htn", "resource": {
      "resourceType": "Condition",
      "code": {"coding": [{"system": "http://hl7.org/fhir/sid/icd-10-cm", "code": "I10", "display": "Essential hypertension"}]},
      "subject": {"reference": "urn:uuid:patient-1"},
      "encounter": {"reference": "urn:uuid:encounter-1"}
    }}
  ]
}
```

Working examples in [`examples/ADT-A01.hl7`](./examples/ADT-A01.hl7) and [`examples/ADT-A01.fhir.json`](./examples/ADT-A01.fhir.json), plus an `ORU^R01` lab result roundtrip in `examples/ORU-R01.hl7`.

## Edge cases

- **MSH-2 isn't always `^~\&`.** Some sites use `^~\&#`. Read it first, don't assume.
- **Empty fields vs absent fields.** `PID|1||MRN||SMITH||1960||M` has empty (`||`) middle name and second-name slots — that's *not* the same as missing fields. Preserve the distinction.
- **Repeating fields use `~`.** `PID-3` (patient identifier list) can hold MRN, SSN, member-id separated by `~`; convert to multiple `Patient.identifier` entries.
- **Sub-components matter.** `PID-5` is `family^given^middle^suffix^prefix`; missing any component shifts the rest. Don't index by position blindly.
- **Date formats vary.** `19600411`, `196004`, `1960`, `1960041112`, `196004110817`, `196004110817-0700` are all valid HL7 v2 dates. Parse with a permissive grammar.
- **Newlines.** HL7 v2 messages use `\r` (CR) between segments — not `\n`. Many pasted examples have been mangled to use `\n`; normalise first.
- **MLLP framing.** Over the wire, HL7 v2 is wrapped in `<VT>...<FS><CR>` (0x0B…0x1C 0x0D). If you're reading from a socket, strip these; if you're writing, add them.
- **Local extensions (Z-segments).** Sites add `ZPM`, `ZIN`, etc., for site-specific data. Don't drop them — keep them as `Basic` resources or extensions.
- **Don't preserve PHI in test fixtures.** Run `phi-redact` over example messages before committing.

## References

- HL7 v2.5.1 spec: <https://www.hl7.org/implement/standards/product_brief.cfm?product_id=144>
- HL7 v2-to-FHIR maps: <https://hl7.org/fhir/uv/v2mappings/>
- `hl7apy` (Python): <https://github.com/crs4/hl7apy>
- Cloverleaf / Rhapsody / Mirth interface engine docs (vendor-specific)
- IHE Patient Administration Profile (mappings for ADT)
- MLLP RFC: HL7 Minimal Lower Layer Protocol
- [`references/hl7v2-segments.md`](./references/hl7v2-segments.md) — segment cheatsheet
