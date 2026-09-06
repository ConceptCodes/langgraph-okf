from typing import Any, NotRequired, TypedDict


class ConceptDetail(TypedDict, total=False):
    concept_id: str
    type: str
    title: str
    description: str
    trust_tier: str
    is_stale: bool
    status: str
    body: str
    links: list[dict[str, str]]
    trust_advisories: list[str]


class ModelUsage(TypedDict):
    phase: NotRequired[str]
    model: str
    status: str
    elapsed_seconds: float
    input_tokens: int | None
    output_tokens: int | None
    total_tokens: int | None
    cost_usd: float | None


class LegalDiscoveryState(TypedDict, total=False):
    query: str
    # Progressive disclosure state
    active_directories: list[str]
    target_concept_ids: list[str]
    # Inspection and link traversal state
    inspected_concepts: dict[str, ConceptDetail]
    expansion_queue: list[str]
    visited_concept_ids: list[str]
    # Computation and verification state
    computation_results: list[dict[str, Any]]
    trust_advisories: list[str]
    traversal_log: list[str]
    # Output
    final_response: str
    model_usage: ModelUsage
    model_calls: list[ModelUsage]
    iteration: int
    expansion_depth: int
