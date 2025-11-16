"""Unit tests for the ReAct research agent utilities."""

from __future__ import annotations

from unittest import mock

from lessons_agent.agent import (
    ResearchAgentConfig,
    ResearchNotes,
    _fallback_research_summary,
    build_research_agent_executor,
    run_research_agent,
)


@mock.patch("lessons_agent.agent.create_react_agent")
def test_build_research_agent_executor_wires_prompt(mock_create_agent):
    fake_runnable = mock.Mock()
    mock_create_agent.return_value = fake_runnable

    result = build_research_agent_executor(llm=mock.Mock())

    assert result is fake_runnable
    mock_create_agent.assert_called_once()


def test_run_research_agent_collects_notes():
    class StubExecutor:
        def __init__(self):
            self.calls = []

        def invoke(self, inputs, config=None):
            self.calls.append((inputs, config))
            return {"output": "Summary of findings.\nCitations: https://example.com"}

    stub = StubExecutor()
    config = ResearchAgentConfig(topic="LangChain Agents", level="beginner")

    notes = run_research_agent(config, agent_executor=stub)

    assert isinstance(notes, ResearchNotes)
    assert len(notes.entries) == 1
    captured_input, captured_config = stub.calls[0]
    assert captured_input["topic"] == "LangChain Agents"
    assert "Conduct deep research" in captured_input["input"]
    assert captured_config["max_execution_time"] == config.max_steps * 30


@mock.patch("lessons_agent.agent.ValyuSearchClient")
def test_fallback_research_summary_is_tool_agnostic(mock_client):
    mock_instance = mock.Mock()
    mock_instance.search.return_value = [
        {
            "title": "Insight A",
            "url": "https://example.com/a",
            "summary": "Practical steps for deploying RAG systems effectively.",
        },
        {
            "title": "Insight B",
            "url": "https://example.com/b",
            "summary": "Common pitfalls to avoid when curating retrieval corpora.",
        },
    ]
    mock_client.from_env.return_value = mock_instance

    config = ResearchAgentConfig(topic="RAG Best Practices", level="intermediate")
    summary, citations = _fallback_research_summary(config)

    assert summary.startswith("Key findings for RAG Best Practices")
    assert "Valyu" not in summary
    assert "Summary compiled from" not in summary
    assert citations == ["https://example.com/a", "https://example.com/b"]


if __name__ == "__main__":
    test_build_research_agent_executor_wires_prompt()
    test_run_research_agent_collects_notes()
    print("All Task 4 tests passed.")

