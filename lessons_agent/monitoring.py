"""Logging and validation utilities for LessonsAgent."""

from __future__ import annotations

import json
import logging
from typing import Any, Iterable

from lessons_agent.schemas import LessonPlanBundle

LOGGER_NAME = "lessons_agent"


def configure_logging(level: int = logging.INFO) -> logging.Logger:
    """Configure and return the shared LessonsAgent logger."""

    logger = logging.getLogger(LOGGER_NAME)
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    logger.setLevel(level)
    logger.propagate = False
    return logger


LOGGER = configure_logging()


def log_event(event_type: str, **metadata: Any) -> None:
    """Log a structured monitoring event."""

    payload = {"event": event_type, **metadata}
    LOGGER.info("%s", json.dumps(payload, default=str))


def validate_lesson_bundle(bundle: LessonPlanBundle) -> None:
    """Perform basic safety/quality checks on generated lessons."""

    if not bundle.lessons:
        raise ValueError("Lesson bundle must contain at least one lesson.")

    for idx, lesson in enumerate(bundle.lessons, start=1):
        if not lesson.sources:
            raise ValueError(f"Lesson {idx} is missing citations/sources.")
        for section in lesson.sections:
            if not section.content_blocks:
                raise ValueError(f"Lesson {idx} contains an empty section {section.title}.")


__all__ = ["configure_logging", "log_event", "validate_lesson_bundle", "LOGGER"]

