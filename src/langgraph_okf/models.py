from datetime import date, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class TrustTier(StrEnum):
    UNVERIFIED = "unverified"
    MACHINE_CONFIRMED = "machine-confirmed"
    HUMAN_REVIEWED = "human-reviewed"

    @property
    def rank(self) -> int:
        ranks = {
            TrustTier.UNVERIFIED: 0,
            TrustTier.MACHINE_CONFIRMED: 1,
            TrustTier.HUMAN_REVIEWED: 2,
        }
        return ranks[self]

    def meets(self, required: TrustTier) -> bool:
        return self.rank >= required.rank


class LifecycleStatus(StrEnum):
    STABLE = "stable"
    DRAFT = "draft"
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    SUPERSEDED = "superseded"


class SourceReference(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: str | None = None
    resource: str
    title: str | None = None
    author: str | None = None
    usage_count: int | None = None
    last_modified: datetime | date | str | None = None


class AttestationSpec(BaseModel):
    model_config = ConfigDict(extra="allow")

    executor: dict[str, Any] | None = None
    attester: dict[str, Any] | None = None
    receipt: dict[str, Any] | None = None


class ConceptFrontmatter(BaseModel):
    model_config = ConfigDict(extra="allow")

    type: str = "Concept"
    title: str | None = None
    description: str | None = None
    resource: str | None = None
    tags: list[str] = Field(default_factory=list)
    sources: list[SourceReference] = Field(default_factory=list)
    generated: dict[str, Any] | None = None
    verified: list[dict[str, Any]] | dict[str, Any] | None = None
    status: str = "stable"
    stale_after: datetime | date | str | None = None
    computation: str | AttestationSpec | None = None
    runtime: str | None = None
    parameters: list[dict[str, Any]] = Field(default_factory=list)
    executor: dict[str, Any] | None = None
    attester: dict[str, Any] | None = None


class ConceptLink(BaseModel):
    text: str
    target: str
    resolved_concept_id: str | None = None


class Concept(BaseModel):
    concept_id: str
    file_path: Path
    frontmatter: ConceptFrontmatter
    body: str
    links: list[ConceptLink] = Field(default_factory=list)
    trust_tier: TrustTier = TrustTier.UNVERIFIED
    is_stale: bool = False
    trust_advisories: list[str] = Field(default_factory=list)

    @property
    def type(self) -> str:
        return self.frontmatter.type

    @property
    def title(self) -> str:
        return self.frontmatter.title or Path(self.concept_id).name.replace("_", " ").title()

    @property
    def description(self) -> str:
        return self.frontmatter.description or ""


class IndexItem(BaseModel):
    concept_id: str
    title: str
    description: str = ""
    type: str = "Concept"
    path: str
    tags: list[str] = Field(default_factory=list)


class IndexListing(BaseModel):
    directory: str
    title: str = ""
    description: str = ""
    items: list[IndexItem] = Field(default_factory=list)
    subdirectories: list[str] = Field(default_factory=list)
