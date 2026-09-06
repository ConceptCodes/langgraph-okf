import json
from dataclasses import replace

from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
from langchain_core.messages import AIMessage

from langgraph_okf.agent.context import Context
from langgraph_okf.agent.graph import build_legal_discovery_graph
from langgraph_okf.agent.reasoning import select_candidates
from langgraph_okf.bundle import OKFBundle


def message(content):
    return AIMessage(content=content, response_metadata={"model_name": "test-model", "token_usage": {
        "prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15, "cost": 0.001,
    }})


def choice(*ids):
    return message(json.dumps({"selected": ids, "reason": "Relevant to the question"}))


def test_semantic_selection_review_and_aggregated_usage(tmp_path):
    (tmp_path / "terms").mkdir()
    (tmp_path / "index.md").write_text("# Root\n[Terms](terms/index.md)")
    (tmp_path / "terms/index.md").write_text("# Terms\n[Unrelated](other.md)\n[Availability](uptime.md)")
    (tmp_path / "terms/other.md").write_text("---\ntype: Concept\n---\nUnrelated")
    (tmp_path / "terms/uptime.md").write_text("---\ntype: Clause\n---\nSee [remedy](remedy.md) and [irrelevant](other.md)")
    (tmp_path / "terms/remedy.md").write_text("---\ntype: Clause\n---\nService credits")
    llm = FakeMessagesListChatModel(responses=[choice("terms"), choice("terms/uptime"), choice("terms/remedy"), choice(), message("Grounded answer")])
    context = Context(bundle=OKFBundle(tmp_path), llm=llm)
    result = build_legal_discovery_graph().invoke({"query": "What happens if the platform goes dark?"}, context=context)
    assert set(result["inspected_concepts"]) == {"terms/uptime", "terms/remedy"}
    assert result["final_response"] == "Grounded answer"
    assert [c["phase"] for c in result["model_calls"]] == ["plan", "navigate", "review", "review", "synthesize"]
    assert result["model_usage"]["total_tokens"] == 75
    assert result["model_usage"]["cost_usd"] == 0.005


def test_invalid_selection_falls_back_without_loading_invented_path(context):
    llm = FakeMessagesListChatModel(responses=[choice("../../secret")])
    selected, usage, reason = select_candidates(llm, "test", {"allowed": "Allowed"}, "plan")
    assert selected is None
    assert "outside" in reason
    assert usage["total_tokens"] == 15


def test_malformed_selection_keeps_deterministic_workflow(context):
    llm = FakeMessagesListChatModel(responses=[message("not JSON")])
    context = replace(context, llm=llm, max_traversal_depth=1)
    result = build_legal_discovery_graph().invoke({"query": "liability cap with $100 in fees"}, context=context)
    assert "contracts/msa/clauses/limitation_of_liability" in result["inspected_concepts"]
    assert any("fallback" in entry for entry in result["traversal_log"])
    assert len(result["model_calls"]) <= context.max_traversal_depth + 3


def test_offline_mode_makes_no_model_calls(context):
    result = build_legal_discovery_graph().invoke({"query": "liability cap"}, context=context)
    assert result["model_calls"] == []
    assert result["model_usage"]["cost_usd"] == 0
