from dataclasses import dataclass

from langchain_core.language_models import BaseChatModel
from langchain_core.runnables import RunnableConfig

from langgraph_okf.agent.llm import get_openrouter_llm
from langgraph_okf.bundle import OKFBundle
from langgraph_okf.models import TrustTier
from langgraph_okf.settings import Settings


@dataclass(frozen=True, kw_only=True)
class Context:
    """Dependencies and policy fixed for one run, separate from graph state."""

    bundle: OKFBundle
    llm: BaseChatModel | None = None
    min_trust_tier: TrustTier = TrustTier.UNVERIFIED
    max_traversal_depth: int = 3
    strict_validation: bool = False

    def __post_init__(self) -> None:
        if self.max_traversal_depth < 0:
            raise ValueError("max_traversal_depth must be nonnegative")
        object.__setattr__(self, "min_trust_tier", TrustTier(self.min_trust_tier))

    @property
    def invocation_config(self) -> RunnableConfig:
        """Allow enough graph steps for this run's link-hop budget."""
        return {"recursion_limit": 2 * self.max_traversal_depth + 10}

    @classmethod
    def from_settings(cls, config: Settings) -> Context:
        """Construct dependencies once at the application boundary."""
        # Initialise the LLM only when a key is present; let OpenRouter surface
        # any authentication error rather than guessing on key format here.
        llm = get_openrouter_llm(config) if config.openrouter_api_key else None
        return cls(
            bundle=OKFBundle(config.bundle_path),
            llm=llm,
            min_trust_tier=config.min_trust_tier,
            max_traversal_depth=config.max_traversal_depth,
            strict_validation=config.strict_validation,
        )
