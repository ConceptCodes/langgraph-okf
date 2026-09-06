from typing import Literal

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from langgraph_okf.agent.context import Context
from langgraph_okf.agent.nodes.compute import compute_node
from langgraph_okf.agent.nodes.expand import expand_links_node
from langgraph_okf.agent.nodes.inspect import inspect_concepts_node
from langgraph_okf.agent.nodes.navigate import navigate_index_node
from langgraph_okf.agent.nodes.plan import plan_traversal_node
from langgraph_okf.agent.nodes.synthesize import synthesize_opinion_node
from langgraph_okf.agent.state import LegalDiscoveryState


def should_continue_expansion(state: LegalDiscoveryState) -> Literal["inspect", "compute"]:
    """
    Conditional routing: If expand_links_node found more concept targets to inspect,
    loop back to inspect_concepts_node; otherwise proceed to deterministic computation.
    """
    targets = state.get("target_concept_ids", [])
    if targets:
        return "inspect"
    return "compute"


def build_legal_discovery_graph() -> CompiledStateGraph:
    """
    Compile the OKF Legal Discovery StateGraph.
    Pure OKF traversal: progressive disclosure -> inspection -> relational link expansion -> attested computation -> synthesis.
    """
    builder = StateGraph(LegalDiscoveryState, context_schema=Context)

    builder.add_node("plan", plan_traversal_node)
    builder.add_node("navigate", navigate_index_node)
    builder.add_node("inspect", inspect_concepts_node)
    builder.add_node("expand", expand_links_node)
    builder.add_node("compute", compute_node)
    builder.add_node("synthesize", synthesize_opinion_node)

    # Define edges
    builder.add_edge(START, "plan")
    builder.add_edge("plan", "navigate")
    builder.add_edge("navigate", "inspect")
    builder.add_edge("inspect", "expand")
    builder.add_conditional_edges(
        "expand",
        should_continue_expansion,
        {
            "inspect": "inspect",
            "compute": "compute",
        },
    )
    builder.add_edge("compute", "synthesize")
    builder.add_edge("synthesize", END)

    return builder.compile()
