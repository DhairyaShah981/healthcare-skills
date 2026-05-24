# HIPAA Security Rule — engineer-facing summary

Citations are to 45 CFR Part 164, Subpart C. Read this in tandem with the actual rule text; this is a working summary, not a legal restatement.

## The three safeguards categories

| Type | What it covers | Engineering surface |
|---|---|---|
| Administrative (§164.308) | Policies, training, contingency plans, BAAs | Mostly out of scope for code review; relevant to vendor selection |
| Physical (§164.310) | Facility access, workstation security, device controls | Mostly out of scope; matters for endpoint security configs |
| **Technical (§164.312)** | Encryption, authentication, audit, integrity, transmission | **This is where code review lives** |

## Technical safeguards (§164.312) — the engineer's checklist

### §164.312(a) — Access control
- (a)(1) — Implement technical policies and procedures for electronic information systems containing PHI to allow access only to authorized persons
- (a)(2)(i) — **Unique user identification (required).** No shared accounts.
- (a)(2)(ii) — Emergency access procedure (required)
- (a)(2)(iii) — Automatic logoff (addressable)
- (a)(2)(iv) — **Encryption and decryption (addressable).** "Addressable" ≠ optional — you must either implement, or document why an equivalent alternative is in place.

### §164.312(b) — Audit controls
Implement hardware, software, and/or procedural mechanisms that **record and examine activity** in information systems that contain or use PHI. There is no carve-out; reads and writes of PHI both require audit.

### §164.312(c) — Integrity
- (c)(1) — Policies and procedures to **protect PHI from improper alteration or destruction**
- (c)(2) — Mechanisms to authenticate PHI (e.g. checksums, digital signatures, append-only history for clinical notes)

### §164.312(d) — Person or entity authentication
Verify that a person or entity seeking access is the one claimed. In practice: MFA for privileged users, strong password hashing, rotated service tokens.

### §164.312(e) — Transmission security
- (e)(1) — Guard against unauthorized access to PHI being transmitted over an electronic communications network
- (e)(2)(i) — Integrity controls (addressable)
- (e)(2)(ii) — **Encryption (addressable).** TLS 1.2+ for all PHI-bearing transmissions.

## Privacy Rule (§164.500–.534) — engineer-facing highlights

- **§164.502(b) Minimum necessary** — uses and disclosures must be limited to the minimum needed. Doesn't apply to treatment.
- **§164.508 Authorization** — most uses outside TPO (treatment, payment, operations) require patient authorization.
- **§164.514(b) De-identification** — Safe Harbor (the 18 identifiers) and Expert Determination are the two paths. See the `phi-redact` skill.

## Breach Notification Rule (§164.400–.414)

A breach is the **acquisition, access, use, or disclosure of PHI in a manner not permitted** by the Privacy Rule, which compromises the security or privacy of the PHI. Includes accidental access.

Notification requirements scale with breach size:
- < 500 affected: log internally; report annually to HHS
- ≥ 500 affected: notify HHS within 60 days; potentially also media
- Always: notify affected individuals within 60 days

**PHI in a log file shipped to a vendor without a BAA is a reportable breach.** This is the #1 reason healthcare engineering shops get fined.

## Encryption — what counts

HHS guidance points to **NIST SP 800-111** for at-rest and **NIST SP 800-52** / **FIPS 140-2 / 140-3** validated modules for in-transit. Practically:

- At rest: AES-256-GCM. Application-level encryption (field-level) for high-sensitivity fields like SSN. KMS-managed keys.
- In transit: TLS 1.2 minimum, prefer TLS 1.3. mTLS for service-to-service.
- Key rotation: at least annually.

## "Addressable" doesn't mean "optional"

Several requirements (encryption at rest, automatic logoff, encryption in transit) are marked "addressable" — meaning you may implement an equivalent control or document a reasoned decision not to. In practice, regulators expect encryption and treat absence as a finding.

## Business Associate Agreement (BAA)

Any vendor that creates, receives, maintains, or transmits PHI on your behalf is a Business Associate and **requires a signed BAA before you send them PHI**. Common gotchas:

- Datadog, Sentry, LogRocket, FullStory, Segment — all are BAs if logs / events contain PHI. Each has a different BAA process (often a separate "HIPAA-eligible" tier).
- AWS / GCP / Azure — sign their BAA at the account level; certain services are not in scope (read the eligibility list).
- A signed BAA covers you contractually; it **doesn't make a leak OK** — minimum-necessary still applies.
