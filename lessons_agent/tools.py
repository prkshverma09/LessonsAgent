"""LangChain tools for research (Valyu search, HTTP fetch, document loading)."""

from __future__ import annotations

import contextlib
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests
from bs4 import BeautifulSoup
from langchain_core.tools import tool
from pypdf import PdfReader

from lessons_agent.monitoring import log_event

ROOT_DIR = Path(__file__).resolve().parents[1]
RESOURCE_DIR = ROOT_DIR / "resources"


def _strip_html(html_text: str) -> str:
    soup = BeautifulSoup(html_text, "html.parser")
    return " ".join(soup.stripped_strings)


def _truncate(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 3] + "..."


@dataclass
class ValyuSearchClient:
    api_key: str
    base_url: str = "https://api.valyu.ai/v1"
    timeout: int = 30

    @classmethod
    def from_env(cls) -> "ValyuSearchClient":
        api_key = os.getenv("VALYU_API_KEY")
        if not api_key:
            raise ValueError("VALYU_API_KEY is not set in the environment.")
        base_url = os.getenv("VALYU_API_BASE_URL") or cls.base_url
        return cls(api_key=api_key, base_url=base_url.rstrip("/"))

    def search(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        payload = {
            "query": query,
            "search_type": "all",
            "max_num_results": max_results,
            "is_tool_call": True,
        }
        headers = {"Content-Type": "application/json", "x-api-key": self.api_key}
        response = requests.post(
            f"{self.base_url}/deepsearch", json=payload, headers=headers, timeout=self.timeout
        )
        try:
            response.raise_for_status()
        except requests.HTTPError as exc:
            detail = ""
            with contextlib.suppress(ValueError):
                detail = response.json().get("error", "")
            raise requests.HTTPError(
                f"Valyu search failed ({response.status_code}): {detail or response.text}"
            ) from exc
        data = response.json()
        if not data.get("success", True):
            raise RuntimeError(f"Valyu search error: {data.get('error', 'unknown error')}")
        results: List[Dict[str, Any]] = []
        for item in data.get("results", []):
            summary = item.get("summary") or item.get("snippet") or ""
            if item.get("content"):
                summary = summary or _strip_html(item["content"])
            summary = summary.strip()
            image_url = (
                item.get("image_url")
                or item.get("imageUrl")
                or item.get("thumbnail_url")
                or item.get("thumbnailUrl")
            )
            thumbnail_url = item.get("thumbnail_url") or item.get("thumbnailUrl")
            prompt_hint_source = item.get("image_prompt") or summary or item.get("title") or ""
            prompt_hint = _truncate(prompt_hint_source.strip(), 400) if prompt_hint_source else ""
            results.append(
                {
                    "title": item.get("title") or item.get("url"),
                    "url": item.get("url"),
                    "summary": summary,
                    "source": "valyu.ai",
                    "image_url": image_url,
                    "thumbnail_url": thumbnail_url,
                    "image_prompt_hint": prompt_hint,
                }
            )
        return results


def _resolve_path(path: str) -> Path:
    candidate = Path(path).expanduser()
    if candidate.is_absolute():
        return candidate
    direct = ROOT_DIR / path
    if direct.exists():
        return direct
    resource_candidate = RESOURCE_DIR / path
    if resource_candidate.exists():
        return resource_candidate
    raise FileNotFoundError(f"Could not locate document: {path}")


def _load_pdf(path: Path) -> str:
    with path.open("rb") as file:
        reader = PdfReader(file)
        texts: List[str] = []
        for page in reader.pages:
            page_text = page.extract_text() or ""
            texts.append(page_text.strip())
        return "\n\n".join(filter(None, texts))


def _load_text(path: Path) -> str:
    encoding = "utf-8"
    with path.open("r", encoding=encoding, errors="ignore") as file:
        return file.read()


def _load_document_content(resolved_path: Path) -> Dict[str, Any]:
    suffix = resolved_path.suffix.lower()
    if suffix == ".pdf":
        content = _load_pdf(resolved_path)
        doc_type = "pdf"
    else:
        content = _load_text(resolved_path)
        doc_type = "text"
    return {
        "path": str(resolved_path),
        "document_type": doc_type,
        "content": content,
        "size_bytes": resolved_path.stat().st_size,
    }


@tool("valyu_web_search", return_direct=False)
def valyu_web_search(query: str, max_results: int = 5) -> Dict[str, Any]:
    """Search the web using Valyu.ai and return high-signal snippets (max_results <= 10)."""

    if not query:
        raise ValueError("query must be provided.")
    max_results = max(1, min(max_results, 10))
    log_event("valyu_web_search_start", query=query, max_results=max_results)
    client = ValyuSearchClient.from_env()
    items = client.search(query=query, max_results=max_results)
    log_event("valyu_web_search_complete", results=len(items))
    return {"query": query, "results": items}


@tool("fetch_web_page", return_direct=False)
def fetch_web_page(url: str, max_chars: int = 6000) -> Dict[str, Any]:
    """Download and clean basic HTML content from a URL."""

    if not url:
        raise ValueError("url must be provided.")
    log_event("fetch_web_page_start", url=url)
    response = requests.get(url, timeout=30, headers={"User-Agent": "LessonsAgent/1.0"})
    response.raise_for_status()
    text = _strip_html(response.text)
    content = _truncate(text, max_chars)
    log_event("fetch_web_page_complete", url=url, chars=len(content))
    return {"url": url, "content": content}


@tool("load_local_resource", return_direct=False)
def load_local_resource(path: str) -> Dict[str, Any]:
    """Load local markdown/text/PDF files (absolute path or relative to repo/resources)."""

    if not path:
        raise ValueError("path must be provided.")
    resolved = _resolve_path(path)
    if not resolved.exists():
        raise FileNotFoundError(f"Document not found: {resolved}")
    if resolved.is_dir():
        raise IsADirectoryError(f"Expected a file but received a directory: {resolved}")
    log_event("load_local_resource_start", path=str(resolved))
    content = _load_document_content(resolved)
    log_event("load_local_resource_complete", path=str(resolved), bytes=content["size_bytes"])
    return content


__all__ = [
    "valyu_web_search",
    "fetch_web_page",
    "load_local_resource",
    "ValyuSearchClient",
]

