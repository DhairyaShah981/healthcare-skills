---
name: prior-auth-fhir
description: |
  Build FHIR R4 prior-authorization payloads — CoverageEligibilityRequest /
  CoverageEligibilityResponse and Da Vinci PAS Claim / ClaimResponse — and the
  CRD/DTR/PAS hook glue that powers payer prior-auth flows. Use when the user
  asks to "build a prior auth", "check eligibility", "send a PAS claim", or
  is integrating with a payer's FHIR endpoint.
when_to_use: |
  Activate when the user:
  - Asks to build a prior-authorization payload
  - References CoverageEligibilityRequest, CoverageEligibilityResponse,
    Claim ($submit), ClaimResponse, or Da Vinci PAS
  - Is integrating with a payer FHIR endpoint
  - Mentions CRD (Coverage Requirements Discovery), DTR (Documentation
    Templates and Rules), or PAS (Prior Authorization Support)
  - Needs to surface "this service requires prior auth" to a clinician
allowed-tools: [Read, Write, Edit, Bash]
license: MIT
tags: [fhir, prior-auth, healthcare, davinci, payer]
incident: |
  Prior-auth integration was implemented bespoke per payer, with subtly
  different bundle shapes, missing identifiers, and incomplete supporting
  documents. Submissions that "looked right" got auto-rejected because a
  required CoverageEligibilityRequest.servicedDate or Claim.insurance link
  was missing. This skill encodes the Da Vinci PAS canonical shape so the
  first submission lands cleanly.
---

# prior-auth-fhir

> Da Vinci PAS / CRD / DTR shapes, done right. CoverageEligibility → Claim → ClaimResponse.

## When to use

- The user is building a prior-authorization integration with a payer.
- The user mentions Da Vinci, CRD, DTR, PAS, X12 278, or "PA workflow".
- The user asks "is this service covered?" / "do I need PA for X?".
- The user is implementing the clinician-facing "submit PA" UI.

## How it works

1. **Pick the right resource for the question.**
   - "Is this patient covered for this service?" → `CoverageEligibilityRequest` ($submit) → `CoverageEligibilityResponse`
   - "Does this service require prior auth, and what docs do I need?" → CRD hook (`order-select` / `order-sign`) returns Cards
   - "Submit the prior-auth request" → Da Vinci PAS `Claim` ($submit) → `ClaimResponse`
   - "Fill out the PA documentation form" → DTR fetches a `Questionnaire` from the payer; the EHR renders + the clinician completes it

2. **Build the payload with the required identifiers.** Common mistakes:
   - Missing `Patient.identifier` with the payer's member ID
   - Missing `Coverage.identifier` (the policy number)
   - `subscriberId` on `Coverage` not matching the member ID
   - `servicedDate` / `servicedPeriod` missing on `CoverageEligibilityRequest.item`
   - Wrong system URI on the service code (CPT vs HCPCS vs SNOMED)

3. **For CoverageEligibilityRequest:**
   ```json
   {
     "resourceType": "CoverageEligibilityRequest",
     "status": "active",
     "purpose": ["benefits"],
     "patient": {"reference": "Patient/123"},
     "servicedDate": "2026-06-01",
     "created": "2026-05-24",
     "insurer": {"reference": "Organization/payer-001"},
     "provider": {"reference": "PractitionerRole/practroles-001"},
     "insurance": [{"coverage": {"reference": "Coverage/cov-001"}}],
     "item": [{
       "productOrService": {"coding": [{"system": "http://www.ama-assn.org/go/cpt", "code": "70553", "display": "MRI brain w/ contrast"}]}
     }]
   }
   ```

4. **For Da Vinci PAS Claim ($submit):**
   - `use: "preauthorization"` (not `claim`)
   - `type` from the Claim-Type-Codes value set (`institutional`, `professional`, `oral`, `pharmacy`, `vision`)
   - At least one `insurance` entry with `focal: true`
   - `supportingInfo[]` with the DTR-filled `QuestionnaireResponse`
   - `Bundle` of type `collection` wrapping the Claim + supporting resources

5. **Wire CRD as a CDS hook.** When a clinician adds a service to a pending order, the EHR fires `order-select` to your CRD service. Return Cards with:
   - "Prior auth required for service X" — `indicator: warning`
   - "Documentation requirements: [link to DTR Questionnaire]" — `links[]`
   - Optional `suggestions[]` to attach a starter `QuestionnaireResponse`

6. **DTR — render the Questionnaire.** Fetch the payer-published Questionnaire (often via `$package`), render it in the clinician UI, and post the completed `QuestionnaireResponse` as `supportingInfo` on the Claim.

7. **Async response handling.** Many payers respond asynchronously (the immediate `ClaimResponse` says "queued"; the final decision arrives via webhook or polling). Implement both.

## Example — eligibility check

**Input:**
> *Check eligibility for MRI brain w/ contrast (CPT 70553) for patient 123 on 2026-06-01, payer 'BCBS-CA'.*

**Output (CoverageEligibilityRequest bundle):**
See [`examples/eligibility-request.json`](./examples/eligibility-request.json).

**Response (from payer, abbreviated):**
```json
{
  "resourceType": "CoverageEligibilityResponse",
  "status": "active",
  "outcome": "complete",
  "patient": {"reference": "Patient/123"},
  "insurance": [{
    "coverage": {"reference": "Coverage/cov-001"},
    "item": [{
      "category": {"coding": [{"system": "http://terminology.hl7.org/CodeSystem/ex-benefitcategory", "code": "diagnostic"}]},
      "productOrService": {"coding": [{"system": "http://www.ama-assn.org/go/cpt", "code": "70553"}]},
      "authorizationRequired": true,
      "authorizationSupporting": [{"coding": [{"system": "...", "code": "clinical-rationale"}]}]
    }]
  }]
}
```

Interpretation: covered, **prior auth required**, and the payer wants the "clinical-rationale" supporting document. Hand off to CRD/DTR.

## Edge cases

- **`use` on Claim** must be `preauthorization` for PA submissions — not `claim`. Common silent error.
- **`focal: true`** on at least one insurance entry, even if the patient has only one policy.
- **`insurer` vs `provider`** — easy to swap. `insurer` is the payer; `provider` is the rendering / requesting clinician.
- **Service codes vary by payer.** Some accept CPT, some HCPCS, some both. Send both codings on `productOrService` when in doubt.
- **`servicedDate` is required** on `CoverageEligibilityRequest.item` for date-sensitive benefits. Missing → silent failure / generic response.
- **Bundle types differ for PAS.** `Bundle.type` is `collection` for PAS submission (per Da Vinci PAS IG), not `transaction`.
- **Auth-only flows.** Some payers expose a `$submit` operation that returns just `ClaimResponse`; others require the full bundle round-trip. Read each payer's CapabilityStatement.
- **Don't surface raw PA-denial reasoning verbatim to the patient.** Decisions sometimes carry payer-internal codes that aren't patient-friendly. Translate.

## References

- Da Vinci Prior Authorization Support (PAS): <https://hl7.org/fhir/us/davinci-pas/>
- Da Vinci CRD (Coverage Requirements Discovery): <https://hl7.org/fhir/us/davinci-crd/>
- Da Vinci DTR (Documentation Templates and Rules): <https://hl7.org/fhir/us/davinci-dtr/>
- FHIR R4 [CoverageEligibilityRequest](https://www.hl7.org/fhir/R4/coverageeligibilityrequest.html)
- FHIR R4 [CoverageEligibilityResponse](https://www.hl7.org/fhir/R4/coverageeligibilityresponse.html)
- FHIR R4 [Claim](https://www.hl7.org/fhir/R4/claim.html) and [ClaimResponse](https://www.hl7.org/fhir/R4/claimresponse.html)
- CMS Patient Access / Prior Authorization Final Rule (CMS-0057-F): <https://www.cms.gov/priorities/key-initiatives/burden-reduction/policies-and-regulations/interoperability/cms-interoperability-and-prior-authorization-final-rule>
- X12 278 (legacy PA transaction; what FHIR PAS replaces)
- Compose with: `cds-hook` (CRD service), `fhir-bundle` (Bundle construction), `smart-oauth-scaffold` (payer auth)
- [`examples/eligibility-request.json`](./examples/eligibility-request.json)
- [`examples/pas-claim.json`](./examples/pas-claim.json)
