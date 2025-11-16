"""Pydantic data models for lesson-plan generation."""

from typing import List, Literal, Optional

from pydantic import BaseModel, Field, HttpUrl, PositiveInt, ValidationInfo, field_validator

LearnerLevel = Literal["beginner", "intermediate", "advanced"]
ContentBlockType = Literal["text", "image"]
ResourceType = Literal["article", "video", "paper", "book", "documentation", "other"]


class ContentBlock(BaseModel):
    """A content block inside a lesson section."""

    type: ContentBlockType
    text: Optional[str] = Field(
        default=None,
        description="Textual content for the block when type is 'text'.",
    )
    image_prompt: Optional[str] = Field(
        default=None,
        description="Prompt describing an image to generate or retrieve.",
    )
    image_caption: Optional[str] = Field(
        default=None,
        description="Suggested caption for the image block.",
    )
    image_url: Optional[HttpUrl] = Field(
        default=None,
        description="Optional remote asset URL for the generated or fetched image.",
    )

    @field_validator("text", mode="after")
    def validate_text(cls, value, info: ValidationInfo):  # type: ignore[override]
        content_type = info.data.get("type")
        if content_type == "text" and not value:
            raise ValueError("Text content blocks must include non-empty text.")
        return value

    @field_validator("image_prompt", mode="after")
    def validate_image_prompt(cls, value, info: ValidationInfo):  # type: ignore[override]
        content_type = info.data.get("type")
        if content_type == "image" and not value:
            raise ValueError("Image content blocks must include an image_prompt.")
        return value


class ReferenceResource(BaseModel):
    """External resources recommended for learners."""

    title: str = Field(..., description="Resource title.")
    type: ResourceType = Field(..., description="Resource format/category.")
    url: Optional[HttpUrl] = Field(
        default=None, description="Optional URL pointing to the resource."
    )
    notes: Optional[str] = Field(
        default=None, description="Context on when/how to use the resource."
    )


class SourceCitation(BaseModel):
    """Metadata about a source consulted during research."""

    source_id: str = Field(..., description="Stable identifier (URL or doc path).")
    description: str = Field(..., description="Summary of what this source covers.")


class LessonSection(BaseModel):
    """A single major section inside a lesson."""

    title: str
    summary: str
    key_points: List[str] = Field(default_factory=list)
    content_blocks: List[ContentBlock] = Field(default_factory=list)

    @field_validator("key_points", mode="after")
    def validate_key_points(cls, value):  # type: ignore[override]
        if not value:
            raise ValueError("Sections must include at least one key point.")
        return value

    @field_validator("content_blocks", mode="after")
    def validate_content_blocks(cls, value):  # type: ignore[override]
        if not value:
            raise ValueError("Sections must include at least one content block.")
        return value


class LessonPlan(BaseModel):
    """Complete lesson definition with pedagogical structure."""

    topic: str
    level: LearnerLevel
    audience: str
    estimated_duration_minutes: PositiveInt = Field(
        ..., description="Approximate duration per lesson."
    )
    learning_objectives: List[str]
    prerequisites: List[str] = Field(default_factory=list)
    sections: List[LessonSection]
    recommended_resources: List[ReferenceResource] = Field(default_factory=list)
    sources: List[SourceCitation] = Field(default_factory=list)

    @field_validator("learning_objectives", mode="after")
    def validate_objectives(cls, value):  # type: ignore[override]
        if not value:
            raise ValueError("Lessons must include at least one learning objective.")
        return value

    @field_validator("sections", mode="after")
    def validate_sections(cls, value):  # type: ignore[override]
        if not value:
            raise ValueError("Lessons must include at least one section.")
        return value


class LessonPlanBundle(BaseModel):
    """Collection of lessons tied to a topic and learner level."""

    topic: str
    level: LearnerLevel
    audience: str
    lessons: List[LessonPlan]

    @field_validator("lessons", mode="after")
    def validate_lessons(cls, value):  # type: ignore[override]
        if not value:
            raise ValueError("Lesson bundles must include at least one lesson.")
        return value

