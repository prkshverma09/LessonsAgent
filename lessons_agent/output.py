"""Utilities for writing lesson bundles and indexes to disk."""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, List

if TYPE_CHECKING:  # pragma: no cover
    from lessons_agent.pipeline import LessonGenerationResult


def _slugify(value: str) -> str:
    slug = "".join(ch.lower() if ch.isalnum() else "-" for ch in value)
    slug = "-".join(filter(None, slug.split("-")))
    return slug or "lesson"


def _timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")


@dataclass
class LessonFileInfo:
    path: Path
    lesson_id: str
    lesson_index: int


def write_lessons_to_directory(
    result: "LessonGenerationResult",
    output_dir: Path,
) -> List[LessonFileInfo]:
    output_dir.mkdir(parents=True, exist_ok=True)
    topic_slug = _slugify(result.bundle.topic)
    timestamp = _timestamp()
    infos: List[LessonFileInfo] = []

    for idx, lesson in enumerate(result.bundle.lessons, start=1):
        lesson_id = lesson.topic or f"{topic_slug}-{uuid.uuid4().hex[:8]}"
        filename = f"{topic_slug}-lesson-{idx:02d}-{timestamp}.json"
        path = output_dir / filename
        path.write_text(
            json.dumps(lesson.model_dump(mode="json"), indent=2),
            encoding="utf-8",
        )
        infos.append(LessonFileInfo(path=path, lesson_id=lesson_id, lesson_index=idx))

    index_payload = {
        "topic": result.bundle.topic,
        "level": result.bundle.level,
        "audience": result.bundle.audience,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "lessons": [
            {
                "lesson_index": info.lesson_index,
                "file": info.path.name,
                "lesson_topic": result.bundle.lessons[info.lesson_index - 1].topic,
            }
            for info in infos
        ],
    }
    index_path = output_dir / f"{topic_slug}-index-{timestamp}.json"
    index_path.write_text(json.dumps(index_payload, indent=2), encoding="utf-8")

    return infos


__all__ = ["write_lessons_to_directory", "LessonFileInfo"]

