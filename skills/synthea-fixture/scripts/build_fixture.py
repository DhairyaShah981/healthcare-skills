#!/usr/bin/env python3
"""
build_fixture.py — generate a single hand-built FHIR R4 Bundle for evals.

For bulk generation, use upstream Synthea. This script is for the 5–20
specialty edge cases you build by hand.

Usage:
    python build_fixture.py \
      --age 65 --sex male \
      --condition hypertension --condition type2-diabetes \
      --medication lisinopril --medication metformin \
      --vital bp=142/91 --vital hr=78 --vital bmi=28.4 \
      --observation hba1c=7.2% \
      --out evals/golden/handbuilt/h001.json

Outputs a US Core 6.1.0 conformant collection Bundle.
"""
from __future__ import annotations

import argparse
import datetime
import json
import sys
import uuid

CONDITIONS = {
    "hypertension":    ("I10", "59621000", "Essential hypertension"),
    "type2-diabetes":  ("E11.9", "44054006", "Type 2 diabetes mellitus"),
    "type1-diabetes":  ("E10.9", "46635009", "Type 1 diabetes mellitus"),
    "hyperlipidemia":  ("E78.5", "55822004", "Hyperlipidemia"),
    "obesity":         ("E66.9", "414916001", "Obesity"),
    "asthma":          ("J45.909", "195967001", "Asthma"),
    "copd":            ("J44.9", "13645005", "COPD"),
    "depression":      ("F32.9", "35489007", "Depressive disorder"),
    "anxiety":         ("F41.1", "21897009", "Generalized anxiety disorder"),
    "chf":             ("I50.9", "84114007", "Heart failure"),
    "afib":            ("I48.91", "49436004", "Atrial fibrillation"),
}

MEDICATIONS = {
    "lisinopril":   ("314076", "lisinopril 10 MG"),
    "metformin":    ("860975", "metformin hydrochloride 500 MG"),
    "atorvastatin": ("207106", "atorvastatin 10 MG"),
    "amlodipine":   ("198211", "amlodipine 5 MG"),
    "losartan":     ("197361", "losartan 50 MG"),
    "levothyroxine":("312961", "levothyroxine 50 MCG"),
    "omeprazole":   ("197316", "omeprazole 20 MG"),
    "aspirin":      ("1191",   "aspirin"),
    "warfarin":     ("11289",  "warfarin"),
}

VITAL_CODES = {
    "bp":  ("85354-9", "Blood pressure panel"),
    "hr":  ("8867-4",  "Heart rate"),
    "bmi": ("39156-5", "BMI"),
    "rr":  ("9279-1",  "Respiratory rate"),
    "temp":("8310-5",  "Body temperature"),
    "spo2":("59408-5", "Oxygen saturation"),
}

LAB_CODES = {
    "hba1c":     ("4548-4", "Hemoglobin A1c", "%"),
    "glucose":   ("2345-7", "Glucose", "mg/dL"),
    "creatinine":("2160-0", "Creatinine", "mg/dL"),
    "ldl":       ("13457-7", "LDL Cholesterol", "mg/dL"),
    "hdl":       ("2085-9", "HDL Cholesterol", "mg/dL"),
    "tsh":       ("3016-3", "TSH", "mIU/L"),
}


def make_patient(age: int, sex: str) -> dict:
    birth_year = datetime.date.today().year - age
    return {
        "resourceType": "Patient",
        "meta": {"profile": ["http://hl7.org/fhir/us/core/StructureDefinition/us-core-patient"]},
        "identifier": [{"system": "http://hospital.example.org/mrn", "value": f"SYN-{uuid.uuid4().hex[:6].upper()}"}],
        "name": [{"family": "Synthea", "given": ["Test"]}],
        "gender": sex,
        "birthDate": str(birth_year),
    }


def make_encounter(patient_ref: str) -> dict:
    return {
        "resourceType": "Encounter",
        "meta": {"profile": ["http://hl7.org/fhir/us/core/StructureDefinition/us-core-encounter"]},
        "status": "finished",
        "class": {"system": "http://terminology.hl7.org/CodeSystem/v3-ActCode", "code": "AMB"},
        "subject": {"reference": patient_ref},
        "period": {"start": datetime.date.today().isoformat()},
    }


def make_condition(name: str, patient_ref: str, encounter_ref: str) -> dict:
    icd, snomed, display = CONDITIONS[name]
    return {
        "resourceType": "Condition",
        "clinicalStatus": {"coding": [{"system": "http://terminology.hl7.org/CodeSystem/condition-clinical", "code": "active"}]},
        "verificationStatus": {"coding": [{"system": "http://terminology.hl7.org/CodeSystem/condition-ver-status", "code": "confirmed"}]},
        "code": {"coding": [
            {"system": "http://hl7.org/fhir/sid/icd-10-cm", "code": icd, "display": display},
            {"system": "http://snomed.info/sct", "code": snomed, "display": display},
        ]},
        "subject": {"reference": patient_ref},
        "encounter": {"reference": encounter_ref},
    }


def make_medication(name: str, patient_ref: str) -> dict:
    code, display = MEDICATIONS[name]
    return {
        "resourceType": "MedicationRequest",
        "status": "active",
        "intent": "order",
        "medicationCodeableConcept": {
            "coding": [{"system": "http://www.nlm.nih.gov/research/umls/rxnorm", "code": code, "display": display}]
        },
        "subject": {"reference": patient_ref},
        "authoredOn": datetime.date.today().isoformat(),
    }


def make_vital(spec: str, patient_ref: str, encounter_ref: str) -> dict:
    key, raw = spec.split("=", 1)
    code, display = VITAL_CODES[key]
    obs = {
        "resourceType": "Observation",
        "status": "final",
        "category": [{"coding": [{"system": "http://terminology.hl7.org/CodeSystem/observation-category", "code": "vital-signs"}]}],
        "code": {"coding": [{"system": "http://loinc.org", "code": code, "display": display}]},
        "subject": {"reference": patient_ref},
        "encounter": {"reference": encounter_ref},
        "effectiveDateTime": datetime.date.today().isoformat(),
    }
    if key == "bp":
        sys_v, dia_v = raw.split("/")
        obs["component"] = [
            {"code": {"coding": [{"system": "http://loinc.org", "code": "8480-6"}]}, "valueQuantity": {"value": float(sys_v), "unit": "mmHg", "system": "http://unitsofmeasure.org", "code": "mm[Hg]"}},
            {"code": {"coding": [{"system": "http://loinc.org", "code": "8462-4"}]}, "valueQuantity": {"value": float(dia_v), "unit": "mmHg", "system": "http://unitsofmeasure.org", "code": "mm[Hg]"}},
        ]
    else:
        unit_map = {"hr": "/min", "bmi": "kg/m2", "rr": "/min", "temp": "Cel", "spo2": "%"}
        obs["valueQuantity"] = {"value": float(raw.rstrip("%")), "unit": unit_map.get(key, ""), "system": "http://unitsofmeasure.org"}
    return obs


def make_lab(spec: str, patient_ref: str, encounter_ref: str) -> dict:
    key, raw = spec.split("=", 1)
    code, display, unit = LAB_CODES[key]
    return {
        "resourceType": "Observation",
        "status": "final",
        "category": [{"coding": [{"system": "http://terminology.hl7.org/CodeSystem/observation-category", "code": "laboratory"}]}],
        "code": {"coding": [{"system": "http://loinc.org", "code": code, "display": display}]},
        "subject": {"reference": patient_ref},
        "encounter": {"reference": encounter_ref},
        "effectiveDateTime": datetime.date.today().isoformat(),
        "valueQuantity": {"value": float(raw.rstrip("%mg/dLmIU/L ")), "unit": unit, "system": "http://unitsofmeasure.org"},
    }


def build_bundle(args) -> dict:
    p_uuid = f"urn:uuid:patient-{uuid.uuid4()}"
    e_uuid = f"urn:uuid:encounter-{uuid.uuid4()}"
    entries: list[dict] = []

    entries.append({"fullUrl": p_uuid, "resource": make_patient(args.age, args.sex)})
    entries.append({"fullUrl": e_uuid, "resource": make_encounter(p_uuid)})

    for c in args.condition:
        entries.append({"fullUrl": f"urn:uuid:cond-{uuid.uuid4()}",
                        "resource": make_condition(c, p_uuid, e_uuid)})
    for m in args.medication:
        entries.append({"fullUrl": f"urn:uuid:med-{uuid.uuid4()}",
                        "resource": make_medication(m, p_uuid)})
    for v in args.vital:
        entries.append({"fullUrl": f"urn:uuid:vital-{uuid.uuid4()}",
                        "resource": make_vital(v, p_uuid, e_uuid)})
    for lab in args.observation:
        entries.append({"fullUrl": f"urn:uuid:lab-{uuid.uuid4()}",
                        "resource": make_lab(lab, p_uuid, e_uuid)})

    return {"resourceType": "Bundle", "type": "collection", "entry": entries}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--age", type=int, required=True)
    ap.add_argument("--sex", choices=["male", "female", "other", "unknown"], required=True)
    ap.add_argument("--condition", action="append", default=[],
                    help=f"Repeatable. Allowed: {sorted(CONDITIONS)}")
    ap.add_argument("--medication", action="append", default=[],
                    help=f"Repeatable. Allowed: {sorted(MEDICATIONS)}")
    ap.add_argument("--vital", action="append", default=[],
                    help="key=value, e.g. bp=142/91, hr=78, bmi=28.4")
    ap.add_argument("--observation", action="append", default=[],
                    help="key=value, e.g. hba1c=7.2%%, glucose=168")
    ap.add_argument("--out", default="-")
    args = ap.parse_args()

    bundle = build_bundle(args)
    text = json.dumps(bundle, indent=2)
    if args.out == "-":
        sys.stdout.write(text)
    else:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
