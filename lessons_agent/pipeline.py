"""Lesson generation pipeline that chains research + structured synthesis."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, List, Optional, Sequence

from lessons_agent.agent import ResearchAgentConfig, ResearchNotes, run_research_agent
from lessons_agent.monitoring import log_event, validate_lesson_bundle
from lessons_agent.output import LessonFileInfo, write_lessons_to_directory
from lessons_agent.schemas import (
    ContentBlock,
    LessonPlan,
    LessonPlanBundle,
    LessonSection,
    ReferenceResource,
    SourceCitation,
)
from lessons_agent.structured_output import get_lesson_plan_bundle_model
from lessons_agent.tools import ValyuSearchClient


@dataclass
class LessonGenerationConfig:
    """Inputs for generating a bundle of lesson plans."""

    topic: str
    level: str = "intermediate"
    audience: str = "General learners"
    num_lessons: int = 2
    goals: str = "Create comprehensive lesson plans."
    estimated_duration_minutes: int = 45


@dataclass
class LessonGenerationResult:
    """Output container for the lesson generation pipeline."""

    notes: ResearchNotes
    bundle: LessonPlanBundle


SCHEMA_JSON = json.dumps(LessonPlanBundle.model_json_schema(), indent=2)


SYNTHESIS_INSTRUCTIONS = """
You are an expert instructional designer producing slide-ready lessons for live teaching.
Convert the research notes into lesson plans strictly following the JSON schema. The prose
must be self-contained, written for educators, and must not mention how the research was
conducted, specific tools, or search providers. Favor short paragraphs and bulletable
statements that can drop directly into presentation slides. Each lesson must cite the
sources referenced in the notes.

When constructing sections, ensure every lesson section contains at least:
- one `text` content block with clear explanations, examples, or facilitator notes, and
- one `image` content block whose `image_prompt` vividly describes a visual to show on a slide.
  Supply `image_url` when available; otherwise leave it null. Keep `image_caption` short.
Never include phrases like "summary compiled from search results" or brand/tool names.

Schema requirements:
- Top-level keys: topic (str), level (str), audience (str), lessons (List[LessonPlan]).
- Each LessonPlan must include: topic (str), level (str), audience (str), estimated_duration_minutes (int),
  learning_objectives (List[str]), prerequisites (List[str]), sections (List[LessonSection]),
  recommended_resources (List[ReferenceResource]), sources (List[SourceCitation]).
- Each LessonSection must include: title (str), summary (str), key_points (List[str]),
  content_blocks (List[{{type: "text"|"image", text?: str, image_prompt?: str, image_caption?: str, image_url?: str}}]).
- Each SourceCitation must be an object with source_id (url or identifier) and description (str).
- Do not introduce any additional keys or rename required ones.

Exact JSON schema (reference only, do not paraphrase field names):
{schema}
""".strip().format(schema=SCHEMA_JSON)


def _build_synthesis_prompt(config: LessonGenerationConfig, notes: ResearchNotes) -> str:
    return (
        f"{SYNTHESIS_INSTRUCTIONS}\n\n"
        f"Topic: {config.topic}\n"
        f"Learner level: {config.level}\n"
        f"Audience: {config.audience}\n"
        f"Target number of lessons: {config.num_lessons}\n"
        f"Estimated duration minutes: {config.estimated_duration_minutes}\n"
        f"Goals: {config.goals}\n"
        "Writing style: slide-ready, instructor-facing, no references to research tools or search engines.\n"
        "Visual guidance: each section should describe at least one compelling visual that aids teaching.\n\n"
        f"Research Notes:\n"
        f"{notes.as_markdown()}\n"
    )


def generate_lessons(
    config: LessonGenerationConfig,
    *,
    research_runner: Callable[[ResearchAgentConfig], ResearchNotes] = run_research_agent,
    structured_runner=None,
) -> LessonGenerationResult:
    """Run research + synthesis to produce a LessonPlanBundle."""

    research_config = ResearchAgentConfig(
        topic=config.topic,
        level=config.level,
        audience=config.audience,
        goals=config.goals,
    )
    notes = research_runner(research_config)
    log_event("lesson_synthesis_start", topic=config.topic, notes_entries=len(notes.entries))
    synthesis = structured_runner or get_lesson_plan_bundle_model()
    prompt = _build_synthesis_prompt(config, notes)
    bundle = None
    try:
        bundle = _invoke_synthesis_with_retries(synthesis, prompt)
    except ValueError as exc:
        log_event("lesson_synthesis_error", error=str(exc))
        bundle = _build_fallback_bundle(config, notes)
    _ensure_image_blocks(bundle, enrichment_topic=config.topic)
    _normalize_bundle(bundle, topic=config.topic)
    validate_lesson_bundle(bundle)
    log_event("lesson_synthesis_complete", lessons=len(bundle.lessons))

    return LessonGenerationResult(notes=notes, bundle=bundle)


def generate_lessons_to_disk(
    config: LessonGenerationConfig,
    *,
    output_dir: Path,
    research_runner: Callable[[ResearchAgentConfig], ResearchNotes] = run_research_agent,
    structured_runner=None,
) -> List[LessonFileInfo]:
    """Convenience wrapper to run generation and persist files."""

    result = generate_lessons(
        config,
        research_runner=research_runner,
        structured_runner=structured_runner,
    )
    infos = write_lessons_to_directory(result, output_dir)
    log_event("lesson_files_written", count=len(infos), output_dir=str(output_dir))
    return infos


def _invoke_synthesis_with_retries(
    synthesis_runnable,
    prompt: str,
    *,
    max_attempts: int = 2,
) -> LessonPlanBundle:
    """Invoke structured synthesis with retries before falling back."""

    last_error: Optional[ValueError] = None
    retry_note = (
        "\n\nSTRICT SCHEMA REMINDER: Respond with a single JSON object that matches the provided schema. "
        "Do not omit the `lessons` list and do not add commentary outside the JSON."
    )
    for attempt in range(max_attempts):
        try:
            return synthesis_runnable.invoke(prompt)
        except ValueError as exc:
            last_error = exc
            prompt = prompt + retry_note
    if last_error:
        raise last_error
    raise ValueError("Structured synthesis failed without raising a specific error.")


def _build_fallback_bundle(
    config: LessonGenerationConfig,
    notes: ResearchNotes,
) -> LessonPlanBundle:
    """Generate a conservative bundle when structured output validation fails."""

    client = ValyuSearchClient.from_env()
    search_results = client.search(
        query=f"{config.topic} {config.goals}",
        max_results=max(6, config.num_lessons * 3),
    )

    lessons: List[LessonPlan] = []
    for idx in range(config.num_lessons):
        entry = notes.entries[min(idx, len(notes.entries) - 1)] if notes.entries else None
        section_text = _clean_summary_text(entry.content if entry else "") or f"Overview of {config.topic}."
        section_summary = section_text[:600]
        key_points = entry.citations[:3] if entry and entry.citations else [
            "Highlight the practical takeaways from referenced materials."
        ]
        sections = [
            LessonSection(
                title=f"Key Insights for {config.topic}",
                summary=section_summary,
                key_points=key_points,
                content_blocks=[ContentBlock(type="text", text=section_text)],
            )
        ]
        slice_start = idx * 2
        slice_end = slice_start + 2
        source_items = search_results[slice_start:slice_end] or search_results[:2]
        sources: List[SourceCitation] = [
            SourceCitation(
                source_id=item.get("url", "https://open-research.example/reference"),
                description=item.get("title", "Curated research reference"),
            )
            for item in source_items
            if item
        ]
        if not sources:
            sources = [
                SourceCitation(
                    source_id="https://open-research.example/reference",
                    description="Fallback reference generated from curated research.",
                )
            ]
        image_blocks = [
            block
            for block in (_build_image_block_from_result(item, config.topic) for item in source_items)
            if block is not None
        ]
        if image_blocks:
            sections[0].content_blocks.extend(image_blocks)
        lessons.append(
            LessonPlan(
                topic=f"{config.topic} — Lesson {idx + 1}",
                level=config.level,
                audience=config.audience,
                estimated_duration_minutes=config.estimated_duration_minutes,
                learning_objectives=[
                    "Review the curated RAG insights.",
                    "Translate findings into learner-facing activities.",
                    "Connect cited references to concrete practices.",
                ],
                prerequisites=[],
                sections=sections,
                recommended_resources=[
                    ReferenceResource(
                        title=source.description,
                        url=source.source_id if source.source_id != "https://valyu.ai" else None,
                        type="article",
                    )
                    for source in sources
                ],
                sources=sources,
            )
        )

    return LessonPlanBundle(
        topic=config.topic,
        level=config.level,
        audience=config.audience,
        lessons=lessons,
    )


def _ensure_image_blocks(bundle: LessonPlanBundle, *, enrichment_topic: str) -> None:
    """Guarantee that every section includes at least one image block."""

    sections_missing_images: List[LessonSection] = []
    for lesson in bundle.lessons:
        for section in lesson.sections:
            if not any(block.type == "image" for block in section.content_blocks):
                sections_missing_images.append(section)
    if not sections_missing_images:
        return

    try:
        client = ValyuSearchClient.from_env()
    except Exception as exc:  # pragma: no cover - defensive
        log_event("image_enrichment_skipped", reason=str(exc))
        return

    max_results = max(len(sections_missing_images) * 2, 4)
    try:
        results = client.search(
            query=f"{enrichment_topic} visuals for instruction",
            max_results=max_results,
        )
    except Exception as exc:  # pragma: no cover - defensive
        log_event("image_enrichment_failed", error=str(exc))
        return

    result_iter = iter(results or [])
    for section in sections_missing_images:
        candidate = next(result_iter, None)
        if candidate is None:
            break
        block = _build_image_block_from_result(candidate, section.title or enrichment_topic)
        if block:
            section.content_blocks.append(block)


def _build_image_block_from_result(item: Optional[dict], topic: str) -> Optional[ContentBlock]:
    """Convert a Valyu search result into an image content block."""

    if not item:
        return None
    prompt_hint = _clean_summary_text(
        item.get("image_prompt_hint") or item.get("summary") or ""
    )
    if not prompt_hint:
        prompt_hint = f"Illustrate the central idea behind {topic}."
    title = item.get("title") or topic
    prompt = f"Slide illustration for {title}: {prompt_hint}"
    image_url = item.get("image_url") or item.get("thumbnail_url") or item.get("url")
    if image_url and isinstance(image_url, str):
        if not image_url.startswith(("http://", "https://")):
            image_url = None
    else:
        image_url = None
    return ContentBlock(
        type="image",
        image_prompt=prompt[:500],
        image_caption=f"Visual reference: {title}",
        image_url=image_url,
    )


def _normalize_bundle(bundle: LessonPlanBundle, *, topic: str) -> None:
    """Polish summaries, blocks, and key points for slide-ready quality."""

    for lesson in bundle.lessons:
        lesson.topic = lesson.topic.strip() or topic
        lesson.learning_objectives = _ensure_list(
            lesson.learning_objectives,
            fallback=[
                f"Describe the most important practices for {topic}.",
                "Connect the practices to real implementation scenarios.",
            ],
        )
        for section in lesson.sections:
            section.title = section.title.strip() or f"Essential Concepts for {topic}"
            section.summary = _polish_text(section.summary, max_sentences=4)
            section.key_points = _ensure_list(
                [_strip_navigation_tokens(point) for point in section.key_points],
                fallback=[f"Summarize how to apply {topic} in production."],
            )
            polished_blocks: List[ContentBlock] = []
            for block in section.content_blocks:
                if block.type == "text" and block.text:
                    block.text = _polish_text(block.text, max_sentences=6)
                elif block.type == "image":
                    block.image_prompt = _polish_text(
                        block.image_prompt or f"Illustrate the concept: {section.title}",
                        max_sentences=2,
                    )
                    block.image_caption = (
                        _trim_caption(block.image_caption or section.title)
                    )
                polished_blocks.append(block)
            section.content_blocks = polished_blocks


def _ensure_list(items: Sequence[str], *, fallback: List[str]) -> List[str]:
    values = [value.strip() for value in items if value and value.strip()]
    return values or fallback


NAVIGATION_STOPWORDS = {
    "home",
    "pricing",
    "docs",
    "documentation",
    "resources",
    "customers",
    "solutions",
    "product",
    "shop",
    "latest",
    "trends",
    "book",
    "demo",
    "request",
    "back",
}

MARKDOWN_TOKEN_PATTERN = re.compile(r"[*_`#]+")
PARENS_LINK_PATTERN = re.compile(r"\[(?P<label>[^\]]+)\]\((?P<url>[^)]+)\)")
MULTI_SPACE_PATTERN = re.compile(r"\s{2,}")


def _clean_summary_text(text: str, *, max_sentences: int = 5) -> str:
    """Collapse noisy snippets into tidy paragraphs suitable for lessons."""

    if not text:
        return ""
    stripped = PARENS_LINK_PATTERN.sub(r"\g<label>", text)
    stripped = MARKDOWN_TOKEN_PATTERN.sub("", stripped)
    stripped = stripped.replace("•", " ").replace("–", " - ").replace("—", " - ")
    stripped = MULTI_SPACE_PATTERN.sub(" ", stripped)
    fragments = re.split(r"(?<=[.!?])\s+|\n+", stripped)
    cleaned_fragments: List[str] = []
    for fragment in fragments:
        candidate = _strip_navigation_tokens(fragment)
        candidate = candidate.strip(" -")
        if not candidate:
            continue
        if len(candidate) < 30:
            continue
        alpha_ratio = sum(c.isalpha() for c in candidate) / max(len(candidate), 1)
        if alpha_ratio < 0.4:
            continue
        cleaned_fragments.append(candidate)
        if len(cleaned_fragments) >= max_sentences:
            break
    if not cleaned_fragments:
        cleaned_fragments = [_strip_navigation_tokens(stripped).strip()]
    combined = " ".join(cleaned_fragments).strip()
    return combined


def _strip_navigation_tokens(text: str) -> str:
    tokens = text.split()
    filtered = [
        token for token in tokens if token.lower() not in NAVIGATION_STOPWORDS
    ]
    return " ".join(filtered)


def _polish_text(value: Optional[str], *, max_sentences: int) -> str:
    cleaned = _clean_summary_text(value or "", max_sentences=max_sentences)
    return cleaned[:1200]


def _trim_caption(caption: str) -> str:
    caption = caption.strip()
    if len(caption) <= 120:
        return caption
    return caption[:117].rstrip() + "..."


__all__ = [
    "LessonGenerationConfig",
    "LessonGenerationResult",
    "generate_lessons",
    "generate_lessons_to_disk",
]

