"""Basic validation checks for LessonPlan schemas and structured output helper."""

from __future__ import annotations

import json
from typing import Any, List, Optional

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_core.runnables import RunnableLambda

from lessons_agent.schemas import (
    ContentBlock,
    LessonPlan,
    LessonPlanBundle,
    LessonSection,
    ReferenceResource,
    SourceCitation,
)
from lessons_agent.structured_output import get_lesson_plan_bundle_model


class _MockChatModel(BaseChatModel):
    """Minimal chat model stub that returns preset JSON content."""

    payload: dict

    def __init__(self, payload: dict):
        super().__init__(payload=payload)

    @property
    def _llm_type(self) -> str:
        return "mock"

    def _generate(  # type: ignore[override]
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> ChatResult:
        del messages, stop, kwargs  # unused
        message = AIMessage(content=json.dumps(self.payload))
        generation = ChatGeneration(message=message)
        return ChatResult(generations=[generation])

    async def _agenerate(self, *args: Any, **kwargs: Any) -> ChatResult:  # type: ignore[override]
        raise NotImplementedError("Async generation is not implemented for the mock.")

    def bind_tools(self, *args: Any, **kwargs: Any) -> "_MockChatModel":  # type: ignore[override]
        return self

    def with_structured_output(self, schema, **kwargs):  # type: ignore[override]
        """Mimic structured output by returning a Runnable that validates payload."""

        return RunnableLambda(lambda _input: schema.model_validate(self.payload))


def _build_sample_bundle() -> LessonPlanBundle:
    block = ContentBlock(type="text", text="Explain what LangChain is.")
    section = LessonSection(
        title="Overview",
        summary="High-level overview of LangChain.",
        key_points=["History", "Key abstractions"],
        content_blocks=[block],
    )
    resource = ReferenceResource(
        title="LangChain Docs",
        type="documentation",
        url="https://python.langchain.com",
    )
    source = SourceCitation(
        source_id="https://python.langchain.com",
        description="Primary documentation site.",
    )
    lesson = LessonPlan(
        topic="LangChain",
        level="beginner",
        audience="New AI engineers",
        estimated_duration_minutes=45,
        learning_objectives=["Understand LangChain's purpose"],
        prerequisites=["Basic Python"],
        sections=[section],
        recommended_resources=[resource],
        sources=[source],
    )
    return LessonPlanBundle(
        topic="LangChain Introduction",
        level="beginner",
        audience="New AI engineers",
        lessons=[lesson],
    )


def test_schema_round_trip() -> None:
    """Ensure lesson bundle objects serialize and deserialize correctly."""

    bundle = _build_sample_bundle()
    serialized = bundle.model_dump_json()
    restored = LessonPlanBundle.model_validate_json(serialized)

    assert restored.topic == bundle.topic
    assert restored.lessons[0].sections[0].content_blocks[0].text == "Explain what LangChain is."


def test_structured_output_helper_returns_bundle() -> None:
    """Verify the helper produces LessonPlanBundle objects via structured output."""

    bundle = _build_sample_bundle()
    mock_llm = _MockChatModel(payload=bundle.model_dump(mode="json"))
    structured_runner = get_lesson_plan_bundle_model(llm=mock_llm)

    result = structured_runner.invoke("generate a bundle")
    assert isinstance(result, LessonPlanBundle)
    assert result.lessons[0].learning_objectives == ["Understand LangChain's purpose"]


if __name__ == "__main__":
    test_schema_round_trip()
    test_structured_output_helper_returns_bundle()
    print("All Task 1 tests passed.")

