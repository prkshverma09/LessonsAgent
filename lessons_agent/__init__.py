"""LessonsAgent package public API."""

from .agent import ResearchAgentConfig, ResearchNotes, run_research_agent
from .pipeline import LessonGenerationConfig, LessonGenerationResult, generate_lessons
from .schemas import (
    ContentBlock,
    LessonPlan,
    LessonPlanBundle,
    LessonSection,
    ReferenceResource,
    SourceCitation,
)

__all__ = [
    "ContentBlock",
    "LessonPlan",
    "LessonPlanBundle",
    "LessonSection",
    "ReferenceResource",
    "SourceCitation",
    "ResearchNotes",
    "ResearchAgentConfig",
    "run_research_agent",
    "LessonGenerationConfig",
    "LessonGenerationResult",
    "generate_lessons",
]

