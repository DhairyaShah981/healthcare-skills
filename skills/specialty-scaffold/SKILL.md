---
name: specialty-scaffold
description: |
  Scaffold a new clinical specialty (ENT, cardiology, GI, derm, ortho, peds,
  women's health, etc.) on top of a shared base: intake forms, triage rubric,
  scope-boundary prompts, common ICD/SNOMED codes, common labs, common
  medications, common red flags. Use when the user adds a new specialty to a
  multi-specialty app, asks "what does triage look like for cardiology?",
  or duplicates 80% of an existing specialty config to add a new one.
when_to_use: |
  Activate when the user:
  - Adds a new clinical specialty to a healthcare AI / workflow product
  - Asks to "onboard cardiology / GI / derm / peds"
  - Has multiple specialty templates that are 80% identical and wants to
    consolidate
  - Asks for "common conditions / labs / red flags for specialty X"
  - References scope boundaries, triage rules, or specialty-specific intake
allowed-tools: [Read, Write, Edit, Bash]
license: MIT
tags: [healthcare, scaffold, specialty, triage]
incident: |
  Each specialty template (ENT, cardiology, internal medicine, GI, derm)
  was created by copy-pasting the previous one and editing 20% of the
  content. The shared 80% drifted across specialties: ENT had a refined
  red-flag prompt, cardiology had a better refusal pattern, but neither
  propagated. This skill scaffolds a *base* template + a specialty *override*
  file, so the shared logic stays shared and the specialty-specific parts
  are the only thing the user maintains.
---

# specialty-scaffold

> Base + overrides. The 80% stays shared; the 20% is the specialty.

## When to use

- The user is adding a new specialty to a multi-specialty healthcare product.
- The user has 3+ specialty templates that look 80% identical.
- The user asks "what are the common conditions / labs / red flags for X?".
- A specialty needs to be onboarded with intake, triage, and scope-boundary text.

## How it works

1. **Pick the specialty.** Supported library (extensible):
   - `internal-medicine`
   - `ent`
   - `cardiology`
   - `gi`
   - `dermatology`
   - `orthopedics`
   - `pediatrics`
   - `womens-health`
   - `psychiatry`
   - `endocrinology`

2. **Lay out the directory.**
   ```
   specialties/
   ├── _base/
   │   ├── intake.yaml          # shared intake schema
   │   ├── triage.yaml          # shared urgency rubric
   │   ├── scope.md             # shared "we can / cannot help with…" copy
   │   └── prompts/
   │       ├── system.md        # base system prompt
   │       └── refusal.md       # base refusal patterns
   ├── ent/
   │   ├── overrides.yaml       # specialty-specific fields ONLY
   │   ├── conditions.yaml      # common ICD/SNOMED for this specialty
   │   ├── red_flags.yaml       # specialty-specific red flags
   │   └── prompts/
   │       └── system_overlay.md  # appended to base system.md
   ├── cardiology/
   │   ├── overrides.yaml
   │   ├── conditions.yaml
   │   ├── red_flags.yaml
   │   └── prompts/
   │       └── system_overlay.md
   └── ...
   ```

3. **Merge at runtime, not at scaffold time.** A small `specialty_loader.py` reads `_base/*` then layers `<specialty>/overrides.yaml` and `<specialty>/prompts/system_overlay.md` over it. Don't bake the merged result into the specialty's directory — that's how 80%-identical files happen.

4. **Specialty content checklist** for each new specialty:
   - **Conditions** — top ~20 ICD-10 + SNOMED codes (compose with `icd-snomed-map`)
   - **Labs / procedures** — top ~15 LOINC + CPT codes
   - **Medications** — top ~15 RxNorm codes
   - **Red flags** — symptom patterns that require emergent / urgent triage
   - **Scope boundary** — what the agent should / shouldn't try to help with
   - **Refusal patterns** — specialty-specific refusal copy (cardiology refusals for chest pain differ from derm refusals for moles)

5. **Run the eval immediately.** After scaffolding, run `clinical-eval` against synthetic fixtures for that specialty (compose with `synthea-fixture`). Don't ship a new specialty without an eval baseline.

## Example

**Input:**
> *Scaffold cardiology.*

**Output (file list):**
```
specialties/cardiology/
├── overrides.yaml
├── conditions.yaml
├── red_flags.yaml
└── prompts/
    └── system_overlay.md
```

`specialties/cardiology/overrides.yaml`:
```yaml
specialty: cardiology
display_name: Cardiology
visit_duration_minutes: {new: 60, follow_up: 30, telehealth: 20}
intake_extra_fields:
  - {id: chest_pain_history, type: text}
  - {id: family_cardiac_history, type: enum, options: [MI, sudden_death, none, unknown]}
  - {id: exertional_symptoms, type: bool}
schedulable_provider_types: [cardiologist, electrophysiologist, advanced-practice-provider]
```

`specialties/cardiology/red_flags.yaml`:
```yaml
emergent:
  - {symptom: chest_pain, modifiers: [radiating_arm_or_jaw, exertional, with_diaphoresis]}
  - {symptom: syncope, modifiers: [during_exertion]}
  - {symptom: palpitations, modifiers: [with_syncope, with_chest_pain]}
  - {symptom: dyspnea, modifiers: [sudden_onset, with_chest_pain]}
urgent:
  - {symptom: ankle_swelling, modifiers: [bilateral, acute, with_dyspnea]}
  - {symptom: palpitations, modifiers: [sustained, regular]}
  - {symptom: dyspnea, modifiers: [progressive, exertional]}
```

`specialties/cardiology/conditions.yaml`:
```yaml
top_conditions:
  - {icd10: I10, snomed: 59621000, display: "Essential hypertension"}
  - {icd10: I25.10, snomed: 414545008, display: "Coronary artery disease"}
  - {icd10: I48.91, snomed: 49436004, display: "Atrial fibrillation"}
  - {icd10: I50.9, snomed: 84114007, display: "Heart failure"}
  - {icd10: I63.9, snomed: 230690007, display: "Cerebrovascular accident"}
  - {icd10: I35.0, snomed: 60573004, display: "Aortic valve stenosis"}
common_labs:
  - {loinc: 2160-0, display: "Creatinine"}
  - {loinc: 32623-1, display: "BNP"}
  - {loinc: 33762-6, display: "NT-proBNP"}
  - {loinc: 13457-7, display: "LDL cholesterol"}
  - {loinc: 2085-9, display: "HDL cholesterol"}
common_meds:
  - {rxnorm: 314076, display: "lisinopril 10 MG"}
  - {rxnorm: 198211, display: "amlodipine 5 MG"}
  - {rxnorm: 6918,   display: "metoprolol tartrate 50 MG"}
  - {rxnorm: 11289,  display: "warfarin"}
  - {rxnorm: 207106, display: "atorvastatin 10 MG"}
```

`specialties/cardiology/prompts/system_overlay.md`:
```
You are scheduling for a CARDIOLOGY practice.

When a caller reports chest pain, evaluate the EMERGENT red flags first
(see red_flags.yaml). If any modifier is present (radiating, exertional,
diaphoresis, sudden onset), do NOT schedule — direct the caller to 911 or
the nearest ED and provide the clinic's after-hours line.

Scope boundary: you can schedule consults, follow-ups, procedure pre-ops,
device interrogation, and lipid clinic. You CANNOT triage acute coronary
syndromes, advise on medication dosing, interpret labs/imaging, or
substitute for a clinician's judgement. Default to "I'll connect you with
the on-call cardiologist" for anything outside scheduling.

Common medications you may hear about (no clinical advice): lisinopril,
amlodipine, metoprolol, warfarin, atorvastatin.
```

## Edge cases

- **Pediatrics changes everything.** Doses, conditions, vitals all scale with age. The peds overlay should add age-band logic at every relevant prompt.
- **Women's health crosses specialties.** OB-GYN scheduling logic differs by trimester for pregnant patients. Build a separate overlay for pregnancy state.
- **Behavioral health red flags** include suicidal ideation and self-harm — these are immediate-escalation paths regardless of specialty. The base should handle these; specialty overlays should never override them.
- **Multi-specialty practices.** A patient may be seen for two specialties at the same encounter; route on the *visit type*, not the practice.
- **Don't fork the base.** A specialty needing "almost-base-but-different" should upstream the change into base with a conditional, not fork.
- **Eval before ship.** Always pair a new specialty with a fixture set (`synthea-fixture`) and an eval suite (`clinical-eval`). Don't ship blind.

## References

- ICD-10-CM / SNOMED / LOINC / RxNorm cross-references — `icd-snomed-map`
- USPSTF screening recommendations: <https://www.uspreventiveservicestaskforce.org/>
- Specialty-specific guidelines: AHA (cardiology), AAD (derm), AAO-HNS (ENT), AAP (peds)
- [`scripts/scaffold_specialty.py`](./scripts/scaffold_specialty.py) — generates the directory tree
- [`examples/cardiology/`](./examples/cardiology/) — full cardiology overlay
- Compose with: `synthea-fixture`, `clinical-eval`, `icd-snomed-map`, `cds-hook`
