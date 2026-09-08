import logging
from typing import Any

from langgraph.runtime import Runtime

from langgraph_okf.agent.context import Context
from langgraph_okf.agent.reasoning import select_candidates
from langgraph_okf.agent.state import LegalDiscoveryState

logger = logging.getLogger(__name__)


def plan_traversal_node(state: LegalDiscoveryState, runtime: Runtime[Context]) -> dict[str, Any]:
    """
    Planning node: Evaluates the user's legal inquiry against the root OKF index.
    Selects top-level subdirectories to explore using progressive disclosure.
    """
    if runtime.context is None:
        raise ValueError("Pass Context(bundle=...) to graph.invoke(..., context=context).")
    query = state.get("query", "").strip()
    bundle = runtime.context.bundle
    root_index = bundle.read_index("")

    subdirectories = root_index.subdirectories
    traversal_log = list(state.get("traversal_log", []))
    traversal_log.append(
        f"[Plan] Consulted root index '{root_index.title}'. Available sections: {subdirectories}"
    )

    # Determine relevant subdirectories based on legal keywords and semantic intent
    q_lower = query.lower()
    selected_dirs: list[str] = []

    # Map inquiry focus to OKF bundle sections
    if any(k in q_lower for k in ("liability", "cap", "limit", "damage", "consequential", "indemn")):
        selected_dirs.extend(["contracts/msa", "contracts/dpa", "computations", "definitions"])
    if any(k in q_lower for k in ("terminat", "cure", "convenience", "insolven", "bankrupt")):
        selected_dirs.extend(["contracts/msa", "computations", "definitions"])
    if any(k in q_lower for k in ("breach", "incident", "security", "dpa", "gdpr", "privacy", "retention", "sub-processor")):
        selected_dirs.extend(["contracts/dpa", "contracts/msa", "definitions"])
    if any(k in q_lower for k in ("sla", "uptime", "credit", "availability", "downtime")):
        selected_dirs.extend(["contracts/sla", "contracts/msa", "computations", "definitions"])
    if any(k in q_lower for k in ("confidential", "proprietary", "trade secret", "disclosure")):
        selected_dirs.extend(["contracts/msa", "definitions"])
    if any(k in q_lower for k in ("dispute", "arbitrat", "mediat", "warrant", "disclaimer", "force majeure", "ip", "intellectual property")):
        selected_dirs.extend(["contracts/msa", "definitions"])
    if not selected_dirs:
        # Default progressive disclosure fallback: start with primary contracts & definitions
        selected_dirs = ["contracts/msa", "definitions"]

    # Filter to only existing subdirectories in the bundle
    matched = [d for d in subdirectories if any(d == s or d.startswith(s) or s.startswith(d) for s in selected_dirs)]
    if not matched:
        matched = subdirectories

    calls = list(state.get("model_calls", []))
    if runtime.context.llm is not None and subdirectories:
        # Build candidates from the already-loaded root index to avoid re-reading
        # every child directory index just to get their titles.
        candidates = {
            item.path.rstrip("/"): f"{item.title} — {item.description}".strip(" —")
            for item in root_index.items
            if item.path.rstrip("/") in subdirectories
        }
        # Fall back to bare directory names for any subdirectories not listed in root index items
        for d in subdirectories:
            if d not in candidates:
                candidates[d] = d
        selected, usage, reason = select_candidates(runtime.context.llm, query, candidates, "plan")
        calls.append(usage)
        if selected:
            matched = selected
        traversal_log.append(f"[Plan LLM] {reason}; {'selected ' + str(selected) if selected else 'using deterministic fallback'}")

    traversal_log.append(f"[Plan] Progressive disclosure directed agent to sections: {matched}")

    return {
        "model_calls": calls,
        "active_directories": matched,
        "target_concept_ids": [item.concept_id for item in root_index.items],
        "traversal_log": traversal_log,
        "iteration": state.get("iteration", 0) + 1,
    }
