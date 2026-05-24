---
name: cds-hook
description: |
  Scaffold a CDS Hooks 1.0 service: discovery endpoint, hook handler, and Card
  responses for patient-view, medication-prescribe, and order-select. Use when
  the user asks to "build a CDS Hook", "add a clinical alert", "build a
  decision-support service", "warn the clinician about X", or mentions
  drug-drug interactions, drug-allergy, or order checks.
when_to_use: |
  Activate when the user:
  - Asks to build a CDS Hooks service (discovery + hook handler)
  - Wants to add a clinical alert / warning to an EHR workflow
  - References drug-drug interactions, drug-allergy checks, duplicate-therapy
    detection, or guideline-based prompts
  - Is integrating decision support into Epic, Cerner, Athena, or another EHR
    via CDS Hooks
  - Mentions cards, suggestions, links, or app-launch in a clinical UI context
allowed-tools: [Read, Write, Edit, Bash]
license: MIT
tags: [cds, healthcare, fhir, interop]
incident: |
  Most home-grown clinical-alert systems are tightly coupled to one EHR vendor
  (Epic's BPA framework, Cerner's MPages) and hard to test, port, or evolve.
  CDS Hooks is the open standard for clinical-alert integration; this skill
  scaffolds it correctly the first time, with the right Card shape, scope
  guardrails, and offline-testable rules registry.
---

# cds-hook

> Scaffold a CDS Hooks 1.0 service correctly. Discovery, hook handler, Cards, prefetch — all from one description.

## When to use

- The user wants to surface a clinical alert / warning / suggestion to a clinician inside an EHR workflow.
- The user mentions drug-drug interactions, drug-allergy, duplicate therapy, or guideline-based prompts.
- The user is wiring up an Epic, Cerner, Athena, or open-source EHR to a decision-support service.
- The user pastes a Card shape and asks how to respond, or asks "what does the EHR send me?"

## How it works

1. **Pin to CDS Hooks 1.0.** Spec: <https://cds-hooks.hl7.org/1.0/>. The standard defines the discovery endpoint, the hook request shape, and the Card response shape.

2. **Decide which hooks to support.** The standard set:
   - `patient-view` — fires when a clinician opens a patient chart
   - `medication-prescribe` (deprecated, replaced by `order-select` + `order-sign`)
   - `order-select` — fires when a clinician adds an item to a pending-orders list
   - `order-sign` — fires when a clinician signs an order set
   - `appointment-book` — fires when scheduling
   - `encounter-start`, `encounter-discharge` — encounter lifecycle

3. **Implement the discovery endpoint.** `GET /cds-services` returns the list of services you provide:
   ```json
   {
     "services": [{
       "hook": "medication-prescribe",
       "id": "ddi-check",
       "title": "Drug-drug interaction check",
       "description": "Warns on clinically-significant DDIs.",
       "prefetch": {
         "patient": "Patient/{{context.patientId}}",
         "active_meds": "MedicationRequest?patient={{context.patientId}}&status=active"
       }
     }]
   }
   ```

4. **Implement the hook handler.** `POST /cds-services/{id}` receives:
   ```json
   {
     "hook": "medication-prescribe",
     "hookInstance": "01HF7T...",
     "fhirServer": "https://ehr.example.org/r4",
     "context": {"patientId": "P123", "encounterId": "E456", "userId": "Pract/U7", "medications": {...}},
     "prefetch": {"patient": {...}, "active_meds": {...}}
   }
   ```
   Return one or more Cards.

5. **Build Card shapes correctly.** A Card has `summary` (≤140 chars), `indicator` (`info` / `warning` / `critical`), optional `detail`, `source`, `suggestions[]`, `links[]`:
   ```json
   {
     "cards": [{
       "summary": "Drug-drug interaction: warfarin + aspirin",
       "indicator": "warning",
       "detail": "Combining warfarin and aspirin increases bleeding risk. Consider gastric protection or alternative analgesia.",
       "source": {"label": "DDI Registry v3.2", "url": "https://example.org/ddi/3.2"},
       "suggestions": [{
         "label": "Replace aspirin with acetaminophen 500 mg",
         "uuid": "01HF7T...",
         "actions": [{
           "type": "delete", "resource": {"resourceType": "MedicationRequest", "id": "med-aspirin"}
         }, {
           "type": "create", "resource": {"resourceType": "MedicationRequest", "status": "draft", "medicationCodeableConcept": {"coding": [{"system": "http://www.nlm.nih.gov/research/umls/rxnorm", "code": "161"}]}}
         }]
       }],
       "links": [{"label": "Up-to-date: warfarin interactions", "url": "https://www.uptodate.com/...", "type": "absolute"}]
     }]
   }
   ```

6. **Keep the rule logic separate.** The hook handler is HTTP glue; the rules (DDI matrix, allergy checks, dose ranges) live in a registry data file the rule engine reads. Easy to test, easy to evolve.

7. **Use prefetch to minimise EHR round-trips.** Declare what FHIR queries your service needs in the discovery response; the EHR pre-fetches and includes the data in the request. Always also support the fallback (`fhirServer` URL) for EHRs that don't prefetch.

8. **Handle auth.** CDS Hooks 1.0 supports JWT bearer tokens (`Authorization: Bearer …`) issued by the EHR. Verify the issuer and signature; cache the JWKS.

9. **Test offline.** Build a [`scripts/cds_mock_server.py`](./scripts/cds_mock_server.py) (or use the fhir-mcp mock pattern) so the CI suite can exercise hooks deterministically without a real EHR.

## Example — drug-drug interaction service

`GET /cds-services` →
```json
{"services": [{
  "hook": "medication-prescribe",
  "id": "ddi-check-v1",
  "title": "DDI check (basic)",
  "description": "Warns on aspirin+warfarin, NSAID+warfarin, and other high-risk pairs.",
  "prefetch": {"active_meds": "MedicationRequest?patient={{context.patientId}}&status=active"}
}]}
```

`POST /cds-services/ddi-check-v1` ← (request shown abbreviated)
```json
{
  "hook": "medication-prescribe",
  "hookInstance": "01HF7T9X3K",
  "context": {"patientId": "P123", "medications": {"resourceType": "Bundle", "entry": [{"resource": {"resourceType": "MedicationRequest", "medicationCodeableConcept": {"coding": [{"system": "http://www.nlm.nih.gov/research/umls/rxnorm", "code": "1191", "display": "aspirin"}]}}}]}},
  "prefetch": {"active_meds": {"resourceType": "Bundle", "entry": [{"resource": {"resourceType": "MedicationRequest", "medicationCodeableConcept": {"coding": [{"system": "http://www.nlm.nih.gov/research/umls/rxnorm", "code": "11289", "display": "warfarin"}]}}}]}}
}
```

Response →
```json
{"cards": [{
  "summary": "Major interaction: aspirin + warfarin",
  "indicator": "warning",
  "detail": "Co-administration significantly increases risk of bleeding (NIH category: D). Consider GI protection (PPI) or replace aspirin with acetaminophen.",
  "source": {"label": "DDI Registry v3.2"},
  "links": [{"label": "DDI evidence", "url": "https://example.org/ddi/aspirin-warfarin", "type": "absolute"}]
}]}
```

Full code in [`examples/patient-view-card.json`](./examples/patient-view-card.json), [`examples/ddi-prescribe-card.json`](./examples/ddi-prescribe-card.json), and the rules registry shape.

## Edge cases

- **Don't return Cards for low-confidence findings.** Alert fatigue is a real safety issue — false positives train clinicians to dismiss alerts. Tune severity thresholds carefully and provide an "always allow" suggestion that captures the override reason.
- **Suggestions must be self-contained FHIR actions.** A suggestion's `actions[]` is the *only* mechanism the EHR will use to apply it; if you reference resources the EHR doesn't know about, the suggestion fails silently.
- **Card `summary` ≤ 140 chars.** EHRs truncate longer strings. Put the punchline in the summary, the explanation in `detail`.
- **Prefetch tokens not interpolated.** The EHR substitutes `{{context.patientId}}` etc.; if your query syntax is wrong, the EHR fails silently and your handler receives no prefetch. Always handle the fallback path.
- **Auth failures must return 401, not Cards.** Don't smuggle errors into the Card layer; the EHR can't act on them.
- **Hooks fire per render.** `patient-view` can fire many times per chart open. Make handlers idempotent and cheap.
- **PHI in `detail`.** The `detail` field appears in EHR audit logs — keep it informational, not patient-specific in a way that doubles the patient's PHI footprint.

## References

- CDS Hooks 1.0 spec: <https://cds-hooks.hl7.org/1.0/>
- CDS Hooks GitHub: <https://github.com/cds-hooks>
- Sample card shapes: <https://cds-hooks.hl7.org/1.0/#card-attributes>
- [`examples/patient-view-card.json`](./examples/patient-view-card.json)
- [`examples/ddi-prescribe-card.json`](./examples/ddi-prescribe-card.json)
- ONC §170.315(b)(11) — Clinical decision support
- HL7 [Clinical Quality Language (CQL)](https://cql.hl7.org/) — for guideline-as-code rule engines
