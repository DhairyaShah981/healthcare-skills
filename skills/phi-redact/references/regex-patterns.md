# Regex catalog

Battle-tested patterns for the `phi-redact` skill. Each pattern is paired with the Safe Harbor identifier it maps to.

> Regex alone misses ~30% of PHI (free-text names, unusual MRN formats). Use these as a baseline; for production-grade detection, route through Presidio or an NER model.

## Identifiers

| Type | Pattern (PCRE) | Safe Harbor # |
|---|---|---|
| SSN | `\b\d{3}-\d{2}-\d{4}\b` | 7 |
| SSN (no dashes) | `\b(?!000\|666)([0-8]\d{2})([ \-]?)((?!00)\d{2})\2((?!0000)\d{4})\b` | 7 |
| Phone (US) | `\b(?:\+?1[-.\s]?)?\(?[2-9]\d{2}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b` | 4 |
| Email | `\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b` | 6 |
| IPv4 | `\b(?:\d{1,3}\.){3}\d{1,3}\b` | 15 |
| IPv6 | `\b(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}\b` | 15 |
| URL | `\bhttps?://[^\s<>"']+` | 14 |
| ZIP+4 | `\b\d{5}-\d{4}\b` | 2 |
| ZIP5 | `\b\d{5}\b` | 2 |
| DOB ISO | `\b(19\|20)\d{2}-(0[1-9]\|1[0-2])-(0[1-9]\|[12]\d\|3[01])\b` | 3 |
| Date (US) | `\b(0?[1-9]\|1[0-2])[/-](0?[1-9]\|[12]\d\|3[01])[/-]\d{2,4}\b` | 3 |
| MRN-like (labelled) | `(?i)\bMRN[:\s#]*([A-Z]?\d{6,10})\b` | 8 |
| MRN-like (unlabelled) | `\b\d{7,10}\b` *(noisy — use with context)* | 8 |
| Driver license | `\b[A-Z]\d{7,8}\b` | 11 |
| Credit card | `\b(?:\d[ -]*?){13,19}\b` *(then Luhn-check)* | 10 |

## JSON-key triggers (structural pass)

```regex
^\s*"(?:first|last|middle|maiden|full|family|given|patient|guardian|emergency)_?name"
^\s*"(?:dob|birth_?date|date_?of_?birth)"
^\s*"(?:ssn|social_?security)"
^\s*"(?:mrn|chart_?id|patient_?id|medical_?record(?:_?number)?)"
^\s*"(?:phone|telephone|cell|mobile|fax)"
^\s*"(?:email|email_?address)"
^\s*"(?:address|street|line[12]?|city|state|zip(?:_?code)?|postal_?code)"
^\s*"(?:account_?(?:no\|number)?\|member_?id\|policy_?(?:no\|number)?)"
^\s*"(?:license|driver_?license\|state_?id)"
^\s*"(?:ip_?address|user_?agent)"
^\s*"(?:device_?id\|serial_?(?:no\|number))"
```

## Free-text name heuristics (the hard part)

Plain regex can't reliably catch a name. Useful heuristics:

- Two consecutive capitalized tokens preceded by an honorific: `(?:Mr|Mrs|Ms|Dr|RN|MD|DO|NP|PA)\.?\s+[A-Z][a-z]+\s+[A-Z][a-z]+`
- A possessive name in clinical narrative: `[A-Z][a-z]+'s\s+(?:wife|husband|mother|father|daughter|son|child|partner)`
- A patient-record header line: `(?i)^(?:patient|name)\s*[:=]\s*[A-Z][a-z]+\s+[A-Z][a-z]+`

Anything beyond these heuristics → escalate to Presidio or an NER model (e.g. spaCy `en_core_web_lg`).

## Anti-patterns (don't match these)

- Drug names: "Lisinopril", "Metformin", "Atorvastatin" — capitalized but not PHI.
- Anatomy: "Right Atrium", "Left Anterior Descending" — capitalized but not PHI.
- Diagnoses: "Diabetes Mellitus", "Hypertensive Heart Disease" — likewise.
- Hospital names: usually safe to keep, but in combination with date+procedure they become identifying — redact when in doubt.

Maintain a `safe_allowlist.txt` of these strings and skip matches that appear in it.
