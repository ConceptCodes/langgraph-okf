---
type: Clause
title: DPA Section 8 - Data Retention and Deletion
description: Retention limits for Customer Data and certified deletion obligations upon termination.
tags: [data-retention, deletion, dpa, gdpr, clause]
verified: { by: "human:dpo_michael", at: "2026-06-01T08:00:00Z" }
sources:
  - id: gdpr-art-5
    resource: https://gdpr-info.eu/art-5-gdpr/
    title: GDPR Article 5 — Principles Relating to Processing of Personal Data
---

# DPA Section 8: Data Retention and Deletion

## 8.1 Retention During Term
Provider shall retain [Personal Data](/definitions/personal_data.md) solely for the
duration of the applicable Order Form and only as necessary to provide the contracted
services. No Personal Data shall be used for Provider's own commercial purposes without
Customer's prior written consent.

## 8.2 Deletion on Termination
Within **thirty (30) days** of termination or expiration, Provider shall, at Customer's election:

1. Return all Customer Data in a standard exportable format (CSV, JSON, or equivalent); **or**
2. Securely delete all Customer Data from production systems and confirm deletion in writing.

## 8.3 Backup Retention Exception
Provider may retain Customer Data in encrypted offline backup media for up to
**ninety (90) additional days** solely to protect against accidental deletion.
Such backup data shall be purged on the next scheduled backup rotation and is not
accessible for operational use.

## 8.4 Legal Hold Exception
If Provider is subject to a legal obligation preventing deletion, Provider shall:

1. Notify Customer in writing within five (5) business days.
2. Isolate the retained data from active processing systems.
3. Delete the data as soon as the legal hold is lifted.

## 8.5 Deletion Certification
Upon completion of deletion, Provider shall issue a written certification within
**five (5) business days**, identifying the data categories deleted, the deletion
method used, and the date of deletion.

## 8.6 Relation to Data Breach
If a [Data Breach](/definitions/data_breach.md) is discovered during the deletion period,
Provider's obligations under [Security Incident Notification](security_incident_notification.md)
apply in full before deletion of the affected data set.
