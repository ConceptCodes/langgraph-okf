import math
from typing import Any

from langgraph_okf.models import AttestationSpec, Concept


def execute_attested_computation(concept: Concept, params: dict[str, Any]) -> dict[str, Any]:
    """
    Execute a sanctioned Attested Computation concept.
    In OKF v0.2, Attested Computations represent deterministic formulas (e.g. liability caps,
    statutory notice windows) that can be verified and evaluated without LLM hallucination.
    """
    if concept.type != "Attested Computation":
        raise ValueError(f"Concept '{concept.concept_id}' is not an Attested Computation.")

    cid = concept.concept_id

    executors = {
        "computations/liability_cap": "liability_calc_v1",
        "computations/termination_notice": "notice_period_calc_v1",
    }
    spec = concept.frontmatter.computation
    executor = concept.frontmatter.executor
    if executor is None and isinstance(spec, AttestationSpec):
        executor = spec.executor
    if cid not in executors or not executor or executor.get("name") != executors[cid]:
        raise ValueError(f"Unsupported computation or executor: {cid}")
    if concept.is_stale:
        raise ValueError(f"Cannot execute stale computation: {cid}")

    if cid == "computations/liability_cap":
        claim_type = str(params.get("claim_type", "standard")).lower()
        allowed = {"standard", "data_breach", "dpa", "gdpr", "uncapped", "confidentiality", "willful_misconduct", "fraud", "gross_negligence", "unpaid_fees"}
        if claim_type not in allowed:
            raise ValueError(f"Unknown claim type: {claim_type}")

        if claim_type in ("uncapped", "confidentiality", "willful_misconduct", "fraud", "gross_negligence", "unpaid_fees"):
            return {
                "computation_id": cid,
                "claim_type": claim_type,
                "cap_amount": None,
                "is_unlimited": True,
                "governing_clause": "MSA Section 11.3",
                "explanation": "Uncapped claim: No aggregate limitation of liability applies.",
            }
        fees = float(params["fees_last_12_months"])
        if not math.isfinite(fees) or fees < 0 or not math.isfinite(2 * fees):
            raise ValueError("Fees must be finite, nonnegative, and within numeric range.")
        if claim_type in ("data_breach", "dpa", "gdpr"):
            cap = 2.0 * fees
            return {
                "computation_id": cid,
                "claim_type": claim_type,
                "multiplier": 2.0,
                "cap_amount": cap,
                "is_unlimited": False,
                "governing_clause": "DPA Section 10.1 (Precedence over MSA 11.2)",
                "explanation": f"Data protection 2x supercap applies: ${cap:,.2f}",
            }
        else:
            cap = 1.0 * fees
            return {
                "computation_id": cid,
                "claim_type": "standard",
                "multiplier": 1.0,
                "cap_amount": cap,
                "is_unlimited": False,
                "governing_clause": "MSA Section 11.2",
                "explanation": f"Standard aggregate cap of 1x fees applies: ${cap:,.2f}",
            }

    elif cid == "computations/termination_notice":
        reason = str(params["termination_reason"]).lower()
        if reason not in {"convenience", "insolvency", "bankruptcy", "material_breach"}:
            raise ValueError(f"Unknown termination reason: {reason}")

        if "convenience" in reason:
            return {
                "computation_id": cid,
                "reason": "convenience",
                "required_advance_notice_days": 60,
                "cure_period_days": 0,
                "immediate": False,
                "governing_clause": "MSA Section 14.3",
                "explanation": "60 days advance written notice required + full payment of remaining committed fees.",
            }
        elif "insolvency" in reason or "bankruptcy" in reason:
            return {
                "computation_id": cid,
                "reason": "insolvency",
                "required_advance_notice_days": 0,
                "cure_period_days": 0,
                "immediate": True,
                "governing_clause": "MSA Section 14.2(2)",
                "explanation": "Immediate termination by written notice upon an insolvency or bankruptcy proceeding; no cure period.",
            }
        else:  # material breach
            return {
                "computation_id": cid,
                "reason": "material_breach",
                "required_advance_notice_days": 30,
                "cure_period_days": 30,
                "immediate": False,
                "governing_clause": "MSA Section 14.2(1)",
                "explanation": "Termination requires a breach remaining uncured for 30 days after receipt of written notice.",
            }

    raise ValueError(f"Unsupported computation: {cid}")
