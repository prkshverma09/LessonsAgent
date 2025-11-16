"""Unit tests for lessons_agent.llm configuration helpers."""

from __future__ import annotations

import os
from unittest import mock

from lessons_agent.config import reload_llm_settings
from lessons_agent.llm import get_default_chat_model, get_structured_output_model
from lessons_agent.schemas import LessonPlanBundle


def _reset_env_var(key: str, original_value: str | None) -> None:
    if original_value is None:
        os.environ.pop(key, None)
    else:
        os.environ[key] = original_value
    reload_llm_settings()


def test_get_default_chat_model_uses_defaults() -> None:
    with mock.patch(
        "lessons_agent.llm.get_chat_model", autospec=True
    ) as mock_get_chat_model:
        fake_model = mock.Mock()
        mock_get_chat_model.return_value = fake_model

        result = get_default_chat_model()

        assert result is fake_model
        mock_get_chat_model.assert_called_once_with(
            model_name="claude-3-5-sonnet",
            use_openai=False,
            temperature=0.3,
            max_tokens=2048,
            timeout=60,
        )


def test_environment_override_affects_model_settings() -> None:
    env_key = "LESSONS_AGENT_LLM_TEMPERATURE"
    original_value = os.environ.get(env_key)
    os.environ[env_key] = "0.75"
    reload_llm_settings()

    try:
        with mock.patch(
            "lessons_agent.llm.get_chat_model", autospec=True
        ) as mock_get_chat_model:
            mock_get_chat_model.return_value = mock.Mock()
            get_default_chat_model()

            mock_get_chat_model.assert_called_once_with(
                model_name="claude-3-5-sonnet",
                use_openai=False,
                temperature=0.75,
                max_tokens=2048,
                timeout=60,
            )
    finally:
        _reset_env_var(env_key, original_value)


def test_structured_output_helper() -> None:
    mock_model = mock.Mock()
    mock_runnable = mock.Mock()
    mock_model.with_structured_output.return_value = mock_runnable
    with mock.patch(
        "lessons_agent.llm.get_chat_model", return_value=mock_model
    ) as mock_get_chat_model:
        result = get_structured_output_model(LessonPlanBundle)

    mock_get_chat_model.assert_called_once()
    mock_model.with_structured_output.assert_called_once_with(LessonPlanBundle)
    assert result is mock_runnable


if __name__ == "__main__":
    test_get_default_chat_model_uses_defaults()
    test_environment_override_affects_model_settings()
    test_structured_output_helper()
    print("All Task 2 tests passed.")

