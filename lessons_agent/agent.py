"""ReAct research agent construction and orchestration."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from langgraph.errors import GraphRecursionError
from langgraph.prebuilt import create_react_agent

from lessons_agent.llm import get_default_chat_model
from lessons_agent.monitoring import log_event
from lessons_agent.prompts import build_research_prompt
from lessons_agent.tools import (
    ValyuSearchClient,
    fetch_web_page,
    load_local_resource,
    valyu_web_search,
)


@dataclass
class ResearchAgentConfig:
    """Configuration for a single research run."""

    topic: str
    level: str = "intermediate"
    audience: str = "General learners"
    goals: str = "Build comprehensive lesson research notes."
    max_steps: int = 15
    overrides: Optional[Dict[str, Any]] = None


@dataclass
class ResearchEntry:
    """Single research note entry produced by the agent."""

    content: str
    citations: List[str] = field(default_factory=list)


@dataclass
class ResearchNotes:
    """Aggregated research notes for downstream synthesis."""

    topic: str
    level: str
    audience: str
    entries: List[ResearchEntry] = field(default_factory=list)

    def add_entry(self, content: str, citations: Optional[List[str]] = None) -> None:
        self.entries.append(
            ResearchEntry(content=content, citations=citations or []),
        )

    def as_markdown(self) -> str:
        lines = [
            f"# Research Notes: {self.topic} ({self.level})",
            "",
        ]
        for idx, entry in enumerate(self.entries, start=1):
            lines.append(f"## Finding {idx}")
            lines.append(entry.content.strip())
            if entry.citations:
                lines.append("")
                lines.append("Sources:")
                for cite in entry.citations:
                    lines.append(f"- {cite}")
            lines.append("")
        return "\n".join(lines).strip()


DEFAULT_TOOLS = [
    valyu_web_search,
    fetch_web_page,
    load_local_resource,
]


def build_research_agent_executor(
    llm=None,
    tools: Optional[List[Any]] = None,
    prompt=None,
):
    """Create the LangGraph ReAct agent runnable wired with project tools."""

    tools = tools or DEFAULT_TOOLS
    llm = llm or get_default_chat_model()
    prompt = prompt or build_research_prompt()
    return create_react_agent(model=llm, tools=tools, prompt=prompt)


def run_research_agent(
    config: ResearchAgentConfig,
    *,
    agent_executor=None,
) -> ResearchNotes:
    """Execute the research agent and capture results in ResearchNotes."""

    llm_overrides = config.overrides or {}
    prompt = build_research_prompt().partial(
        topic=config.topic,
        level=config.level,
        audience=config.audience,
        goals=config.goals,
    )
    executor = agent_executor or build_research_agent_executor(
        llm=get_default_chat_model(overrides=llm_overrides),
        tools=DEFAULT_TOOLS,
        prompt=prompt,
    )
    notes = ResearchNotes(topic=config.topic, level=config.level, audience=config.audience)
    final_input = {
        "topic": config.topic,
        "level": config.level,
        "audience": config.audience,
        "goals": config.goals,
    }
    log_event("research_agent_start", topic=config.topic, level=config.level)
    invoke_config = {
        "max_execution_time": config.max_steps * 30,
        "recursion_limit": config.max_steps,
    }
    try:
        result = executor.invoke(
            {
                "input": "Conduct deep research and return findings with citations.",
                **final_input,
            },
            config=invoke_config,
        )
        output = result if isinstance(result, str) else result.get("output")
        if not output:
            output = "No findings were produced."
        notes.add_entry(output)
        log_event("research_agent_complete", topic=config.topic)
        return notes
    except GraphRecursionError:
        log_event("research_agent_recursion_limit", topic=config.topic, limit=config.max_steps)
        fallback_summary, fallback_citations = _fallback_research_summary(config)
        notes.add_entry(fallback_summary, fallback_citations)
        return notes


def _fallback_research_summary(config: ResearchAgentConfig) -> tuple[str, List[str]]:
    """When the agent hits recursion limits, perform a direct Valyu search."""

    client = ValyuSearchClient.from_env()
    query = f"{config.topic} {config.goals}"
    raw_results = client.search(query=query, max_results=5)
    if not raw_results:
        return (
            f"Unable to retrieve external data for {config.topic}. Provide high-level best practices.",
            [],
        )
    bullets = []
    citations: List[str] = []
    for idx, item in enumerate(raw_results, start=1):
        url = item.get("url")
        snippet = _clean_fallback_snippet(item.get("summary") or "")
        title = item.get("title") or "Source insight"
        if url:
            citations.append(url)
        detail = snippet or "Review the referenced source for concrete practices."
        bullets.append(f"{idx}. {title}: {detail}")
    intro = f"Key findings for {config.topic}:\n"
    guidance = (
        "Use these evidence-backed talking points when designing the lesson outline."
    )
    content = intro + "\n".join(bullets) + f"\n\n{guidance}"
    return content, citations


def _clean_fallback_snippet(snippet: str) -> str:
    """Normalize snippets so they read like polished teaching notes."""

    snippet = re.sub(r"\s+", " ", snippet).strip()
    if not snippet:
        return ""
    snippet = snippet.replace("TODO:", "").strip()
    max_len = 320
    if len(snippet) > max_len:
        snippet = snippet[: max_len - 3].rstrip() + "..."
    return snippet


__all__ = [
    "ResearchAgentConfig",
    "ResearchNotes",
    "build_research_agent_executor",
    "run_research_agent",
]

