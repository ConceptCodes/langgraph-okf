from pathlib import Path

import pytest

from langgraph_okf.bundle import OKFBundle
from langgraph_okf.models import TrustTier


@pytest.fixture
def legal_bundle() -> OKFBundle:
    bundle_path = Path(__file__).parent.parent / "bundles" / "legal_sample"
    return OKFBundle(bundle_path)


def test_root_index_progressive_disclosure(legal_bundle: OKFBundle) -> None:
    root_index = legal_bundle.read_index("")
    assert root_index.title == "Enterprise Legal Knowledge Bundle"
    assert len(root_index.subdirectories) > 0
    assert any("msa" in s for s in root_index.subdirectories)
    assert any("definitions" in s for s in root_index.subdirectories)


def test_sub_index_navigation(legal_bundle: OKFBundle) -> None:
    msa_index = legal_bundle.read_index("contracts/msa")
    assert len(msa_index.items) > 0
    concept_ids = [item.concept_id for item in msa_index.items]
    assert any("limitation_of_liability" in cid for cid in concept_ids)


def test_concept_loading_and_trust(legal_bundle: OKFBundle) -> None:
    concept = legal_bundle.get_concept("contracts/msa/clauses/limitation_of_liability")
    assert concept.type == "Clause"
    assert concept.trust_tier == TrustTier.HUMAN_REVIEWED
    assert not concept.is_stale
    assert len(concept.links) > 0

    # Test link resolution
    link_targets = [link.resolved_concept_id for link in concept.links if link.resolved_concept_id]
    assert "definitions/fees" in link_targets
    assert "contracts/msa/clauses/confidentiality" in link_targets
    assert "computations/liability_cap" in link_targets


def test_dpa_supercap_concept(legal_bundle: OKFBundle) -> None:
    dpa_cap = legal_bundle.get_concept("contracts/dpa/clauses/liability_supercap")
    assert dpa_cap.type == "Clause"
    assert "2X" in dpa_cap.body
    assert any(link.resolved_concept_id == "contracts/msa/clauses/limitation_of_liability" for link in dpa_cap.links)


def test_attested_computation_concept(legal_bundle: OKFBundle) -> None:
    comp = legal_bundle.get_concept("computations/liability_cap")
    assert comp.type == "Attested Computation"
    assert comp.frontmatter.runtime == "python"
    assert comp.frontmatter.executor is not None
    assert "def calculate_liability_cap" in comp.body
