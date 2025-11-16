"""Tests for monitoring utilities."""

from __future__ import annotations

import json
from unittest import mock

from lessons_agent.monitoring import configure_logging, log_event, validate_lesson_bundle
from lessons_agent.schemas import (
    ContentBlock,
    LessonPlan,
    LessonPlanBundle,
    LessonSection,
    SourceCitation,
)


def test_log_event_writes_json(capfd=None):
    configure_logging()
    with mock.patch("lessons_agent.monitoring.LOGGER") as logger:
        log_event("test_event", foo="bar")
        logger.info.assert_called_once()


def test_validate_lesson_bundle_requires_sources():
    block = ContentBlock(type="text", text="content")
    section = LessonSection(
        title="Section",
        summary="Summary",
        key_points=["One"],
        content_blocks=[block],
    )
    lesson = LessonPlan(
        topic="Topic",
        level="beginner",
        audience="aud",
        estimated_duration_minutes=30,
        learning_objectives=["Obj"],
        prerequisites=[],
        sections=[section],
        recommended_resources=[],
        sources=[SourceCitation(source_id="https://example.com", description="desc")],
    )
    bundle = LessonPlanBundle(topic="Topic", level="beginner", audience="aud", lessons=[lesson])
    validate_lesson_bundle(bundle)
    bundle.lessons[0].sources = []
    try:
        validate_lesson_bundle(bundle)
        assert False, "Expected validation error when sources missing"
    except ValueError:
        pass

