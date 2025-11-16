"""Centralized configuration primitives for LessonsAgent."""

from __future__ import annotations

from functools import lru_cache
from typing import Any, Dict

from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict


class LLMSettings(BaseSettings):
    """Settings controlling the default LLM configuration."""

    model_name: str = "claude-3-5-sonnet"
    temperature: float = 0.3
    max_tokens: int = 2048
    timeout: int = 60
    use_openai: bool = False

    model_config = SettingsConfigDict(
        env_prefix="LESSONS_AGENT_LLM_",
        env_file=".env",
        extra="ignore",
    )


@lru_cache(maxsize=1)
def get_llm_settings() -> LLMSettings:
    """Return cached LLM settings loaded from environment / defaults."""

    return LLMSettings()


def reload_llm_settings() -> LLMSettings:
    """Clear cached settings and reload from the environment."""

    get_llm_settings.cache_clear()  # type: ignore[attr-defined]
    return get_llm_settings()


def to_overrides_dict(overrides: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """Return a sanitized overrides dictionary."""

    return {k: v for k, v in (overrides or {}).items() if v is not None}


class ResolvedLLMConfig(BaseModel):
    """Materialized configuration passed to `get_chat_model`."""

    model_name: str
    use_openai: bool
    temperature: float
    max_tokens: int
    timeout: int


