---
type: Attested Computation
title: Liability Cap Computation Rule
description: Illustrative liability cap formulas for individual claim scenarios.
tags: [liability, computation, financial, attested]
generated: { by: "process:sample-bundle-audit", at: "2026-09-05T00:00:00Z" }
runtime: python
parameters:
  - { name: fees_last_12_months, type: number, required: true }
  - { name: claim_type, type: string, required: true }
executor:
  name: liability_calc_v1
  resource: /scope.md
  receipt: [computation_id, inputs, cap_amount, is_unlimited, governing_clause]
---

# Computation

Illustrative calculation for one claim scenario. Fees must be explicitly supplied,
finite, and nonnegative. Use paid-or-payable fees for standard claims and paid fees
for DPA claims. See [scope and unresolved overlaps](/scope.md). No independent
attester is implemented.

```python
def calculate_liability_cap(
    fees_last_12_months: float,
    claim_type: str,
) -> dict:
    """
    claim_type options:
    - 'standard': General breach of MSA
    - 'data_breach': Breach of DPA / Personal Data Compromise
    - 'uncapped': Confidentiality breach, willful misconduct, or fraud
    """
    if claim_type == "uncapped":
        return {
            "cap_amount": None,
            "is_unlimited": True,
            "governing_clause": "MSA Section 11.3",
            "explanation": "Uncapped claim: No aggregate cap applies."
        }
    elif claim_type == "data_breach":
        cap = 2.0 * fees_last_12_months
        return {
            "cap_amount": cap,
            "is_unlimited": False,
            "multiplier": 2.0,
            "governing_clause": "DPA Section 10.1",
            "explanation": f"Data protection supercap of 2x fees: ${cap:,.2f}"
        }
    elif claim_type == "standard":
        cap = 1.0 * fees_last_12_months
        return {
            "cap_amount": cap,
            "is_unlimited": False,
            "multiplier": 1.0,
            "governing_clause": "MSA Section 11.2",
            "explanation": f"Standard MSA aggregate cap of 1x fees: ${cap:,.2f}"
        }
    else:
        raise ValueError(f"Unknown claim type: {claim_type}")
```

## Related Provisions
- Standard Cap: [Limitation of Liability](/contracts/msa/clauses/limitation_of_liability.md)
- Supercap: [DPA Liability Supercap](/contracts/dpa/clauses/liability_supercap.md)
- Fees definition: [Fees](/definitions/fees.md)
