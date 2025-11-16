"""Tests for the end-to-end lesson generation pipeline."""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest import mock

from lessons_agent.agent import ResearchAgentConfig, ResearchNotes
from lessons_agent.pipeline import (
    LessonGenerationConfig,
    LessonGenerationResult,
    _clean_summary_text,
    _normalize_bundle,
    generate_lessons,
    generate_lessons_to_disk,
)
from lessons_agent.schemas import (
    ContentBlock,
    LessonPlan,
    LessonPlanBundle,
    LessonSection,
    SourceCitation,
)


def _mock_bundle() -> LessonPlanBundle:
    block = ContentBlock(type="text", text="Intro content")
    section = LessonSection(
        title="Section 1",
        summary="Summary",
        key_points=["KP1"],
        content_blocks=[block],
    )
    lesson = LessonPlan(
        topic="Sample",
        level="beginner",
        audience="Learners",
        estimated_duration_minutes=30,
        learning_objectives=["Objective"],
        prerequisites=[],
        sections=[section],
        recommended_resources=[],
        sources=[
            SourceCitation(
                source_id="https://example.com",
                description="Example source",
            )
        ],
    )
    return LessonPlanBundle(
        topic="Sample",
        level="beginner",
        audience="Learners",
        lessons=[lesson],
    )


@mock.patch("lessons_agent.pipeline.ValyuSearchClient")
def test_generate_lessons_runs_research_and_synthesis(mock_client):
    notes = ResearchNotes(topic="LangChain", level="beginner", audience="devs")
    notes.add_entry("Finding A", ["https://example.com"])

    research_mock = mock.Mock(return_value=notes)
    structured_mock = mock.Mock()
    structured_mock.invoke.return_value = _mock_bundle()
    mock_instance = mock.Mock()
    mock_instance.search.return_value = [
        {
            "title": "Visual A",
            "url": "https://example.com/a",
            "summary": "Illustration of concept A.",
            "image_url": "https://example.com/a.png",
            "image_prompt_hint": "Concept A diagram",
        },
        {
            "title": "Visual B",
            "url": "https://example.com/b",
            "summary": "Illustration of concept B.",
            "image_url": "https://example.com/b.png",
            "image_prompt_hint": "Concept B chart",
        },
    ]
    mock_client.from_env.return_value = mock_instance

    config = LessonGenerationConfig(topic="LangChain", level="beginner")

    result = generate_lessons(
        config,
        research_runner=research_mock,
        structured_runner=structured_mock,
    )

    assert isinstance(result, LessonGenerationResult)
    research_mock.assert_called_once()
    structured_mock.invoke.assert_called_once()

    research_args: ResearchAgentConfig = research_mock.call_args.args[0]
    assert research_args.topic == "LangChain"
    assert result.bundle.lessons[0].sections[0].content_blocks[0].text == "Intro content"
    assert any(
        block.type == "image"
        for block in result.bundle.lessons[0].sections[0].content_blocks
    )

    tmp_path = Path(tempfile.mkdtemp())
    infos = generate_lessons_to_disk(
        config,
        output_dir=tmp_path,
        research_runner=research_mock,
        structured_runner=structured_mock,
    )
    assert infos, "Expected lesson files to be created"
    assert infos[0].path.exists()
    assert any(
        block.type == "image"
        for block in result.bundle.lessons[0].sections[0].content_blocks
    )


def test_clean_summary_text_removes_navigation_noise():
    noisy = "Home Pricing Docs\nRAG best practices require clean context windows and trustworthy sources."
    cleaned = _clean_summary_text(noisy)
    assert "Home" not in cleaned
    assert "RAG best practices" in cleaned


def test_normalize_bundle_polishes_sections():
    bundle = _mock_bundle()
    section = bundle.lessons[0].sections[0]
    section.summary = "Home Pricing Docs. Detailed walkthrough of RAG deployments."
    section.content_blocks.append(
        ContentBlock(
            type="image",
            image_prompt="Home Pricing Docs diagram of workflow for retrieval augmented generation with context windows.",
            image_caption="   Visual reference: Demo landing page with nav   ",
            image_url="http://example.com/image.png",
        )
    )
    _normalize_bundle(bundle, topic="RAG Best Practices")
    polished_section = bundle.lessons[0].sections[0]
    assert "Home" not in polished_section.summary
    image_block = next(block for block in polished_section.content_blocks if block.type == "image")
    assert image_block.image_caption.startswith("Visual reference")
    assert len(image_block.image_caption) <= 120


if __name__ == "__main__":
    test_generate_lessons_runs_research_and_synthesis()
    print("All Task 5 tests passed.")

