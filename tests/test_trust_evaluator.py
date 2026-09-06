from datetime import UTC, datetime
from pathlib import Path

from langgraph_okf.models import Concept, ConceptFrontmatter, TrustTier
from langgraph_okf.trust import enrich_concept_trust, evaluate_trust_tier


def test_trust_tier_inference(tmp_path: Path) -> None:
    # 1. Unverified: no verified field
    c1 = Concept(
        concept_id="c1",
        file_path=tmp_path / "c1.md",
        frontmatter=ConceptFrontmatter(type="Clause"),
        body="content",
    )
    assert evaluate_trust_tier(c1) == TrustTier.UNVERIFIED

    # 2. Machine-confirmed: verified by agent or process
    c2 = Concept(
        concept_id="c2",
        file_path=tmp_path / "c2.md",
        frontmatter=ConceptFrontmatter(
            type="Clause",
            verified={"by": "contract_analyzer/gemini-2.5-pro", "at": "2026-06-01T00:00:00Z"},
        ),
        body="content",
    )
    assert evaluate_trust_tier(c2) == TrustTier.MACHINE_CONFIRMED

    # 3. Human-reviewed: verified by human or attorney
    c3 = Concept(
        concept_id="c3",
        file_path=tmp_path / "c3.md",
        frontmatter=ConceptFrontmatter(
            type="Clause",
            verified={"by": "human:attorney_sarah", "at": "2026-06-01T00:00:00Z"},
        ),
        body="content",
    )
    assert evaluate_trust_tier(c3) == TrustTier.HUMAN_REVIEWED


def test_freshness_and_superseded_detection(tmp_path: Path) -> None:
    # Expired clause
    c = Concept(
        concept_id="expired_clause",
        file_path=tmp_path / "exp.md",
        frontmatter=ConceptFrontmatter(
            type="Clause",
            status="superseded",
            stale_after=datetime(2025, 1, 1, tzinfo=UTC),
        ),
        body="content",
    )
    enrich_concept_trust(c, current_time=datetime(2026, 6, 1, tzinfo=UTC))
    assert c.is_stale is True
    assert len(c.trust_advisories) == 2
    assert any("SUPERSEDED" in adv for adv in c.trust_advisories)
    assert any("expired" in adv for adv in c.trust_advisories)
