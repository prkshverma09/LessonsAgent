"""Unit tests for research tools."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict
from unittest import mock

from lessons_agent import tools


def _mock_response(json_payload: Dict[str, Any]) -> mock.Mock:
    response = mock.Mock()
    response.json.return_value = json_payload
    response.raise_for_status = mock.Mock()
    response.text = "<html><body>Hello world</body></html>"
    return response


@mock.patch("lessons_agent.tools.requests.post")
def test_valyu_web_search_tool(mock_post: mock.Mock) -> None:
    os.environ["VALYU_API_KEY"] = "test-key"
    mock_post.return_value = _mock_response(
        {
            "results": [
                {
                    "title": "Result A",
                    "url": "https://example.com/a",
                    "summary": "Summary A",
                    "image_url": "https://example.com/a.png",
                    "thumbnail_url": "https://example.com/thumb-a.png",
                    "image_prompt": "Diagram of concept A",
                }
            ]
        }
    )
    result = tools.valyu_web_search.invoke({"query": "langchain", "max_results": 3})
    assert result["query"] == "langchain"
    assert result["results"][0]["title"] == "Result A"
    assert result["results"][0]["image_url"] == "https://example.com/a.png"
    assert "image_prompt_hint" in result["results"][0]
    mock_post.assert_called_once()


@mock.patch("lessons_agent.tools.requests.get")
def test_fetch_web_page_tool(mock_get: mock.Mock) -> None:
    mock_resp = _mock_response({})
    mock_resp.text = "<html><head><title>Test</title></head><body><p>Body text</p></body></html>"
    mock_get.return_value = mock_resp

    payload = tools.fetch_web_page.invoke({"url": "https://example.com"})
    assert "Body text" in payload["content"]
    mock_get.assert_called_once()


def test_load_local_resource_markdown() -> None:
    relative_path = "resources/TRACK_A_RESOURCES.md"
    result = tools.load_local_resource.invoke({"path": relative_path})
    assert result["document_type"] == "text"
    assert len(result["content"]) > 0


def test_load_local_resource_pdf() -> None:
    pdf_path = "resources/api-guide.pdf"
    result = tools.load_local_resource.invoke({"path": pdf_path})
    assert result["document_type"] == "pdf"
    assert isinstance(result["content"], str)


if __name__ == "__main__":
    test_valyu_web_search_tool()
    test_fetch_web_page_tool()
    test_load_local_resource_markdown()
    test_load_local_resource_pdf()
    print("All Task 3 tests passed.")

