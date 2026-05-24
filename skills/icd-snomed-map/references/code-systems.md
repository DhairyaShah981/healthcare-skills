# Offline code table

The most common clinical concepts and their canonical codes across systems.
This is the table `scripts/code_lookup.py` consults first before falling back to `tx.fhir.org` or UMLS.

## Canonical system URIs

| System | URI |
|---|---|
| ICD-10-CM | `http://hl7.org/fhir/sid/icd-10-cm` |
| ICD-10 (intl) | `http://hl7.org/fhir/sid/icd-10` |
| SNOMED CT | `http://snomed.info/sct` |
| LOINC | `http://loinc.org` |
| RxNorm | `http://www.nlm.nih.gov/research/umls/rxnorm` |
| CPT | `http://www.ama-assn.org/go/cpt` |
| HCPCS | `https://www.cms.gov/Medicare/Coding/HCPCSReleaseCodeSets` |
| NDC | `http://hl7.org/fhir/sid/ndc` |
| UCUM | `http://unitsofmeasure.org` |

## Common diagnoses — ICD-10-CM ↔ SNOMED CT

| ICD-10-CM | SNOMED CT | Concept |
|---|---|---|
| I10 | 59621000 | Essential hypertension |
| I50.9 | 84114007 | Heart failure, unspecified |
| I25.10 | 414545008 | Atherosclerotic heart disease |
| I63.9 | 230690007 | Cerebrovascular accident |
| I48.91 | 49436004 | Atrial fibrillation |
| E11.9 | 44054006 | Type 2 diabetes mellitus |
| E10.9 | 46635009 | Type 1 diabetes mellitus |
| E78.5 | 55822004 | Hyperlipidemia |
| E66.9 | 414916001 | Obesity |
| E03.9 | 40930008 | Hypothyroidism |
| J44.9 | 13645005 | Chronic obstructive pulmonary disease |
| J45.909 | 195967001 | Asthma |
| J20.9 | 6142004 | Acute bronchitis |
| J18.9 | 233604007 | Pneumonia, unspecified |
| N18.6 | 46177005 | End-stage renal disease |
| N39.0 | 68566005 | Urinary tract infection |
| K21.9 | 235595009 | Gastroesophageal reflux disease |
| K57.30 | 235759005 | Diverticulosis of colon |
| M25.50 | 57676002 | Joint pain |
| M54.50 | 279039007 | Low back pain |
| G43.909 | 25064002 | Migraine |
| G47.00 | 193462001 | Insomnia |
| F32.9 | 35489007 | Depressive disorder |
| F41.1 | 21897009 | Generalized anxiety disorder |
| R51 | 25064002 | Headache |
| R10.9 | 21522001 | Abdominal pain |
| R05 | 49727002 | Cough |
| R50.9 | 386661006 | Fever |

## Common vital signs and labs — LOINC

| Code | Display |
|---|---|
| 85354-9 | Blood pressure panel with all children optional |
| 8480-6 | Systolic blood pressure |
| 8462-4 | Diastolic blood pressure |
| 8867-4 | Heart rate |
| 9279-1 | Respiratory rate |
| 8310-5 | Body temperature |
| 2708-6 | Oxygen saturation in Arterial blood |
| 59408-5 | Oxygen saturation in Arterial blood by Pulse oximetry |
| 29463-7 | Body weight |
| 8302-2 | Body height |
| 39156-5 | Body mass index (BMI) |
| 9843-4 | Head circumference |
| 4548-4 | Hemoglobin A1c |
| 2345-7 | Glucose [Mass/volume] in Serum or Plasma |
| 2339-0 | Glucose [Mass/volume] in Blood |
| 14749-6 | Glucose [Moles/volume] in Serum or Plasma |
| 718-7 | Hemoglobin [Mass/volume] in Blood |
| 4544-3 | Hematocrit |
| 6690-2 | Leukocytes [#/volume] in Blood |
| 777-3 | Platelets [#/volume] in Blood |
| 2160-0 | Creatinine [Mass/volume] in Serum or Plasma |
| 3094-0 | Urea nitrogen [Mass/volume] in Serum or Plasma |
| 2823-3 | Potassium [Moles/volume] in Serum or Plasma |
| 2951-2 | Sodium [Moles/volume] in Serum or Plasma |
| 13457-7 | LDL Cholesterol |
| 2085-9 | HDL Cholesterol |
| 2093-3 | Cholesterol [Mass/volume] in Serum or Plasma |
| 2571-8 | Triglyceride [Mass/volume] in Serum or Plasma |
| 1742-6 | Alanine aminotransferase (ALT) |
| 1920-8 | Aspartate aminotransferase (AST) |
| 3016-3 | TSH |
| 1988-5 | C-reactive protein |
| 26474-7 | Lymphocytes [#/volume] in Blood |

## Common medications — RxNorm

| Code | Display |
|---|---|
| 314076 | lisinopril 10 MG |
| 207106 | atorvastatin 10 MG |
| 860975 | metformin hydrochloride 500 MG |
| 198211 | amlodipine 5 MG |
| 197361 | losartan 50 MG |
| 312961 | levothyroxine 50 MCG |
| 197316 | omeprazole 20 MG |
| 161 | acetaminophen 500 MG |
| 5640 | ibuprofen 200 MG |
| 1191 | aspirin 81 MG |
| 11289 | warfarin |
| 7980 | penicillin |
| 723 | amoxicillin |
| 18631 | azithromycin |
| 5640 | hydrochlorothiazide 25 MG |
| 6918 | metoprolol tartrate 50 MG |
| 197411 | gabapentin 100 MG |
| 197697 | sertraline 50 MG |
| 7646 | omeprazole |
| 35636 | albuterol |

## Common procedures — CPT

| Code | Display |
|---|---|
| 99213 | Office visit, established patient, level 3 |
| 99214 | Office visit, established patient, level 4 |
| 99203 | Office visit, new patient, level 3 |
| 99204 | Office visit, new patient, level 4 |
| 99396 | Periodic comprehensive preventive visit, 40–64 years |
| 99397 | Periodic comprehensive preventive visit, 65+ years |
| 90686 | Influenza vaccine, quadrivalent (IIV4) |
| 90630 | Influenza vaccine, quadrivalent intradermal |
| 90471 | Immunization administration, one vaccine |
| 36415 | Routine venipuncture |
| 71045 | Chest X-ray, single view |
| 80061 | Lipid panel |
| 80048 | Basic metabolic panel |
| 80050 | General health panel |
| 83036 | Hemoglobin A1c |
| 85025 | CBC with automated differential |
| 80053 | Comprehensive metabolic panel |
| 93000 | ECG, complete |

## Encounter classes — `v3-ActCode`

| Code | Display |
|---|---|
| AMB | Ambulatory |
| EMER | Emergency |
| IMP | Inpatient |
| ACUTE | Inpatient acute |
| HH | Home health |
| VR | Virtual |
| OBSENC | Observation encounter |
| SS | Short-stay |

## Observation categories

| Code | Display | System |
|---|---|---|
| vital-signs | Vital signs | `http://terminology.hl7.org/CodeSystem/observation-category` |
| laboratory | Laboratory | `http://terminology.hl7.org/CodeSystem/observation-category` |
| social-history | Social history | `http://terminology.hl7.org/CodeSystem/observation-category` |
| imaging | Imaging | `http://terminology.hl7.org/CodeSystem/observation-category` |
| survey | Survey | `http://terminology.hl7.org/CodeSystem/observation-category` |
| exam | Exam | `http://terminology.hl7.org/CodeSystem/observation-category` |
| therapy | Therapy | `http://terminology.hl7.org/CodeSystem/observation-category` |
| activity | Activity | `http://terminology.hl7.org/CodeSystem/observation-category` |
