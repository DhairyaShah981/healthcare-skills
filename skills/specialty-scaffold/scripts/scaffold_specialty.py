#!/usr/bin/env python3
"""
scaffold_specialty.py — generate a specialty directory from a starter template.

Usage:
    python scaffold_specialty.py cardiology
    python scaffold_specialty.py ent --out specialties/
    python scaffold_specialty.py psychiatry --display "Behavioral Health"

Creates:
    specialties/<name>/
      overrides.yaml      — visit durations, intake extra fields, provider types
      conditions.yaml     — top conditions / labs / medications (skeleton)
      red_flags.yaml      — emergent / urgent triage flags (skeleton)
      prompts/
        system_overlay.md — appended to base system prompt

After scaffolding, fill in the YAML files using `icd-snomed-map`, pair with
`synthea-fixture` for eval fixtures, and run `clinical-eval` before shipping.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Starter library — top conditions per specialty (skeleton; expand in your codebase)
STARTERS: dict[str, dict] = {
    "internal-medicine": {
        "conditions": [("I10", "59621000", "Essential hypertension"),
                       ("E11.9", "44054006", "Type 2 diabetes mellitus"),
                       ("E78.5", "55822004", "Hyperlipidemia"),
                       ("F32.9", "35489007", "Depressive disorder")],
        "scope": "primary care visits, annual physicals, chronic disease management",
    },
    "cardiology": {
        "conditions": [("I10", "59621000", "Essential hypertension"),
                       ("I25.10", "414545008", "Coronary artery disease"),
                       ("I48.91", "49436004", "Atrial fibrillation"),
                       ("I50.9", "84114007", "Heart failure")],
        "scope": "consults, follow-ups, procedure pre-ops, device interrogation, lipid clinic",
    },
    "ent": {
        "conditions": [("J34.2", "73892008", "Deviated nasal septum"),
                       ("H66.90", "65363002", "Otitis media"),
                       ("J32.9", "36971009", "Chronic sinusitis"),
                       ("H93.13", "60862001", "Tinnitus")],
        "scope": "ENT consults, post-op follow-up, hearing eval scheduling",
    },
    "gi": {
        "conditions": [("K21.9", "235595009", "GERD"),
                       ("K57.30", "235759005", "Diverticulosis"),
                       ("K58.9", "10743008", "Irritable bowel syndrome"),
                       ("K50.90", "34000006", "Crohn disease")],
        "scope": "GI consults, colonoscopy scheduling, endoscopy follow-up",
    },
    "dermatology": {
        "conditions": [("L70.0", "11381005", "Acne vulgaris"),
                       ("L20.9", "24079001", "Atopic dermatitis"),
                       ("L40.9", "9014002", "Psoriasis"),
                       ("D23.9", "126808005", "Benign skin lesion")],
        "scope": "skin checks, lesion biopsies, cosmetic consults, acne follow-up",
    },
    "orthopedics": {
        "conditions": [("M54.50", "279039007", "Low back pain"),
                       ("M25.50", "57676002", "Joint pain"),
                       ("M17.9", "239873007", "Osteoarthritis of knee"),
                       ("S83.5", "23475005", "Sprain of knee")],
        "scope": "orthopedic consults, post-op follow-up, sports injury eval",
    },
    "pediatrics": {
        "conditions": [("Z00.121", "171304002", "Routine child health exam"),
                       ("J20.9", "6142004", "Acute bronchitis"),
                       ("J45.909", "195967001", "Asthma"),
                       ("F90.9", "406506008", "ADHD")],
        "scope": "well-child visits, sick visits, school physicals — AGE-BAND LOGIC REQUIRED",
    },
    "womens-health": {
        "conditions": [("Z01.419", "171149006", "Routine gyn exam"),
                       ("N92.0", "17402008", "Heavy menstrual bleeding"),
                       ("N94.6", "9209005", "Dysmenorrhea"),
                       ("Z34.90", "424525001", "Routine prenatal care")],
        "scope": "annual exams, prenatal scheduling, contraception consults — PREGNANCY STATE MATTERS",
    },
    "psychiatry": {
        "conditions": [("F32.9", "35489007", "Major depressive disorder"),
                       ("F41.1", "21897009", "Generalized anxiety disorder"),
                       ("F33.1", "66344007", "Recurrent depression, moderate"),
                       ("F90.9", "406506008", "ADHD")],
        "scope": "med-management visits, intake — SUICIDAL IDEATION ALWAYS ESCALATES",
    },
    "endocrinology": {
        "conditions": [("E11.9", "44054006", "Type 2 diabetes mellitus"),
                       ("E10.9", "46635009", "Type 1 diabetes mellitus"),
                       ("E03.9", "40930008", "Hypothyroidism"),
                       ("E05.90", "34486009", "Hyperthyroidism")],
        "scope": "endocrine consults, diabetes management, thyroid follow-up",
    },
}


def overrides_yaml(specialty: str, display: str) -> str:
    return f"""specialty: {specialty}
display_name: {display}
visit_duration_minutes:
  new: 60
  follow_up: 30
  telehealth: 20
intake_extra_fields: []      # fill in specialty-specific fields
schedulable_provider_types: []
"""


def conditions_yaml(specialty: str) -> str:
    cs = STARTERS.get(specialty, {}).get("conditions", [])
    lines = ["top_conditions:"]
    for icd, snomed, display in cs:
        lines.append(f'  - {{icd10: "{icd}", snomed: "{snomed}", display: "{display}"}}')
    lines += ["common_labs: []", "common_meds: []"]
    return "\n".join(lines) + "\n"


def red_flags_yaml(specialty: str) -> str:
    return f"""# {specialty} red flags — FILL IN PER SPECIALTY GUIDELINES
emergent: []
urgent: []
"""


def system_overlay_md(specialty: str, display: str) -> str:
    scope = STARTERS.get(specialty, {}).get("scope",
                                            "fill in: what this specialty schedules / handles")
    return f"""You are scheduling for a {display.upper()} practice.

Scope boundary: you can help with {scope}.
You CANNOT triage acute conditions, interpret labs / imaging, advise on
medication dosing, or substitute for a clinician's judgement.

When in doubt, defer to "I'll connect you with the on-call clinician".

Red flags: see ../red_flags.yaml. Any emergent flag → immediate escalation
(911 / nearest ED / on-call line). Do NOT schedule emergent presentations.
"""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("specialty")
    ap.add_argument("--out", default="specialties")
    ap.add_argument("--display", default=None,
                    help="display name; defaults to title-cased specialty")
    args = ap.parse_args()

    root = Path(args.out) / args.specialty
    if root.exists():
        print(f"{root} already exists; refusing to overwrite", file=sys.stderr)
        return 2
    (root / "prompts").mkdir(parents=True)

    display = args.display or args.specialty.replace("-", " ").title()
    (root / "overrides.yaml").write_text(overrides_yaml(args.specialty, display))
    (root / "conditions.yaml").write_text(conditions_yaml(args.specialty))
    (root / "red_flags.yaml").write_text(red_flags_yaml(args.specialty))
    (root / "prompts" / "system_overlay.md").write_text(system_overlay_md(args.specialty, display))

    print(f"scaffolded {root}/")
    print("next steps:")
    print(f"  1. fill in {root}/red_flags.yaml from your specialty's guidelines")
    print(f"  2. expand {root}/conditions.yaml common_labs and common_meds")
    print(f"  3. write fixtures with synthea-fixture")
    print(f"  4. baseline with clinical-eval")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
