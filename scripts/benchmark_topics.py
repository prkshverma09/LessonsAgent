#!/usr/bin/env python
"""Run LessonsAgent across a small topic benchmark set."""

from __future__ import annotations

import argparse
from pathlib import Path

from lessons_agent.pipeline import LessonGenerationConfig, generate_lessons_to_disk
from lessons_agent.monitoring import configure_logging, log_event

BENCHMARK_TOPICS = [
    ("LangChain ReAct Basics", "beginner"),
    ("Retrieval Augmented Generation", "intermediate"),
    ("LLM Safety Mitigations", "advanced"),
]


def main():
    parser = argparse.ArgumentParser(description="Benchmark LessonsAgent on fixed topics.")
    parser.add_argument("--output-dir", default="./benchmark_output")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    configure_logging()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    for topic, level in BENCHMARK_TOPICS:
        config = LessonGenerationConfig(topic=topic, level=level, num_lessons=1)
        log_event("benchmark_topic_start", topic=topic)
        infos = generate_lessons_to_disk(config, output_dir=output_dir)
        log_event("benchmark_topic_complete", topic=topic, files=len(infos))


if __name__ == "__main__":
    main()

