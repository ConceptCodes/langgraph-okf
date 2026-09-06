import logging
import os
import re
from pathlib import Path
from urllib.parse import unquote, urlsplit

import frontmatter
from pydantic import ValidationError

from langgraph_okf.models import (
    Concept,
    ConceptFrontmatter,
    ConceptLink,
    IndexItem,
    IndexListing,
)

logger = logging.getLogger(__name__)

# Regex for Markdown links: [text](target)
LINK_PATTERN = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")


def parse_concept_file(file_path: Path, bundle_root: Path) -> Concept:
    """
    Parse an OKF concept markdown file according to the permissive consumer spec (v0.2).
    Consumers MUST tolerate unknown types, extra fields, and missing optional fields.
    """
    content = file_path.read_text(encoding="utf-8")

    return parse_concept_content(content, file_path, bundle_root)


def parse_concept_content(content: str, file_path: Path, bundle_root: Path) -> Concept:
    """
    Parse concept content string with YAML frontmatter.
    """
    try:
        post = frontmatter.loads(content)
        metadata = dict(post.metadata)
        body = post.content
    except Exception as e:
        logger.warning(f"Error parsing frontmatter in {file_path}, falling back to permissive defaults: {e}")
        metadata = {}
        body = content

    # Calculate concept ID relative to bundle root without .md suffix
    try:
        rel_path = file_path.relative_to(bundle_root)
        concept_id = str(rel_path.with_suffix("")).replace("\\", "/")
    except ValueError:
        concept_id = file_path.stem

    # Permissive fallback: if type is missing, treat as generic Concept
    if "type" not in metadata or not metadata["type"]:
        metadata["type"] = "Concept"

    # Instantiate frontmatter model permissively
    while True:
        try:
            fm = ConceptFrontmatter(**metadata)
            break
        except ValidationError as e:
            # Preserve valid metadata, especially lifecycle restrictions, when an
            # unrelated optional field is malformed.
            for error in e.errors():
                field = error["loc"][0]
                logger.warning("Ignoring invalid frontmatter field %s in %s", field, concept_id)
                metadata.pop(field, None)

    # Extract markdown links from the body
    links: list[ConceptLink] = []
    for match in LINK_PATTERN.finditer(body):
        text = match.group(1).strip()
        target = match.group(2).strip()
        # Skip external web urls in concept link graphs
        if not (target.startswith("http://") or target.startswith("https://") or target.startswith("#")):
            links.append(ConceptLink(text=text, target=target))

    return Concept(
        concept_id=concept_id,
        file_path=file_path,
        frontmatter=fm,
        body=body,
        links=links,
    )


def parse_index_file(file_path: Path, bundle_root: Path) -> IndexListing:
    """
    Parse an OKF index.md file to enable progressive disclosure.
    index.md is a reserved file that lists concepts and subdirectories in its folder.
    """
    content = file_path.read_text(encoding="utf-8")

    try:
        post = frontmatter.loads(content)
        metadata = dict(post.metadata)
        body = post.content
    except Exception:
        metadata = {}
        body = content

    try:
        rel_dir = file_path.parent.relative_to(bundle_root)
        dir_str = str(rel_dir).replace("\\", "/")
        if dir_str == ".":
            dir_str = ""
    except ValueError:
        dir_str = ""

    title = str(metadata.get("title") or "")
    description = str(metadata.get("description") or "")
    if not title:
        heading = re.search(r"^#\s+(.+)$", body, re.MULTILINE)
        title = heading.group(1).strip() if heading else ""

    # Extract listed items from markdown links in the index file
    items: list[IndexItem] = []
    subdirectories: set[str] = set()

    for match in LINK_PATTERN.finditer(body):
        link_title = match.group(1).strip()
        target = match.group(2).strip()

        parts = urlsplit(target)
        if parts.scheme or parts.netloc or not parts.path:
            continue

        target = unquote(parts.path)
        candidate = (
            bundle_root / target.lstrip("/") if target.startswith("/")
            else file_path.parent / target
        ).resolve()
        if not candidate.is_relative_to(bundle_root.resolve()):
            continue

        # If link points to another index.md or directory
        if candidate.name == "index.md" or target.endswith("/") or candidate.is_dir():
            directory = candidate.parent if candidate.name == "index.md" else candidate
            # Paths are relative to the current index, including cross-directory links.
            sub_target = os.path.relpath(directory, file_path.parent)
            if sub_target != ".":
                subdirectories.add(sub_target)
            continue

        # Concept item
        if candidate.suffix not in ("", ".md") or candidate.name == "log.md":
            continue
        full_concept_id = candidate.relative_to(bundle_root.resolve()).as_posix().removesuffix(".md")

        items.append(
            IndexItem(
                concept_id=full_concept_id,
                title=link_title,
                path=target,
                description=body[match.end():].split("\n", 1)[0].strip().lstrip("- "),
            )
        )

    # Also detect physical subdirectories with an index.md if existing on disk
    directory_path = file_path.parent
    if directory_path.is_dir():
        for child in directory_path.iterdir():
            if child.is_dir() and not child.name.startswith("."):
                sub_index = child / "index.md"
                if sub_index.exists() and sub_index.resolve().is_relative_to(bundle_root.resolve()):
                    subdirectories.add(child.name)

    return IndexListing(
        directory=dir_str,
        title=title or (f"Index: {dir_str}" if dir_str else "Root Index"),
        description=description,
        items=items,
        subdirectories=sorted(subdirectories),
    )
