"""Structured output helpers for lesson generation."""

from typing import Optional

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.runnables import Runnable

from lessons_agent.schemas import LessonPlanBundle
from tutorials.holistic_ai_bedrock import get_chat_model


def get_lesson_plan_bundle_model(
    *,
    llm: Optional[BaseChatModel] = None,
    model_name: str = "claude-3-5-sonnet",
    **llm_kwargs,
) -> Runnable:
    """Return a LangChain runnable that yields LessonPlanBundle instances.

    Args:
        llm: Optional pre-instantiated chat model. If not provided, the Holistic AI
            helper is used to construct one via ``get_chat_model``.
        model_name: Identifier passed to ``get_chat_model`` when ``llm`` is omitted.
        **llm_kwargs: Forwarded to ``get_chat_model`` for finer-grained control.

    Returns:
        A Runnable that, when invoked, produces ``LessonPlanBundle`` objects that
        conform to the schema defined in ``lessons_agent.schemas``.
    """

    base_llm = llm or get_chat_model(model_name=model_name, **llm_kwargs)
    return base_llm.with_structured_output(LessonPlanBundle)

