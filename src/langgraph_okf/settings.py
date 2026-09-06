from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from langgraph_okf.models import TrustTier


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # OpenRouter API Configuration
    openrouter_api_key: str = ""
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_model: str = "google/gemini-2.5-flash"
    openrouter_app_title: str = "LangGraph-OKF-Consumer"
    openrouter_app_url: str = "https://github.com/ConceptCodes/langgraph-okf"

    # OKF Bundle Configuration
    bundle_path: Path = Path("bundles/legal_sample")
    min_trust_tier: TrustTier = TrustTier.UNVERIFIED
    max_traversal_depth: int = Field(default=3, ge=0)
    strict_validation: bool = False


settings = Settings()
