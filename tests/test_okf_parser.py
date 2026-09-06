from pathlib import Path

from langgraph_okf.parser import parse_concept_content


def test_permissive_parsing_missing_type(tmp_path: Path) -> None:
    # OKF consumer spec: consumers MUST tolerate missing/unknown type
    content = """---
title: Clause Without Type
tags: [test]
custom_vendor_field: 42
---
# Body
This is a test clause.
"""
    file_path = tmp_path / "test.md"
    concept = parse_concept_content(content, file_path, tmp_path)
    assert concept.type == "Concept"
    assert concept.title == "Clause Without Type"
    assert concept.frontmatter.model_extra["custom_vendor_field"] == 42


def test_permissive_parsing_malformed_frontmatter(tmp_path: Path) -> None:
    # Malformed frontmatter should degrade gracefully, not throw
    content = """---
type: [unterminated list
title: broken
---
# Raw content
"""
    file_path = tmp_path / "broken.md"
    concept = parse_concept_content(content, file_path, tmp_path)
    assert concept.type == "Concept"
    assert "Raw content" in concept.body


def test_extract_markdown_links(tmp_path: Path) -> None:
    content = """---
type: Clause
title: Interlinked Clause
---
See [Confidentiality](../definitions/confidentiality.md) and [External](https://example.com).
Also refer to [Root Concept](/contracts/msa/summary.md).
"""
    file_path = tmp_path / "interlinked.md"
    concept = parse_concept_content(content, file_path, tmp_path)
    # External https link should be filtered out from internal concept graph links
    assert len(concept.links) == 2
    assert concept.links[0].text == "Confidentiality"
    assert concept.links[0].target == "../definitions/confidentiality.md"
    assert concept.links[1].text == "Root Concept"
    assert concept.links[1].target == "/contracts/msa/summary.md"
