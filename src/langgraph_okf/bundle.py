import logging
import os
from pathlib import Path
from urllib.parse import unquote, urlsplit

import frontmatter as _fm

from langgraph_okf.models import Concept, ConceptFrontmatter, IndexItem, IndexListing, TrustTier
from langgraph_okf.parser import parse_concept_file, parse_index_file
from langgraph_okf.trust import enrich_concept_trust

logger = logging.getLogger(__name__)


class OKFBundle:
    """
    Consumer interface for an OKF (Open Knowledge Format v0.2) Bundle.
    Implements progressive disclosure and deterministic graph traversal.
    """

    def __init__(self, root_path: str | Path):
        self.root_path = Path(root_path).resolve()
        if not self.root_path.is_dir():
            raise FileNotFoundError(f"OKF bundle directory not found at: {self.root_path}")

    def _contained_path(self, path: str | Path) -> Path:
        candidate = (self.root_path / path).resolve()
        if not candidate.is_relative_to(self.root_path):
            raise ValueError(f"Path escapes OKF bundle: {path}")
        return candidate

    def read_index(self, directory: str = "") -> IndexListing:
        """
        Progressive disclosure: Read the index.md for a given directory relative to bundle root.
        If index.md does not exist, permissive consumer spec dictates synthesizing a listing.
        """
        clean_dir = directory.strip("/").replace("\\", "/")
        target_dir = self._contained_path(clean_dir)
        clean_dir = target_dir.relative_to(self.root_path).as_posix()
        clean_dir = "" if clean_dir == "." else clean_dir

        index_file = self._contained_path(target_dir / "index.md")
        if index_file.exists():
            return parse_index_file(index_file, self.root_path)

        # Synthesize index if index.md is absent (permissive consumer behavior)
        items: list[IndexItem] = []
        subdirs: list[str] = []

        if target_dir.is_dir():
            for entry in sorted(target_dir.iterdir()):
                if entry.name.startswith(".") or entry.name == "log.md":
                    continue
                if not entry.resolve().is_relative_to(self.root_path):
                    continue
                if entry.is_dir():
                    subdirs.append(entry.name)
                elif entry.is_file() and entry.suffix == ".md" and entry.name != "index.md":
                    try:
                        concept = self.get_concept(str(entry.relative_to(self.root_path)))
                        items.append(
                            IndexItem(
                                concept_id=concept.concept_id,
                                title=concept.title,
                                description=concept.description,
                                type=concept.type,
                                path=str(entry.relative_to(target_dir)),
                                tags=concept.frontmatter.tags,
                            )
                        )
                    except Exception as e:
                        logger.warning(f"Error loading concept {entry}: {e}")

        return IndexListing(
            directory=clean_dir,
            title=f"Directory: {clean_dir}" if clean_dir else "Root Catalog",
            description="Synthesized directory listing",
            items=items,
            subdirectories=subdirs,
        )

    def resolve_concept_path(self, concept_id_or_path: str) -> Path | None:
        """
        Resolve a concept ID or relative path to an absolute filesystem Path.
        """
        clean = concept_id_or_path.strip().lstrip("/")
        if not clean.endswith(".md"):
            clean += ".md"

        candidate = self._contained_path(clean)
        if candidate.exists() and candidate.is_file():
            return candidate

        return None

    def get_concept(self, concept_id_or_path: str) -> Concept:
        """
        Load a concept document by its concept ID or relative path.
        Enriches the concept with evaluated trust signals and resolves link targets.
        """
        file_path = self.resolve_concept_path(concept_id_or_path)
        if not file_path:
            raise FileNotFoundError(f"Concept '{concept_id_or_path}' not found in bundle at {self.root_path}")

        concept = parse_concept_file(file_path, self.root_path)
        concept = enrich_concept_trust(concept)

        # Resolve outbound link targets
        for link in concept.links:
            resolved = self.resolve_link(concept.concept_id, link.target)
            link.resolved_concept_id = resolved

        return concept

    def resolve_link(self, from_concept_id: str, target: str) -> str | None:
        """
        Resolve a markdown link target to a canonical concept ID.
        Supports bundle-absolute links (/definitions/fees.md) and relative links (../../definitions/fees.md).
        """
        parts = urlsplit(target.strip())
        if not target or parts.scheme or parts.netloc:
            return None

        clean_target = unquote(parts.path).strip()
        if not clean_target:
            return None

        if clean_target.startswith("/"):
            # Bundle-absolute link
            candidate = self.root_path / clean_target.lstrip("/")
        else:
            # Relative link from the originating concept's directory
            from_dir = (self.root_path / from_concept_id).parent
            candidate = (from_dir / clean_target).resolve()

        candidate = candidate.resolve()
        if not candidate.is_relative_to(self.root_path):
            return None
        if candidate.suffix and candidate.suffix != ".md":
            return None
        if candidate.exists() and candidate.is_file():
            try:
                rel = candidate.relative_to(self.root_path)
                return str(rel.with_suffix("")).replace("\\", "/")
            except ValueError:
                return None

        # Try appending .md if omitted
        if not clean_target.endswith(".md"):
            return self.resolve_link(from_concept_id, clean_target + ".md")

        return None

    def list_all_concept_ids(self) -> list[str]:
        """
        List all concept IDs present in the bundle.
        """
        concept_ids: list[str] = []
        for root, dirs, files in os.walk(self.root_path):
            dirs[:] = sorted(d for d in dirs if not d.startswith(".") and not (Path(root) / d).is_symlink())
            for file in sorted(files):
                if file.endswith(".md") and not file.startswith(".") and file not in ("index.md", "log.md"):
                    full_path = Path(root) / file
                    if not full_path.resolve().is_relative_to(self.root_path):
                        continue
                    rel = full_path.relative_to(self.root_path)
                    concept_ids.append(str(rel.with_suffix("")).replace("\\", "/"))
        return sorted(concept_ids)

    def _scan_frontmatter(self, concept_id: str) -> ConceptFrontmatter | None:
        """
        Parse only the YAML frontmatter of a concept — no body loading, no trust enrichment.
        Used as a cheap pre-filter before calling the heavier get_concept() path.
        """
        path = self.resolve_concept_path(concept_id)
        if not path:
            return None
        try:
            metadata = dict(_fm.loads(path.read_text(encoding="utf-8")).metadata)
            return ConceptFrontmatter(**metadata)
        except Exception:
            return None

    def find_concepts(
        self,
        concept_type: str | None = None,
        tag: str | None = None,
        min_trust_tier: TrustTier | None = None,
    ) -> list[Concept]:
        """
        Query concepts across the bundle matching type, tag, or trust requirements.
        Cheap frontmatter fields (type, tags) are pre-filtered without loading bodies.
        """
        results: list[Concept] = []
        for cid in self.list_all_concept_ids():
            try:
                # Pre-filter on cheap frontmatter fields to avoid loading all bodies
                if concept_type or tag:
                    fm = self._scan_frontmatter(cid)
                    if fm is None:
                        continue
                    if concept_type and fm.type.lower() != concept_type.lower():
                        continue
                    if tag and tag.lower() not in [t.lower() for t in fm.tags]:
                        continue
                # Full load only for concepts that pass the cheap filters
                c = self.get_concept(cid)
                if min_trust_tier and not c.trust_tier.meets(min_trust_tier):
                    continue
                results.append(c)
            except Exception as e:
                logger.warning(f"Error checking concept {cid}: {e}")
        return results
