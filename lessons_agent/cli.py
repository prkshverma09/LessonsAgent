"""Command-line interface for running the LessonsAgent pipeline."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from typing import Callable, List, Sequence

from lessons_agent.agent import ResearchNotes
from lessons_agent.pipeline import (
    LessonGenerationConfig,
    LessonGenerationResult,
    generate_lessons_to_disk,
)
from lessons_agent.schemas import (
    ContentBlock,
    LessonPlan,
    LessonPlanBundle,
    LessonSection,
)
from lessons_agent.output import LessonFileInfo, write_lessons_to_directory
from lessons_agent.monitoring import configure_logging


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="lessons-agent",
        description="Generate AI-powered lesson plans with DeepResearch Agent",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    gen_parser = subparsers.add_parser("generate-lessons", help="Generate lesson JSON files")
    gen_parser.add_argument("topic", help="Topic to research")
    gen_parser.add_argument(
        "--level",
        choices=["beginner", "intermediate", "advanced"],
        default="intermediate",
        help="Learner level",
    )
    gen_parser.add_argument("--audience", default="General learners", help="Target audience")
    gen_parser.add_argument("--num-lessons", type=int, default=2, help="Number of lessons to create")
    gen_parser.add_argument(
        "--estimated-duration",
        type=int,
        default=45,
        help="Estimated duration per lesson (minutes)",
    )
    gen_parser.add_argument("--goals", default="Create comprehensive lesson plans.")
    gen_parser.add_argument(
        "--output-dir",
        default="./output",
        help="Directory to write lesson JSON files",
    )
    gen_parser.add_argument(
        "--mock-run",
        action="store_true",
        help="Use mock data instead of calling live LLMs (useful for testing).",
    )
    gen_parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging.",
    )
    return parser


def _mock_generation_result(config: LessonGenerationConfig) -> LessonGenerationResult:
    notes = ResearchNotes(topic=config.topic, level=config.level, audience=config.audience)
    notes.add_entry(
        f"Mock research notes for {config.topic}. Include citations.",
        ["https://example.com"],
    )

    block = ContentBlock(type="text", text="Mock lesson content block.")
    section = LessonSection(
        title="Introduction",
        summary="Mock summary.",
        key_points=["Point 1"],
        content_blocks=[block],
    )
    lesson = LessonPlan(
        topic=config.topic,
        level=config.level,
        audience=config.audience,
        estimated_duration_minutes=config.estimated_duration_minutes,
        learning_objectives=["Understand mock content"],
        prerequisites=[],
        sections=[section],
        recommended_resources=[],
        sources=[],
    )
    bundle = LessonPlanBundle(
        topic=config.topic,
        level=config.level,
        audience=config.audience,
        lessons=[lesson] * config.num_lessons,
    )
    return LessonGenerationResult(notes=notes, bundle=bundle)


def _run_generation(
    config: LessonGenerationConfig,
    output_dir: Path,
    *,
    mock_run: bool,
) -> List[LessonFileInfo]:
    if mock_run:
        result = _mock_generation_result(config)
        return write_lessons_to_directory(result, output_dir)
    return generate_lessons_to_disk(config, output_dir=output_dir)


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command == "generate-lessons":
        configure_logging(level=logging.DEBUG if args.verbose else logging.INFO)
        config = LessonGenerationConfig(
            topic=args.topic,
            level=args.level,
            audience=args.audience,
            num_lessons=args.num_lessons,
            goals=args.goals,
            estimated_duration_minutes=args.estimated_duration,
        )
        infos = _run_generation(
            config,
            output_dir=Path(args.output_dir),
            mock_run=args.mock_run,
        )
        print(f"Generated {len(infos)} lessons in {args.output_dir}")
        for info in infos:
            print(f"- Lesson {info.lesson_index}: {info.path}")
        return 0

    parser.error("Unknown command")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

