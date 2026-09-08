---
type: Attested Computation
title: SLA Service Credit Computation Rule
description: Calculates the service credit percentage and dollar amount owed for a given monthly uptime percentage.
tags: [sla, credits, computation, financial, attested]
generated: { by: "process:sample-bundle-audit", at: "2026-09-05T00:00:00Z" }
runtime: python
parameters:
  - { name: monthly_uptime_pct, type: number, required: true }
  - { name: monthly_fee, type: number, required: true }
executor:
  name: sla_credit_calc_v1
  resource: /scope.md
  receipt: [computation_id, inputs, credit_pct, credit_amount, governing_clause]
---

# Computation

Calculates the service credit owed for an uptime shortfall in a given billing month.
Both `monthly_uptime_pct` (0–100) and `monthly_fee` (finite, positive) must be supplied
explicitly. No default amounts are assumed. See [scope and limits](/scope.md).

```python
def calculate_sla_credit(
    monthly_uptime_pct: float,
    monthly_fee: float,
) -> dict:
    """
    monthly_uptime_pct: measured uptime for the month (e.g. 98.5 for 98.5%)
    monthly_fee:        the customer's net monthly fee for the affected service
    Credit tiers per SLA Section 4:
      >= 99.9%          -> no credit
      99.0% to < 99.9%  -> 10%
      95.0% to < 99.0%  -> 25%
      < 95.0%           -> 50%
    """
    if monthly_uptime_pct >= 99.9:
        return {
            "credit_pct": 0,
            "credit_amount": 0.0,
            "is_eligible": False,
            "governing_clause": "SLA Section 4",
            "explanation": "Uptime meets or exceeds 99.9% SLA target. No credit owed.",
        }
    elif monthly_uptime_pct >= 99.0:
        pct = 10
    elif monthly_uptime_pct >= 95.0:
        pct = 25
    else:
        pct = 50

    credit = (pct / 100) * monthly_fee
    return {
        "credit_pct": pct,
        "credit_amount": round(credit, 2),
        "is_eligible": True,
        "governing_clause": "SLA Section 4",
        "explanation": (
            f"{pct}% service credit applies for {monthly_uptime_pct:.2f}% uptime: "
            f"${credit:,.2f}"
        ),
    }
```

## Related Provisions
- Credit tiers: [Service Credit Remedies](/contracts/sla/clauses/service_credits.md)
- Uptime measurement: [Uptime Commitment](/contracts/sla/clauses/uptime_commitment.md)
- Credit definition: [Service Credits](/definitions/service_credits.md)
- Force majeure exclusion: [Force Majeure Clause](/contracts/msa/clauses/force_majeure.md)
