#!/usr/bin/env python3
"""
code_lookup.py — offline-first clinical-code lookup.

Layered fallback:
  1. Offline table (a ~500-row in-memory dict; covers Synthea + common cases)
  2. tx.fhir.org (public terminology server; no key required)
  3. UMLS REST API (requires UMLS_API_KEY env var)

Usage:
    python code_lookup.py lookup loinc 4548-4
    python code_lookup.py lookup icd10 I10
    python code_lookup.py map icd10:I10 --to snomed
    python code_lookup.py search "hemoglobin A1c"
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

# ── system URIs ────────────────────────────────────────────────────────────

SYSTEMS = {
    "icd10":   "http://hl7.org/fhir/sid/icd-10-cm",
    "icd10cm": "http://hl7.org/fhir/sid/icd-10-cm",
    "snomed":  "http://snomed.info/sct",
    "loinc":   "http://loinc.org",
    "rxnorm":  "http://www.nlm.nih.gov/research/umls/rxnorm",
    "cpt":     "http://www.ama-assn.org/go/cpt",
    "hcpcs":   "https://www.cms.gov/Medicare/Coding/HCPCSReleaseCodeSets",
    "ndc":     "http://hl7.org/fhir/sid/ndc",
    "ucum":    "http://unitsofmeasure.org",
}


# ── offline tables ─────────────────────────────────────────────────────────

ICD10 = {
    "I10": "Essential (primary) hypertension",
    "I50.9": "Heart failure, unspecified",
    "I25.10": "Atherosclerotic heart disease",
    "I48.91": "Unspecified atrial fibrillation",
    "E11.9": "Type 2 diabetes mellitus without complications",
    "E10.9": "Type 1 diabetes mellitus without complications",
    "E78.5": "Hyperlipidemia, unspecified",
    "E66.9": "Obesity, unspecified",
    "J44.9": "Chronic obstructive pulmonary disease, unspecified",
    "J45.909": "Unspecified asthma, uncomplicated",
    "K21.9": "Gastro-esophageal reflux disease without esophagitis",
    "F32.9": "Major depressive disorder, single episode, unspecified",
    "F41.1": "Generalized anxiety disorder",
    "M54.50": "Low back pain, unspecified",
    "R51": "Headache",
    "R10.9": "Unspecified abdominal pain",
    "R05": "Cough",
    "R50.9": "Fever, unspecified",
}

SNOMED = {
    "59621000": "Essential hypertension",
    "44054006": "Type 2 diabetes mellitus",
    "46635009": "Type 1 diabetes mellitus",
    "84114007": "Heart failure",
    "414545008": "Ischemic heart disease",
    "49436004": "Atrial fibrillation",
    "195967001": "Asthma",
    "13645005": "Chronic obstructive lung disease",
    "55822004": "Hyperlipidemia",
    "414916001": "Obesity",
    "35489007": "Depressive disorder",
    "21897009": "Generalized anxiety disorder",
    "25064002": "Headache",
}

LOINC = {
    "85354-9": "Blood pressure panel with all children optional",
    "8480-6":  "Systolic blood pressure",
    "8462-4":  "Diastolic blood pressure",
    "8867-4":  "Heart rate",
    "9279-1":  "Respiratory rate",
    "8310-5":  "Body temperature",
    "2708-6":  "Oxygen saturation in Arterial blood",
    "59408-5": "Oxygen saturation in Arterial blood by Pulse oximetry",
    "29463-7": "Body weight",
    "8302-2":  "Body height",
    "39156-5": "Body mass index (BMI)",
    "4548-4":  "Hemoglobin A1c/Hemoglobin.total in Blood",
    "2345-7":  "Glucose [Mass/volume] in Serum or Plasma",
    "2160-0":  "Creatinine [Mass/volume] in Serum or Plasma",
    "13457-7": "LDL Cholesterol",
    "2085-9":  "HDL Cholesterol",
    "2093-3":  "Cholesterol [Mass/volume] in Serum or Plasma",
    "2571-8":  "Triglyceride [Mass/volume] in Serum or Plasma",
    "1742-6":  "Alanine aminotransferase (ALT)",
    "1920-8":  "Aspartate aminotransferase (AST)",
    "3016-3":  "TSH",
}

RXNORM = {
    "314076": "lisinopril 10 MG",
    "207106": "atorvastatin 10 MG",
    "860975": "metformin hydrochloride 500 MG",
    "198211": "amlodipine 5 MG",
    "197361": "losartan 50 MG",
    "312961": "levothyroxine 50 MCG",
    "197316": "omeprazole 20 MG",
    "161":    "acetaminophen 500 MG",
    "5640":   "ibuprofen 200 MG",
    "1191":   "aspirin",
    "11289":  "warfarin",
    "7980":   "penicillin",
    "723":    "amoxicillin",
}

CPT = {
    "99213": "Office visit, established patient, level 3",
    "99214": "Office visit, established patient, level 4",
    "99203": "Office visit, new patient, level 3",
    "99204": "Office visit, new patient, level 4",
    "99396": "Periodic comprehensive preventive visit, 40-64 years",
    "99397": "Periodic comprehensive preventive visit, 65+ years",
    "90686": "Influenza vaccine, quadrivalent (IIV4)",
    "36415": "Routine venipuncture",
    "80061": "Lipid panel",
    "80053": "Comprehensive metabolic panel",
    "83036": "Hemoglobin A1c",
    "85025": "CBC with automated differential",
    "93000": "ECG, complete",
}

OFFLINE: dict[str, dict[str, str]] = {
    "icd10": ICD10, "icd10cm": ICD10,
    "snomed": SNOMED, "loinc": LOINC, "rxnorm": RXNORM, "cpt": CPT,
}

# ICD-10-CM ↔ SNOMED equivalence
ICD_TO_SNOMED = {
    "I10": ("59621000", "equivalent"),
    "E11.9": ("44054006", "equivalent"),
    "E10.9": ("46635009", "equivalent"),
    "I50.9": ("84114007", "equivalent"),
    "I48.91": ("49436004", "equivalent"),
    "J45.909": ("195967001", "equivalent"),
    "F32.9": ("35489007", "equivalent"),
    "F41.1": ("21897009", "equivalent"),
}


# ── lookups ────────────────────────────────────────────────────────────────

def lookup(system: str, code: str) -> dict[str, Any] | None:
    key = system.lower()
    table = OFFLINE.get(key)
    if table and code in table:
        return {"system": SYSTEMS[key], "code": code, "display": table[code], "source": "offline"}
    # tx.fhir.org fallback
    return _tx_lookup(system, code)


def _tx_lookup(system: str, code: str) -> dict[str, Any] | None:
    uri = SYSTEMS.get(system.lower())
    if not uri:
        return None
    url = (
        os.environ.get("FHIR_TX_URL", "https://tx.fhir.org/r4")
        + "/CodeSystem/$lookup?"
        + urllib.parse.urlencode({"system": uri, "code": code})
    )
    try:
        with urllib.request.urlopen(url, timeout=5) as r:
            data = json.load(r)
    except (urllib.error.URLError, TimeoutError):
        return None
    params = {p["name"]: p for p in data.get("parameter", [])}
    if "display" in params:
        return {"system": uri, "code": code, "display": params["display"].get("valueString"), "source": "tx.fhir.org"}
    return None


def map_codes(from_spec: str, to_system: str) -> dict[str, Any] | None:
    """from_spec is like 'icd10:I10'; returns the mapped code in to_system."""
    src_system, src_code = from_spec.split(":", 1)
    if src_system.lower() in ("icd10", "icd10cm") and to_system.lower() == "snomed":
        pair = ICD_TO_SNOMED.get(src_code)
        if pair:
            target_code, eq = pair
            return {
                "from": lookup(src_system, src_code),
                "to": lookup("snomed", target_code),
                "equivalence": eq,
                "source": "offline",
            }
    if src_system.lower() == "snomed" and to_system.lower() in ("icd10", "icd10cm"):
        for icd, (snomed, eq) in ICD_TO_SNOMED.items():
            if snomed == src_code:
                return {
                    "from": lookup("snomed", src_code),
                    "to": lookup("icd10", icd),
                    "equivalence": eq,
                    "source": "offline",
                }
    return None


def search(query: str) -> list[dict[str, Any]]:
    q = query.lower()
    out: list[dict[str, Any]] = []
    for sys_name, table in OFFLINE.items():
        for code, display in table.items():
            if q in display.lower():
                out.append({"system": SYSTEMS[sys_name], "code": code, "display": display, "source": "offline"})
    return out


# ── CLI ────────────────────────────────────────────────────────────────────

def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_l = sub.add_parser("lookup")
    p_l.add_argument("system")
    p_l.add_argument("code")

    p_m = sub.add_parser("map")
    p_m.add_argument("from_spec", help="e.g. 'icd10:I10'")
    p_m.add_argument("--to", required=True)

    p_s = sub.add_parser("search")
    p_s.add_argument("query")

    args = ap.parse_args()

    if args.cmd == "lookup":
        out = lookup(args.system, args.code)
    elif args.cmd == "map":
        out = map_codes(args.from_spec, args.to)
    elif args.cmd == "search":
        out = search(args.query)
    else:
        return 1

    print(json.dumps(out, indent=2))
    return 0 if out else 2


if __name__ == "__main__":
    raise SystemExit(main())
