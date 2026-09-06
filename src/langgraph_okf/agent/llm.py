import logging
from typing import Any

from langchain_openai import ChatOpenAI

from langgraph_okf.settings import Settings

logger = logging.getLogger(__name__)


def get_openrouter_llm(
    settings: Settings,
    model: str | None = None,
    temperature: float = 0.0,
    **kwargs: Any,
) -> ChatOpenAI:
    """
    Instantiate a LangChain ChatOpenAI client configured for OpenRouter
    with application identification headers.
    """
    model_name = model or settings.openrouter_model
    api_key = settings.openrouter_api_key or "sk-dummy-openrouter-key"

    headers = {
        "HTTP-Referer": settings.openrouter_app_url,
        "X-Title": settings.openrouter_app_title,
    }

    return ChatOpenAI(
        model=model_name,
        openai_api_key=api_key,
        openai_api_base=settings.openrouter_base_url,
        temperature=temperature,
        default_headers=headers,
        **kwargs,
    )
