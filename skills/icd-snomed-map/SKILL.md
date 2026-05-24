---
name: icd-snomed-map
description: |
  Map between ICD-10-CM, SNOMED-CT, CPT, LOINC, and RxNorm. Look up a single
  code, suggest the most likely match, or build a crosswalk table. Works
  offline against an embedded table; falls back to the public `tx.fhir.org`
  terminology server; full SNOMED coverage requires a UMLS key. Use when the
  user asks to "map ICD to SNOMED", "find the LOINC for X", "what's the
  RxNorm code for Y", or pastes a code and asks for its meaning / equivalents.
when_to_use: |
  Activate when the user:
  - Asks to map between two clinical code systems
  - Wants the canonical code for a clinical concept (LOINC for HbA1c, etc.)
  - Pastes a code (e.g. "I10", "44054006") and asks for meaning
  - Is wiring up ConceptMap resources or building a crosswalk
  - Asks about value-sets, code systems, or UCUM units
allowed-tools: [Read, Write, Edit, Bash]
license: MIT
tags: [terminology, fhir, healthcare, icd, snomed, loinc, rxnorm]
incident: |
  Engineers without a terminology background hand-write code mappings
  inconsistently across services — one service uses `I10` for hypertension,
  another uses `38341003` (SNOMED), a third stores both, none use the same
  display string. This skill provides a single offline-first lookup with
  graceful fallback to public terminology services so the team uses one
  canonical mapping everywhere.
---

# icd-snomed-map

> One skill, five code systems. Offline-first; public-tx fallback; full SNOMED via UMLS.

## When to use

- The user wants to map a clinical concept between two coding systems.
- The user pastes a code and asks for the meaning or the equivalent in another system.
- The user is building a `ConceptMap` resource, value-set, or crosswalk table.
- The user is wiring up a FHIR resource and needs to pick the right `system` + `code` (see also `fhir-bundle`).

## How it works

1. **Identify the source code system.** Most common in the wild:
   - **ICD-10-CM** — billing diagnoses (US); strings like `I10`, `E11.9`, `J45.30`. System URI: `http://hl7.org/fhir/sid/icd-10-cm`.
   - **SNOMED CT** — clinical-concept ontology; numeric SCTID. System URI: `http://snomed.info/sct`.
   - **LOINC** — lab and clinical observations; codes like `4548-4`. System URI: `http://loinc.org`.
   - **RxNorm** — medications; codes like `314076`. System URI: `http://www.nlm.nih.gov/research/umls/rxnorm`.
   - **CPT** — procedures (US); 5-digit codes. System URI: `http://www.ama-assn.org/go/cpt`.

2. **Try the offline table first.** A ~500-row embedded table (`references/code-systems.md`) covers the most common concepts: HbA1c, BP, BMI, lisinopril, metformin, COVID-19, diabetes, hypertension, CHF, asthma, common procedures, etc. This is what most "give me a code for X" requests need.

3. **Fall back to `tx.fhir.org`.** If the offline table misses, query the public terminology server:
   ```
   GET https://tx.fhir.org/r4/CodeSystem/$lookup?system=http://loinc.org&code=4548-4
   ```
   Returns the display + properties. No API key required.

4. **Escalate to UMLS for full SNOMED.** SNOMED CT has ~350,000 concepts; only a few hundred are in the offline table. For exhaustive SNOMED lookup or cross-mapping, query the UMLS REST API (requires `UMLS_API_KEY` — free at <https://uts.nlm.nih.gov>):
   ```
   GET https://uts-ws.nlm.nih.gov/rest/content/current/source/SNOMEDCT_US/{cui}/atoms?apiKey={UMLS_API_KEY}
   ```

5. **Gracefully degrade.** When offline + no key: return the offline-table answer and a clear note "Confirm against a SNOMED browser if mapping must be exhaustive — full SNOMED is gated by UMLS license."

6. **Output a FHIR Coding shape.** When asked for a code, always return:
   ```json
   {"system": "http://loinc.org", "code": "4548-4", "display": "Hemoglobin A1c/Hemoglobin.total in Blood"}
   ```
   This shape is what every FHIR resource expects.

7. **For crosswalks, return a ConceptMap fragment.** When the user asks "map this set of ICD-10 codes to SNOMED", emit a [FHIR ConceptMap](https://www.hl7.org/fhir/R4/conceptmap.html) with `equivalence` values: `equal`, `equivalent`, `wider`, `narrower`, `inexact`, `unmatched`.

## Example

**Input:**
> *What's the code for hypertension?*

**Output:**
```
"essential hypertension" appears in multiple systems:

| System    | Code      | Display |
|-----------|-----------|---------|
| ICD-10-CM | I10       | Essential (primary) hypertension |
| SNOMED CT | 59621000  | Essential hypertension (disorder) |
| ICD-9-CM  | 401.9     | Unspecified essential hypertension |

In FHIR R4, prefer ICD-10-CM for billing diagnoses, SNOMED for clinical concept.
```

**Input:**
> *Map ICD-10 I10 to SNOMED.*

**Output:**
```json
{
  "icd10": {"system": "http://hl7.org/fhir/sid/icd-10-cm", "code": "I10", "display": "Essential (primary) hypertension"},
  "snomed": {"system": "http://snomed.info/sct", "code": "59621000", "display": "Essential hypertension (disorder)"},
  "equivalence": "equivalent",
  "source": "offline table (canonical pairing)"
}
```

**Input:**
> *I have a panel of LOINC codes: 4548-4, 2345-7, 13457-7, 2160-0. What are they?*

**Output:**
```
| LOINC    | Display                                             |
|----------|-----------------------------------------------------|
| 4548-4   | Hemoglobin A1c/Hemoglobin.total in Blood            |
| 2345-7   | Glucose [Mass/volume] in Serum or Plasma            |
| 13457-7  | LDL Cholesterol                                     |
| 2160-0   | Creatinine [Mass/volume] in Serum or Plasma         |
```

## Edge cases

- **ICD-10-CM vs ICD-10.** US uses CM (`http://hl7.org/fhir/sid/icd-10-cm`); international uses base (`http://hl7.org/fhir/sid/icd-10`). They overlap but aren't identical. Default to ICD-10-CM in US contexts.
- **SNOMED CT licensing varies by country.** US users have access via the NLM (free). UK, Canada, Australia have national licenses. Other jurisdictions require a per-affiliate license. Don't redistribute full SNOMED in a public repo.
- **CPT is owned by the AMA.** Codes are well-known; full CPT requires a license. The skill ships only the most common 30–50 codes; deeper use requires a license.
- **NDC vs RxNorm.** NDC is a manufacturer-specific package code (11 digits); RxNorm is the clinical-drug concept (a code per dose+form+ingredient). Use RxNorm for clinical decisions, NDC for billing / supply.
- **LOINC scale.** A LOINC code includes scale (`Qn` quantitative, `Ord` ordinal, `Nom` nominal). Don't pick a LOINC by name alone — confirm the scale matches the result type.
- **Display strings drift.** SNOMED's official display can change between versions. Always carry the `version` if the use case demands stability (research, billing).
- **"Inexact" mappings need review.** When the offline table returns `equivalence: inexact`, the result is "best available" — flag it to the user so they don't silently propagate a wrong mapping.

## References

- [HL7 FHIR R4 — Using codes in resources](https://www.hl7.org/fhir/R4/terminologies.html)
- [FHIR R4 ConceptMap](https://www.hl7.org/fhir/R4/conceptmap.html)
- ICD-10-CM browser: <https://www.icd10data.com/>
- SNOMED CT browser: <https://browser.ihtsdotools.org/>
- LOINC search: <https://loinc.org/search/>
- RxNav (RxNorm browser): <https://mor.nlm.nih.gov/RxNav/>
- UMLS REST API: <https://documentation.uts.nlm.nih.gov/rest/home.html>
- Public terminology server (no key): <https://tx.fhir.org/r4>
- [`references/code-systems.md`](./references/code-systems.md) — offline code table
- [`scripts/code_lookup.py`](./scripts/code_lookup.py) — offline + tx.fhir.org client
