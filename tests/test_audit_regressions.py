from dataclasses import replace
from datetime import UTC, datetime

import pytest
from langgraph.runtime import Runtime

from langgraph_okf.agent.context import Context
from langgraph_okf.agent.graph import build_legal_discovery_graph
from langgraph_okf.agent.nodes.expand import expand_links_node
from langgraph_okf.agent.tools import execute_attested_computation
from langgraph_okf.bundle import OKFBundle
from langgraph_okf.models import TrustTier
from langgraph_okf.parser import parse_concept_content, parse_concept_file
from langgraph_okf.settings import Settings
from langgraph_okf.trust import enrich_concept_trust


@pytest.fixture
def sample(context):
    return context.bundle


def test_bundle_blocks_path_and_symlink_escape(tmp_path):
    root = tmp_path / "bundle"
    root.mkdir()
    (tmp_path / "outside.md").write_text("private")
    (root / "escape.md").symlink_to(tmp_path / "outside.md")
    (root / "escape_dir").symlink_to(tmp_path, target_is_directory=True)
    bundle = OKFBundle(root)
    for target in ("../outside", "escape", "/../outside"):
        with pytest.raises(ValueError, match="escapes"):
            bundle.get_concept(target)
    with pytest.raises(ValueError, match="escapes"):
        bundle.read_index("../")
    with pytest.raises(ValueError, match="escapes"):
        bundle.read_index("escape_dir")
    assert bundle.resolve_link("test", "/../outside.md") is None
    assert bundle.resolve_link("test", "/escape.md") is None
    assert bundle.resolve_link("test", "file:///etc/passwd") is None
    assert bundle.list_all_concept_ids() == []


def test_bundle_root_must_be_directory(tmp_path):
    file = tmp_path / "file.md"
    file.write_text("test")
    with pytest.raises(FileNotFoundError):
        OKFBundle(file)


def test_reads_do_not_return_stale_cached_content(tmp_path):
    file = tmp_path / "test.md"
    file.write_text("---\ntype: Concept\n---\nold")
    bundle = OKFBundle(tmp_path)
    assert bundle.get_concept("test").body == "old"
    file.write_text("---\ntype: Concept\n---\nnew")
    assert bundle.get_concept("./test.md").body == "new"


def test_index_normalizes_paths_and_reads_descriptions(tmp_path):
    folder = tmp_path / "nested"
    folder.mkdir()
    (folder / "index.md").write_text("# Nested\n- [Shared](../shared.md#part) - shared metadata\n- [Root](/index.md)\n- [Unsafe](../../outside.md)\n")
    listing = OKFBundle(tmp_path).read_index("nested")
    assert listing.title == "Nested"
    assert [item.concept_id for item in listing.items] == ["shared"]
    assert listing.items[0].description == "shared metadata"
    assert listing.subdirectories == [".."]


def test_nested_navigation_and_index_cycle(tmp_path, monkeypatch):
    (tmp_path / "nested").mkdir()
    (tmp_path / "index.md").write_text("# Root\n[Branch](nested/index.md)")
    (tmp_path / "nested/index.md").write_text("# Branch\n[Root](/index.md)\n[Widget](widget.md)")
    (tmp_path / "nested/widget.md").write_text("---\ntype: Concept\n---\nWidget evidence")
    context = Context(bundle=OKFBundle(tmp_path))
    result = build_legal_discovery_graph().invoke({"query": "What is a widget?"}, context=context, config=context.invocation_config)
    assert "nested/widget" in result["inspected_concepts"]
    assert "Widget evidence" in result["final_response"]


def test_invalid_optional_metadata_preserves_lifecycle_and_dates(tmp_path):
    concept = parse_concept_content("---\ntype: Clause\nstatus: deprecated\nstale_after: 2026-01-01\ntags: 42\n---\nbody", tmp_path / "x.md", tmp_path)
    enrich_concept_trust(concept, datetime(2026, 1, 1))
    assert concept.frontmatter.status == "deprecated"
    assert concept.is_stale
    assert len(concept.trust_advisories) == 2


@pytest.mark.parametrize("verified,expected", [
    ("[{by: process:check}, {by: 'human:alice'}]", TrustTier.HUMAN_REVIEWED),
    ("{by: null}", TrustTier.UNVERIFIED),
    ("{by: 'human:'}", TrustTier.UNVERIFIED),
    ("{by: 'attorney:alice'}", TrustTier.MACHINE_CONFIRMED),
])
def test_verification_shapes(tmp_path, verified, expected):
    concept = parse_concept_content(f"---\ntype: Concept\nverified: {verified}\n---\nbody", tmp_path / "x.md", tmp_path)
    assert enrich_concept_trust(concept).trust_tier == expected
    assert concept.frontmatter.status == "stable"


def test_missing_file_is_not_a_successful_empty_concept(tmp_path):
    with pytest.raises(FileNotFoundError):
        parse_concept_file(tmp_path / "missing.md", tmp_path)


@pytest.mark.parametrize("fees", [-1, float("inf"), float("nan")])
def test_invalid_calculation_inputs(sample, fees):
    with pytest.raises(ValueError):
        execute_attested_computation(sample.get_concept("computations/liability_cap"), {"fees_last_12_months": fees})


def test_unknown_computation_and_scenarios_rejected(sample):
    concept = sample.get_concept("computations/liability_cap")
    with pytest.raises(ValueError):
        execute_attested_computation(concept, {"claim_type": "typo"})
    concept.concept_id = "other/liability_cap"
    with pytest.raises(ValueError, match="Unsupported"):
        execute_attested_computation(concept, {"fees_last_12_months": 1})
    with pytest.raises(ValueError, match="Unknown termination"):
        execute_attested_computation(sample.get_concept("computations/termination_notice"), {"termination_reason": "typo"})


@pytest.mark.parametrize("amount", ["", "$100k", "$100 and $200", "$-100"])
def test_query_does_not_invent_fee_input(amount, context):
    result = build_legal_discovery_graph().invoke({"query": f"What is the liability cap with {amount} in fees?"}, context=context, config=context.invocation_config)
    assert result["computation_results"] == []
    assert result["trust_advisories"]


def test_query_preserves_decimal_fees(context):
    result = build_legal_discovery_graph().invoke({"query": "What is the standard liability cap with $1,234.56 in fees?"}, context=context, config=context.invocation_config)
    assert result["computation_results"][0]["cap_amount"] == 1234.56
    assert result["computation_results"][0]["attestation_verified"] is False


def test_multiple_termination_scenarios(context):
    result = build_legal_discovery_graph().invoke({"query": "What notice is needed to terminate for insolvency and material breach?"}, context=context, config=context.invocation_config)
    assert {c["reason"] for c in result["computation_results"]} == {"insolvency", "material_breach"}


def test_trust_policy_applies_to_computations(context):
    context = replace(context, min_trust_tier=TrustTier.HUMAN_REVIEWED)
    result = build_legal_discovery_graph().invoke({"query": "What is the liability cap with $100 in fees?"}, context=context, config=context.invocation_config)
    assert "computations/liability_cap" not in result["inspected_concepts"]
    assert not result["computation_results"]


def test_strict_freshness_policy(tmp_path, monkeypatch):
    (tmp_path / "old.md").write_text("---\ntype: Concept\nstatus: deprecated\n---\nOld evidence")
    context = Context(bundle=OKFBundle(tmp_path))
    context = replace(context, strict_validation=True)
    result = build_legal_discovery_graph().invoke({"query": "old"}, context=context, config=context.invocation_config)
    assert not result["inspected_concepts"]
    assert any("Excluded" in a for a in result["trust_advisories"])


def test_link_hop_limit_is_independent_of_node_iterations(context):
    runtime = Runtime(context=replace(context, max_traversal_depth=1))
    state = {"expansion_queue": ["a"], "iteration": 100, "expansion_depth": 0}
    result = expand_links_node(state, runtime)
    assert result["target_concept_ids"] == ["a"]
    state["expansion_depth"] = 1
    assert expand_links_node(state, runtime)["target_concept_ids"] == []


def test_configuration_validation():
    with pytest.raises(ValueError):
        Settings(_env_file=None, min_trust_tier="typo")
    with pytest.raises(ValueError):
        Settings(_env_file=None, max_traversal_depth=-1)


def test_sample_links_resolve(sample):
    for cid in sample.list_all_concept_ids():
        for link in sample.get_concept(cid).links:
            assert link.resolved_concept_id is not None, (cid, link.target)


def test_stale_at_exact_boundary(tmp_path):
    concept = parse_concept_content("---\ntype: Concept\nstale_after: 2026-01-01T00:00:00Z\n---\nbody", tmp_path / "x.md", tmp_path)
    assert enrich_concept_trust(concept, datetime(2026, 1, 1, tzinfo=UTC)).is_stale


def test_reserved_indexes_are_not_evidence(context):
    result = build_legal_discovery_graph().invoke({"query": "What is the liability cap?"}, context=context, config=context.invocation_config)
    assert all(not cid.endswith("/index") for cid in result["inspected_concepts"])


def test_top_level_computation_contract(tmp_path):
    concept = parse_concept_content("---\ntype: Attested Computation\nruntime: python\ncomputation: /references/calc.py\nexecutor: {resource: /references/run.md}\nparameters: [{name: fees, type: number, required: true}]\nverified: [{by: 'human:alice'}]\n---\nbody", tmp_path / "x.md", tmp_path)
    assert concept.frontmatter.computation == "/references/calc.py"
    assert concept.frontmatter.runtime == "python"
    assert enrich_concept_trust(concept).trust_tier == TrustTier.HUMAN_REVIEWED
