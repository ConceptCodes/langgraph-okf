import re
from typing import Any

from langgraph.runtime import Runtime

from langgraph_okf.agent.context import Context
from langgraph_okf.agent.state import LegalDiscoveryState
from langgraph_okf.agent.tools import CLAIM_TYPE_KEYWORDS, execute_attested_computation


def compute_node(state: LegalDiscoveryState, runtime: Runtime[Context]) -> dict[str, Any]:
    """Evaluate only inspected rules, with explicit inputs and visible assumptions."""
    inspected = state.get("inspected_concepts", {})
    query = state.get("query", "").lower()
    log = list(state.get("traversal_log", []))
    advisories = list(state.get("trust_advisories", []))
    results: list[dict[str, Any]] = []
    bundle = runtime.context.bundle
    jobs: list[tuple[str, dict[str, Any]]] = []
    liability_id = "computations/liability_cap"
    notice_id = "computations/termination_notice"
    sla_credit_id = "computations/sla_credit"

    if liability_id in inspected and any(k in query for k in ("liability", "cap", "exposure")):
        amounts = re.findall(r"\$\s*(-?(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?)(?![\d.,])", query)
        if len(amounts) != 1 or re.search(r"\d\s*(?:k|m|million|thousand)\b", query):
            advisories.append("Liability calculation requires one explicit dollar amount for the applicable 12-month fees; no default amount was assumed.")
        else:
            fees = float(amounts[0].replace(",", ""))
            claims = []
            # Derive applicable claim types from shared CLAIM_TYPE_KEYWORDS vocabulary
            for claim_type, keywords in CLAIM_TYPE_KEYWORDS.items():
                if any(k in query for k in keywords):
                    claims.append(claim_type)
            if not claims or any(k in query for k in ("standard", "general", "msa", "exceptions", "under the contract")):
                claims.insert(0, "standard")
            for claim in claims:
                jobs.append((liability_id, {"fees_last_12_months": fees, "claim_type": claim}))
            advisories.append("Calculation scenarios use the supplied amount as the applicable 12-month fee base: paid or payable for the MSA, paid for the DPA. Claim classification is keyword-based; overlapping exclusions require review.")

    if notice_id in inspected and any(k in query for k in ("terminat", "cure", "notice", "insolven", "bankrupt")):
        reasons = []
        if "convenience" in query:
            reasons.append("convenience")
        if "insolven" in query or "bankrupt" in query:
            reasons.append("insolvency")
        if "material breach" in query or "cure" in query:
            reasons.append("material_breach")
        if not reasons:
            advisories.append("Notice calculation requires a termination reason (convenience, material breach, or insolvency).")
        for reason in reasons:
            jobs.append((notice_id, {"termination_reason": reason}))

    if sla_credit_id in inspected and any(k in query for k in ("sla", "uptime", "downtime", "credit")):
        amounts = re.findall(r"\$\s*(-?(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?)(?![\d.,])", query)
        uptimes = re.findall(r"(\d+(?:\.\d+)?)\s*%", query)
        if len(amounts) != 1 or re.search(r"\d\s*(?:k|m|million|thousand)\b", query) or len(uptimes) != 1:
            advisories.append("SLA credit calculation requires one explicit monthly fee dollar amount and one explicit monthly uptime percentage.")
        else:
            monthly_fee = float(amounts[0].replace(",", ""))
            uptime_pct = float(uptimes[0])
            jobs.append((sla_credit_id, {"monthly_fee": monthly_fee, "monthly_uptime_pct": uptime_pct}))
            advisories.append("SLA credit calculation assumes standard Monthly Uptime Percentage under SLA Section 4 without force majeure exclusions.")

    for cid, params in jobs:
        try:
            result = execute_attested_computation(bundle.get_concept(cid), params)
            result["inputs"] = params
            result["attestation_verified"] = False
            results.append(result)
            log.append(f"[Compute] Evaluated '{cid}' with {params}: {result['explanation']}")
        except (ValueError, KeyError, OSError) as exc:
            advisory = f"Computation '{cid}' was not executed: {exc}"
            advisories.append(advisory)
            log.append(f"[Compute Warning] {advisory}")

    return {
        "computation_results": results,
        "trust_advisories": advisories,
        "traversal_log": log,
        "iteration": state.get("iteration", 0) + 1,
    }
