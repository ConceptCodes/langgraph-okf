import logging
from pathlib import PurePosixPath
from typing import Any

from langgraph.runtime import Runtime

from langgraph_okf.agent.context import Context
from langgraph_okf.agent.state import ConceptDetail, LegalDiscoveryState
from langgraph_okf.models import TrustTier

logger = logging.getLogger(__name__)


def inspect_concepts_node(state: LegalDiscoveryState, runtime: Runtime[Context]) -> dict[str, Any]:
    """
    Inspection node: Loads targeted concepts from disk, validates trust tiers,
    extracts operative body text, and harvests relational outbound links.
    """
    target_ids = state.get("target_concept_ids", [])
    inspected = dict(state.get("inspected_concepts", {}))
    visited = list(state.get("visited_concept_ids", []))
    expansion_queue = list(state.get("expansion_queue", []))
    trust_advisories = list(state.get("trust_advisories", []))
    traversal_log = list(state.get("traversal_log", []))

    bundle = runtime.context.bundle

    for cid in target_ids:
        if cid in visited:
            continue

        try:
            if PurePosixPath(cid).name in ("index", "index.md"):
                listing = bundle.read_index(str(PurePosixPath(cid).parent))
                visited.append(cid)
                expansion_queue.extend(item.concept_id for item in listing.items if item.concept_id not in visited)
                expansion_queue.extend(str(PurePosixPath(listing.directory) / subdir / "index") for subdir in listing.subdirectories)
                traversal_log.append(f"[Inspect] Followed directory index '{cid}' as navigation, not concept evidence.")
                continue
            if PurePosixPath(cid).name in ("log", "log.md"):
                visited.append(cid)
                continue
            concept = bundle.get_concept(cid)
            visited.append(concept.concept_id)

            # Record trust advisories if any
            if concept.trust_advisories:
                trust_advisories.extend(concept.trust_advisories)
                for adv in concept.trust_advisories:
                    traversal_log.append(f"[Trust Advisory] {adv}")

            if not concept.trust_tier.meets(TrustTier(runtime.context.min_trust_tier)) or (
                runtime.context.strict_validation and concept.is_stale
            ):
                advisory = f"Excluded '{concept.concept_id}' by configured trust/freshness policy."
                trust_advisories.append(advisory)
                traversal_log.append(f"[Trust Advisory] {advisory}")
                continue

            # Harvest outbound links for graph expansion
            extracted_links: list[dict[str, str]] = []
            for link in concept.links:
                target_ref = link.resolved_concept_id or link.target
                extracted_links.append({"text": link.text, "target": target_ref})
                if (
                    link.resolved_concept_id
                    and link.resolved_concept_id not in visited
                    and link.resolved_concept_id not in expansion_queue
                ):
                    expansion_queue.append(link.resolved_concept_id)

            detail: ConceptDetail = {
                "concept_id": concept.concept_id,
                "type": concept.type,
                "title": concept.title,
                "description": concept.description,
                "trust_tier": concept.trust_tier.value,
                "is_stale": concept.is_stale,
                "status": concept.frontmatter.status,
                "body": concept.body,
                "links": extracted_links,
                "trust_advisories": concept.trust_advisories,
            }
            inspected[concept.concept_id] = detail

            traversal_log.append(
                f"[Inspect] Loaded '{concept.concept_id}' | Type: {concept.type} | "
                f"Trust: {concept.trust_tier.value} | Outbound Links: {len(extracted_links)}"
            )

        except Exception as e:
            logger.warning(f"Error inspecting concept {cid}: {e}")
            traversal_log.append(f"[Inspect Error] Failed to load {cid}: {e}")

    return {
        "inspected_concepts": inspected,
        "visited_concept_ids": visited,
        "expansion_queue": expansion_queue,
        "trust_advisories": trust_advisories,
        "traversal_log": traversal_log,
        "iteration": state.get("iteration", 0) + 1,
    }
