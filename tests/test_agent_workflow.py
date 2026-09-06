from langgraph_okf.agent.graph import build_legal_discovery_graph
from langgraph_okf.agent.state import LegalDiscoveryState


def test_liability_cap_discovery_and_computation(context) -> None:
    graph = build_legal_discovery_graph()
    initial_state: LegalDiscoveryState = {
        "query": "What is the liability cap under the contract, what exceptions apply, and how does a data breach affect it with $100,000 in fees?",
    }

    result = graph.invoke(initial_state, context=context, config=context.invocation_config)

    inspected = result.get("inspected_concepts", {})
    traversal_log = result.get("traversal_log", [])
    computations = result.get("computation_results", [])
    final_response = result.get("final_response", "")

    # 1. Check that progressive disclosure navigated into MSA & DPA
    assert any("[Plan]" in log for log in traversal_log)
    assert any("[Navigate]" in log for log in traversal_log)

    # 2. Check that key clauses were inspected
    assert "contracts/msa/clauses/limitation_of_liability" in inspected

    # 3. Check that relational links were followed via expand_links_node
    assert any("definitions/fees" in cid or "definitions/confidential_information" in cid for cid in inspected)
    assert "contracts/dpa/clauses/liability_supercap" in inspected or any("supercap" in cid for cid in inspected)

    # 4. Check that Attested Computation was evaluated deterministically
    assert len(computations) > 0
    liability_calc = next((c for c in computations if c.get("claim_type") == "data_breach"), None)
    assert liability_calc is not None
    assert liability_calc.get("multiplier") == 2.0 or liability_calc.get("cap_amount") == 200000.0

    # 5. Check that final response contains the grounded legal analysis
    assert len(final_response) > 100
    assert "Limitation of Liability" in final_response or "liability" in final_response.lower()


def test_termination_notice_discovery(context) -> None:
    graph = build_legal_discovery_graph()
    initial_state: LegalDiscoveryState = {
        "query": "Can a party terminate immediately for insolvency, and what cure period is required for a material breach?",
    }

    result = graph.invoke(initial_state, context=context, config=context.invocation_config)

    inspected = result.get("inspected_concepts", {})
    computations = result.get("computation_results", [])
    final_response = result.get("final_response", "")

    # Check that termination clause was inspected
    assert any("termination" in cid for cid in inspected)

    # Check that Attested Computation evaluated notice & cure
    assert len(computations) > 0
    notice_calc = next((c for c in computations if "termination_notice" in c.get("computation_id", "")), None)
    assert notice_calc is not None
    assert notice_calc.get("immediate") is True or notice_calc.get("cure_period_days") == 30
    assert len(final_response) > 50
