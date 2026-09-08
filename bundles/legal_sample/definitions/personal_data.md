---
type: Definition
title: Personal Data
description: Any information relating to an identified or identifiable natural person processed under the DPA.
tags: [personal-data, gdpr, ccpa, dpa, definitions]
verified: { by: "human:dpo_michael", at: "2026-06-01T08:00:00Z" }
sources:
  - id: gdpr-art-4
    resource: https://gdpr-info.eu/art-4-gdpr/
    title: GDPR Article 4 — Definitions
  - id: ccpa-1798-140
    resource: https://leginfo.legislature.ca.gov/faces/codes_displaySection.xhtml?lawCode=CIV&sectionNum=1798.140
    title: CCPA Section 1798.140 — Definitions
---

# Definition: Personal Data

**"Personal Data"** means any information relating to an identified or identifiable
natural person (**"Data Subject"**). A natural person is identifiable if they can be
identified, directly or indirectly, by reference to:

- A name, identification number, or location data.
- An online identifier (IP address, cookie ID, device fingerprint).
- One or more factors specific to the physical, physiological, genetic, mental,
  economic, cultural, or social identity of that person.

## Categories Processed Under the CloudScale DPA

| Category | Examples | Sensitivity |
|----------|----------|-------------|
| Identity data | Name, employee ID, email address | Standard |
| Authentication data | Hashed passwords, MFA tokens | High |
| Usage data | Log entries, feature interaction timestamps | Standard |
| Location data | IP-derived city/country | Standard |
| Special category data | Health, biometric, or racial data | **Restricted** — requires explicit consent |

## Regulatory Scope

This definition aligns with:

- **GDPR** Article 4(1) (EU/EEA data subjects).
- **CCPA** Section 1798.140(o) (California residents).
- **UK GDPR** Section 3(2) (UK data subjects post-Brexit).

## Relation to Data Breach

Personal Data is the key asset whose unauthorised access or disclosure triggers the
[Data Breach](/definitions/data_breach.md) definition and associated notification
obligations under [Security Incident Notification](/contracts/dpa/clauses/security_incident_notification.md).

## Relation to Sub-Processors

[Sub-processors](/contracts/dpa/clauses/sub_processors.md) may only process Personal
Data to the extent strictly necessary for their contracted sub-processing function.
