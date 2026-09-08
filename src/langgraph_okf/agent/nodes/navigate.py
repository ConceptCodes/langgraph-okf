import logging
from collections import deque
from pathlib import PurePosixPath
from typing import Any

from langgraph.runtime import Runtime

from langgraph_okf.agent.context import Context
from langgraph_okf.agent.reasoning import select_candidates
from langgraph_okf.agent.state import LegalDiscoveryState

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Legal topic relevance rules
# Each entry is (query_keywords, item_keywords): a concept is relevant if the
# query contains ANY query keyword AND the item text contains ANY item keyword.
# Keeping this as a module-level table makes legal/product review straightforward.
# ---------------------------------------------------------------------------
_LEGAL_TOPIC_RULES: list[tuple[frozenset[str], frozenset[str]]] = [
    (frozenset({"liabilit", "cap"}),                 frozenset({"liability", "fee", "supercap"})),
    (frozenset({"terminat", "cancel"}),               frozenset({"terminat", "breach", "notice"})),
    (frozenset({"breach", "data", "security"}),       frozenset({"breach", "incident", "supercap", "retention", "sub-processor"})),
    (frozenset({"confidential", "secret"}),           frozenset({"confidential"})),
    (frozenset({"sla", "uptime", "downtime", "credit"}), frozenset({"sla", "uptime", "credit", "remed"})),
    (frozenset({"indemnif", "infring"}),              frozenset({"indemnif", "infring", "intellectual", "ip"})),
    (frozenset({"dispute", "arbitrat", "mediat"}),    frozenset({"dispute", "arbitrat", "mediat"})),
    (frozenset({"warrant", "disclaimer", "as is"}),   frozenset({"warrant", "disclaimer"})),
    (frozenset({"force majeure", "act of god"}),      frozenset({"force majeure", "excused"})),
]


def _is_topic_relevant(query: str, item_text: str) -> bool:
    """Return True if the query+item pair matches any registered legal topic rule."""
    return any(
        any(qk in query for qk in query_keys) and any(ik in item_text for ik in item_keys)
        for query_keys, item_keys in _LEGAL_TOPIC_RULES
    )


def navigate_index_node(state: LegalDiscoveryState, runtime: Runtime[Context]) -> dict[str, Any]:
    """
    Navigation node: Performs progressive disclosure by reading directory-level index.md files.
    Identifies target concept documents to inspect without loading full document bodies.
    """
    query = state.get("query", "").lower()
    active_dirs = state.get("active_directories", [])
    traversal_log = list(state.get("traversal_log", []))
    target_concepts: list[str] = list(state.get("target_concept_ids", []))

    bundle = runtime.context.bundle

    pending = deque(active_dirs)
    visited_dirs: set[str] = set()
    fallback_ids: list[str] = []
    candidates = {}
    while pending:
        dir_path = pending.popleft()
        index_listing = bundle.read_index(dir_path)
        if index_listing.directory in visited_dirs:
            continue
        visited_dirs.add(index_listing.directory)
        for subdir in index_listing.subdirectories:
            pending.append(str(PurePosixPath(index_listing.directory) / subdir))
        if index_listing.items:
            fallback_ids.append(index_listing.items[0].concept_id)
        traversal_log.append(
            f"[Navigate] Read index for '{dir_path}': discovered {len(index_listing.items)} concepts, "
            f"{len(index_listing.subdirectories)} subdirs."
        )

        for item in index_listing.items:
            cid = item.concept_id
            candidates[cid] = {"title": item.title, "description": item.description}
            item_text = f"{item.title} {item.description} {cid}".lower()

            # Pure OKF heuristic navigation matching query terms against index metadata
            relevance_keywords = [word for word in query.split() if len(word) > 3]
            is_relevant = any(kw in item_text for kw in relevance_keywords)

            # Special legal topic associations — table-driven for auditability
            if _is_topic_relevant(query, item_text):
                is_relevant = True

            if is_relevant and cid not in target_concepts:
                target_concepts.append(cid)
                traversal_log.append(f"[Navigate] Queued concept '{cid}' ({item.title}) based on index metadata.")

    # If no specific concept was selected, pick the primary overview in the active directories
    if not target_concepts:
        target_concepts = list(dict.fromkeys(fallback_ids))

    calls = list(state.get("model_calls", []))
    if runtime.context.llm is not None and candidates:
        selected, usage, reason = select_candidates(runtime.context.llm, query, candidates, "navigate")
        calls.append(usage)
        if selected:
            target_concepts = list(dict.fromkeys([*state.get("target_concept_ids", []), *selected]))
        traversal_log.append(f"[Navigate LLM] {reason}; {'selected ' + str(selected) if selected else 'using deterministic fallback'}")

    return {
        "model_calls": calls,
        "target_concept_ids": target_concepts,
        "traversal_log": traversal_log,
        "iteration": state.get("iteration", 0) + 1,
    }
