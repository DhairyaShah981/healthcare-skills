# HIPAA Safe Harbor — the 18 identifiers

Per **45 CFR §164.514(b)(2)(i)**, data is considered de-identified under Safe Harbor when **all 18** of the following identifiers — of the individual *or of relatives, employers, or household members* — are removed.

| #  | Identifier | Notes for the scrubber |
|----|-----------|------------------------|
| 1  | Names | First, last, middle, maiden, nicknames. Also family-member names. |
| 2  | Geographic subdivisions smaller than a state | Street, city, county, precinct. ZIP allowed only as first three digits *if* the combined population of all ZIPs with that ZIP3 is >20,000 (else those ZIP3s must be `000`). |
| 3  | All elements of dates (except year) directly related to an individual | Birth date, admission date, discharge date, date of death. All ages over 89 → "90+". |
| 4  | Telephone numbers | Including extensions, alt numbers. |
| 5  | Fax numbers | |
| 6  | Email addresses | |
| 7  | Social Security numbers | Including last-4. |
| 8  | Medical record numbers (MRN) | |
| 9  | Health plan beneficiary numbers | |
| 10 | Account numbers | |
| 11 | Certificate / license numbers | Driver's license, state ID. |
| 12 | Vehicle identifiers and serial numbers, including license plates | |
| 13 | Device identifiers and serial numbers | Pacemaker, insulin pump, etc. |
| 14 | Web URLs | |
| 15 | IP addresses | Both v4 and v6. |
| 16 | Biometric identifiers | Fingerprints, voiceprints, iris scans. |
| 17 | Full-face photographs and comparable images | |
| 18 | Any other unique identifying number, characteristic, or code | Catch-all; includes hospital-internal codes, encounter IDs that map 1:1 to a patient. |

## §164.514(b)(2)(ii) — knowledge clause

Even after removing 1–18, the covered entity must not have **actual knowledge** that the remaining information could be used alone or in combination to re-identify the individual.

## Practical implications for `phi-redact`

- "Year of birth + 3-digit ZIP + gender" can still re-identify someone in a sparsely populated region. Default to redacting all three.
- A surgery date + procedure type + hospital can re-identify celebrities and any patient in a small facility. Aggregate dates to year for any free-text.
- Encounter IDs (item 18) are PHI in their own right, even though they look like opaque tokens. Either remove them or replace with pseudonyms (see the `deid-vault` skill).
- Removing PHI from a log is **not** the same as de-identifying a dataset for research. Safe Harbor governs disclosure of datasets; logging hygiene is a separate (often stricter) operational requirement.
