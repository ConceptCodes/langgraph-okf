---
type: Reference
title: Sample Bundle Scope and Limitations
description: Fictional provenance, missing source documents, and calculation assumptions.
status: stable
---

# Scope

This bundle is a fictional software test fixture. No signed MSA, DPA, SLA, Order
Form, fee ledger, or attorney approval is supplied. Existing human verification
records are illustrative metadata only. Statutory background links do not establish
that a negotiated term is enforceable or that these fictional clauses were reviewed.

# Calculation boundaries

- The MSA cap uses fees paid or payable in the 12 months before the first liability event.
- The DPA cap uses fees actually paid in the 12 months before the incident.
- One supplied dollar amount is used as a scenario input; it does not establish either fee base.
- The sample does not resolve all overlaps between DPA claims and MSA exclusions
  (confidentiality, gross negligence, willful misconduct, fraud, and unpaid fees).
  The independent-cap wording in MSA 11.4 and sub-limit wording in DPA 10.2 also
  leave combined claims ambiguous. Calculations show individual scenarios, not a
  combined recovery limit.
- Notice calculations return durations, not calendar deadlines. They do not establish
  receipt dates, enforceability, or completion of written-notice requirements.
- Service credit calculations compute estimated percentages and dollar amounts from SLA
  Section 4 for explicitly supplied monthly fees and uptime percentages. They do not resolve
  claim submission timing or force majeure exclusions.

# Execution and trust

The consumer runs three registered local Python rules. Bundle code and resource URLs
are never executed. There is no independent receipt attester; results explicitly
report `attestation_verified: false`. A matching executor name is routing metadata,
not proof that a document or result has been authenticated.

The sample covers selected clauses only. Missing Order Forms, amendments, effective
dates, fee records, and claim facts must be obtained before applying it to a real case.
