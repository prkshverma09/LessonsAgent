"""Helpers for building chat models configured for LessonsAgent."""

from __future__ import annotations

from typing import Any, Dict, Optional, Type

from dotenv import load_dotenv
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.runnables import Runnable
from pydantic import BaseModel

from lessons_agent.config import (
    LLMSettings,
    ResolvedLLMConfig,
    get_llm_settings,
    reload_llm_settings,
    to_overrides_dict,
)
from tutorials.holistic_ai_bedrock import get_chat_model

load_dotenv()


def _merge_llm_config(
    overrides: Optional[Dict[str, Any]] = None,
) -> ResolvedLLMConfig:
    """Combine env/default settings with ad-hoc overrides."""

    settings: LLMSettings = get_llm_settings()
    merged = settings.model_dump()
    merged.update(to_overrides_dict(overrides))
    return ResolvedLLMConfig(**merged)


def get_default_chat_model(
    *, overrides: Optional[Dict[str, Any]] = None
) -> BaseChatModel:
    """Instantiate the default chat model with optional runtime overrides."""

    config = _merge_llm_config(overrides)
    return get_chat_model(
        model_name=config.model_name,
        use_openai=config.use_openai,
        temperature=config.temperature,
        max_tokens=config.max_tokens,
        timeout=config.timeout,
    )


def get_structured_output_model(
    schema: Type[BaseModel],
    *,
    overrides: Optional[Dict[str, Any]] = None,
) -> Runnable:
    """Return a runnable guaranteed to match the provided schema."""

    chat_model = get_default_chat_model(overrides=overrides)
    return chat_model.with_structured_output(schema)


__all__ = [
    "get_default_chat_model",
    "get_structured_output_model",
    "reload_llm_settings",
]

