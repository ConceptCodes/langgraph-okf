from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace

import pytest
from langchain_core.language_models.fake_chat_models import FakeListChatModel

from langgraph_okf.agent.context import Context
from langgraph_okf.agent.graph import build_legal_discovery_graph
from langgraph_okf.bundle import OKFBundle
from langgraph_okf.models import TrustTier
from langgraph_okf.settings import Settings


def test_same_graph_concurrent_runs_have_isolated_dependencies(tmp_path):
    contexts = []
    for name in ("first", "second"):
        root = tmp_path / name
        root.mkdir()
        (root / f"{name}.md").write_text(f"---\ntype: Concept\n---\n{name} evidence")
        contexts.append(Context(bundle=OKFBundle(root), llm=FakeListChatModel(responses=[name])))
    graph = build_legal_discovery_graph()

    def invoke(context):
        return graph.invoke({"query": "evidence"}, context=context, config=context.invocation_config)

    with ThreadPoolExecutor(max_workers=2) as pool:
        first, second = list(pool.map(invoke, contexts))
    assert first["final_response"] == "first"
    assert second["final_response"] == "second"
    assert set(first["inspected_concepts"]) == {"first"}
    assert set(second["inspected_concepts"]) == {"second"}
    assert "bundle" not in first and "llm" not in first


def test_same_graph_uses_each_runs_policy(context):
    graph = build_legal_discovery_graph()
    query = {"query": "What is the liability cap with $100 in fees?"}
    strict = replace(context, min_trust_tier=TrustTier.HUMAN_REVIEWED)
    assert graph.invoke(query, context=context)["computation_results"]
    assert not graph.invoke(query, context=strict)["computation_results"]
    assert graph.invoke(query, context=context)["computation_results"]


def test_recursion_budget_follows_deep_context(tmp_path):
    (tmp_path / "index.md").write_text("# Root\n[Start](step0.md)")
    for index in range(15):
        link = f"[Next](step{index + 1}.md)" if index < 14 else "Finished"
        (tmp_path / f"step{index}.md").write_text(f"---\ntype: Concept\n---\n{link}")
    graph = build_legal_discovery_graph()
    context = Context(bundle=OKFBundle(tmp_path), max_traversal_depth=14)
    result = graph.invoke({"query": "start"}, context=context, config=context.invocation_config)
    assert len(result["inspected_concepts"]) == 15
    shallow = replace(context, max_traversal_depth=0)
    result = graph.invoke({"query": "start"}, context=shallow, config=shallow.invocation_config)
    assert set(result["inspected_concepts"]) == {"step0"}


def test_context_from_settings_snapshots_policy(context):
    config = Settings(_env_file=None, openrouter_api_key="", bundle_path=context.bundle.root_path,
                      max_traversal_depth=7, min_trust_tier="human-reviewed", strict_validation=True)
    created = Context.from_settings(config)
    config.max_traversal_depth = 1
    assert created.bundle.root_path == context.bundle.root_path
    assert created.llm is None
    assert created.max_traversal_depth == 7
    assert created.min_trust_tier == TrustTier.HUMAN_REVIEWED
    assert created.strict_validation


def test_missing_context_has_actionable_error():
    with pytest.raises(ValueError, match="Pass Context"):
        build_legal_discovery_graph().invoke({"query": "test"})


def test_invalid_context_policy(context):
    with pytest.raises(ValueError):
        replace(context, max_traversal_depth=-1)
    with pytest.raises(ValueError):
        replace(context, min_trust_tier="typo")
