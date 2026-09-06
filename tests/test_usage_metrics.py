from dataclasses import replace
from io import StringIO
from unittest.mock import Mock

import pytest
from langchain_core.messages import AIMessage
from langgraph.runtime import Runtime
from rich.console import Console

from langgraph_okf import cli
from langgraph_okf.agent.nodes.synthesize import synthesize_opinion_node


@pytest.mark.parametrize("cost", [0.00123456, 0.0, None])
def test_reported_usage_and_cost(context, cost):
    llm = Mock(model_name="requested-model")
    llm.invoke.return_value = AIMessage(content="Answer", response_metadata={
        "model_name": "actual-model",
        "token_usage": {"prompt_tokens": 120, "completion_tokens": 30, "total_tokens": 150, "cost": cost},
    })
    usage = synthesize_opinion_node({"query": "test"}, Runtime(context=replace(context, llm=llm)))["model_usage"]
    assert usage["model"] == "actual-model"
    assert usage["input_tokens"] == 120
    assert usage["output_tokens"] == 30
    assert usage["total_tokens"] == 150
    assert usage["cost_usd"] == cost
    assert usage["elapsed_seconds"] >= 0


def test_normalized_tokens_without_price(context):
    llm = Mock(model_name="test-model")
    llm.invoke.return_value = AIMessage(content="Answer", usage_metadata={"input_tokens": 4, "output_tokens": 2, "total_tokens": 6})
    usage = synthesize_opinion_node({}, Runtime(context=replace(context, llm=llm)))["model_usage"]
    assert usage["total_tokens"] == 6
    assert usage["cost_usd"] is None


def test_failed_call_does_not_claim_zero_cost(context):
    llm = Mock(model_name="test-model")
    llm.invoke.side_effect = RuntimeError("Request failed")
    usage = synthesize_opinion_node({}, Runtime(context=replace(context, llm=llm)))["model_usage"]
    assert usage["status"] == "partial/failed"
    assert usage["total_tokens"] is None
    assert usage["cost_usd"] is None


def test_offline_metrics_and_cli_display(context, monkeypatch):
    usage = synthesize_opinion_node({}, Runtime(context=context))["model_usage"]
    assert usage["total_tokens"] == 0
    assert usage["cost_usd"] == 0
    output = StringIO()
    monkeypatch.setattr(cli, "console", Console(file=output, width=100, color_system=None))
    cli.print_run_metrics(usage, 1.25)
    assert "1.25s" in output.getvalue()
    assert "$0.00000000" in output.getvalue()
    usage["cost_usd"] = None
    cli.print_run_metrics(usage, 1.25)
    assert "Unavailable (not reported)" in output.getvalue()
