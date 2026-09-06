---
type: Attested Computation
title: Termination Notice Period Computation
description: Illustrative notice and cure durations for specified termination grounds.
tags: [termination, notice, computation, attested]
generated: { by: "process:sample-bundle-audit", at: "2026-09-05T00:00:00Z" }
runtime: python
parameters:
  - { name: termination_reason, type: string, required: true }
executor:
  name: notice_period_calc_v1
  resource: /scope.md
  receipt: [computation_id, inputs, required_advance_notice_days, cure_period_days, immediate]
---

# Computation

Illustrative calculation of notice and cure durations. Written notice is still
required for insolvency; the material-breach cure period starts on receipt of
written notice. Calendar deadlines and independent attestation are not implemented.
See [scope](/scope.md).

```python
def calculate_termination_notice(
    termination_reason: str,
) -> dict:
    """
    termination_reason options:
    - 'convenience': Voluntary termination
    - 'material_breach': Breach of fundamental obligation
    - 'insolvency': Bankruptcy or liquidation
    """
    if termination_reason == "convenience":
        return {
            "required_advance_notice_days": 60,
            "cure_period_days": 0,
            "immediate": False,
            "governing_clause": "MSA Section 14.3",
            "condition": "Requires payment of all committed fees through end of current term."
        }
    elif termination_reason == "material_breach":
        return {
            "required_advance_notice_days": 30,
            "cure_period_days": 30,
            "immediate": False,
            "governing_clause": "MSA Section 14.2(1)",
            "condition": "Termination takes effect only if breach is uncured after 30 days."
        }
    elif termination_reason == "insolvency":
        return {
            "required_advance_notice_days": 0,
            "cure_period_days": 0,
            "immediate": True,
            "governing_clause": "MSA Section 14.2(2)",
            "condition": "Immediate termination upon filing or bankruptcy proceeding."
        }
    else:
        raise ValueError(f"Unknown termination reason: {termination_reason}")
```

## Related Provisions
- [Termination Clause](/contracts/msa/clauses/termination.md)
- [Material Breach Definition](/definitions/material_breach.md)
