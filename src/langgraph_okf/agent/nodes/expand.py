import logging
from typing import Any

from langgraph.runtime import Runtime

from langgraph_okf.agent.context import Context
from langgraph_okf.agent.state import LegalDiscoveryState

logger = logging.getLogger(__name__)


def expand_links_node(state: LegalDiscoveryState, runtime: Runtime[Context]) -> dict[str, Any]:
    """
    Expansion node: Traverses the OKF knowledge graph along explicit relational edges
    (markdown links to definitions, carve-outs, addenda, and computations).
    """
    expansion_queue = list(state.get("expansion_queue", []))
    visited = list(state.get("visited_concept_ids", []))
    traversal_log = list(state.get("traversal_log", []))
    iteration = state.get("iteration", 0)

    # Filter queue to unvisited links
    next_batch = [cid for cid in expansion_queue if cid not in visited]

    depth = state.get("expansion_depth", 0)
    if next_batch and depth < runtime.context.max_traversal_depth:
        traversal_log.append(
            f"[Expand] Following relational links to {len(next_batch)} concepts: {next_batch}"
        )
        return {
            "target_concept_ids": next_batch,
            "expansion_queue": [],
            "traversal_log": traversal_log,
            "iteration": iteration + 1,
            "expansion_depth": depth + 1,
        }

    if next_batch:
        traversal_log.append(f"[Expand] Depth limit reached; {len(next_batch)} linked concepts remain uninspected.")
    else:
        traversal_log.append("[Expand] Relational link traversal complete. Proceeding to computation and synthesis.")
    return {
        "target_concept_ids": [],
        "expansion_queue": [],
        "traversal_log": traversal_log,
        "iteration": iteration + 1,
    }
