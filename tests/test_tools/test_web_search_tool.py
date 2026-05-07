from __future__ import annotations

from pathlib import Path

import httpx
import pytest

from leeway.tools.base import ToolExecutionContext
from leeway.tools.web_search_tool import WebSearchInput, WebSearchTool


class _MockResponse:
    def __init__(self, payload: dict, status_code: int = 200):
        self._payload = payload
        self.status_code = status_code

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return self._payload


class _MockAsyncClient:
    def __init__(self, payload: dict | None = None, responses: list[_MockResponse] | None = None):
        self.payload = payload or {}
        self.responses = responses or []
        self.called = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def get(self, url: str, params: dict, headers: dict):
        self.called.append({"url": url, "params": params, "headers": headers})
        if self.responses:
            return self.responses.pop(0)
        return _MockResponse(self.payload)


@pytest.mark.asyncio
async def test_web_search_you_provider_success(monkeypatch):
    tool = WebSearchTool()
    context = ToolExecutionContext(cwd=Path("."))

    monkeypatch.setenv("WEB_SEARCH_PROVIDER", "you")
    monkeypatch.setenv("YDC_API_KEY", "test-key")

    mock_client = _MockAsyncClient(
        {
            "results": {
                "web": [
                    {
                        "title": "Result A",
                        "url": "https://example.com/a",
                        "snippets": ["Snippet A"],
                        "description": "Fallback description",
                    }
                ]
            }
        }
    )

    monkeypatch.setattr(httpx, "AsyncClient", lambda timeout=15.0: mock_client)

    result = await tool.execute(WebSearchInput(query="test", num_results=1), context)

    assert not result.is_error
    assert "Result A" in result.output
    assert "https://api.ydc-index.io/v1/search" in mock_client.called[0]["url"]
    assert mock_client.called[0]["params"]["query"] == "test"
    assert mock_client.called[0]["params"]["count"] == 1


@pytest.mark.asyncio
async def test_web_search_you_provider_without_key(monkeypatch):
    tool = WebSearchTool()
    context = ToolExecutionContext(cwd=Path("."))

    monkeypatch.setenv("WEB_SEARCH_PROVIDER", "you")
    monkeypatch.delenv("YDC_API_KEY", raising=False)

    mock_client = _MockAsyncClient(
        {
            "results": {
                "web": [
                    {
                        "title": "Result A",
                        "url": "https://example.com/a",
                        "description": "Fallback description",
                    }
                ]
            }
        }
    )
    monkeypatch.setattr(httpx, "AsyncClient", lambda timeout=15.0: mock_client)

    result = await tool.execute(WebSearchInput(query="test"), context)

    assert not result.is_error
    assert "Result A" in result.output
    assert "X-API-Key" not in mock_client.called[0]["headers"]


@pytest.mark.asyncio
async def test_web_search_invalid_provider(monkeypatch):
    tool = WebSearchTool()
    context = ToolExecutionContext(cwd=Path("."))

    monkeypatch.setenv("WEB_SEARCH_PROVIDER", "invalid")

    result = await tool.execute(WebSearchInput(query="test"), context)

    assert result.is_error
    assert "Unsupported WEB_SEARCH_PROVIDER" in result.output
