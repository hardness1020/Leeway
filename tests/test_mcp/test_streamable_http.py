"""Exercise HTTP MCP through settings, runtime registration and the agent loop."""

import json
from contextlib import asynccontextmanager
from types import SimpleNamespace

import httpx
import pytest

from leeway.api.client import ApiMessageCompleteEvent
from leeway.api.usage import UsageSnapshot
from leeway.engine.messages import ConversationMessage, TextBlock, ToolResultBlock, ToolUseBlock
from leeway.engine.stream_events import ToolExecutionCompleted
from leeway.mcp import McpClientManager, McpServerConfig
from leeway.ui.runtime import build_runtime, close_runtime

mcp = pytest.importorskip("mcp")

TOOLS = [
    {
        "name": "web_search",
        "description": "Search the web",
        "inputSchema": {
            "type": "object",
            "properties": {
                "objective": {"type": "string", "description": "Information to find"},
                "search_queries": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["objective", "search_queries"],
        },
    },
    {
        "name": "web_fetch",
        "description": "Fetch a page",
        "inputSchema": {
            "type": "object",
            "properties": {
                "urls": {"type": "array", "items": {"type": "string"}},
                "search_queries": {
                    "anyOf": [{"type": "array", "items": {"type": "string"}}, {"type": "null"}],
                    "default": None,
                },
            },
            "required": ["urls"],
        },
    },
]


class ScriptedModel:
    """Deterministic model responses; tool execution uses the real agent loop."""

    def __init__(self):
        self.turn = 0

    async def stream_message(self, request):
        schemas = {tool["name"]: tool for tool in request.tools}
        assert "mcp_parallel_web_search" in schemas
        assert "mcp_parallel_web_fetch" in schemas
        if self.turn:
            result = request.messages[-1].content[0]
            assert isinstance(result, ToolResultBlock)
            assert not result.is_error
            assert "https://example.com" in result.content
        if self.turn == 0:
            content = [ToolUseBlock(name="mcp_parallel_web_search", input={
                "objective": "Find an example page", "search_queries": ["example domain page"],
            })]
        elif self.turn == 1:
            content = [ToolUseBlock(name="mcp_parallel_web_fetch", input={
                "urls": ["https://example.com"], "search_queries": ["example domain page"],
            })]
        else:
            content = [TextBlock(text="Found and read the example page.")]
        self.turn += 1
        yield ApiMessageCompleteEvent(
            message=ConversationMessage(role="assistant", content=content), usage=UsageSnapshot(),
        )


@pytest.mark.asyncio
async def test_runtime_http_search_and_fetch(tmp_path, monkeypatch):
    from mcp.client import streamable_http

    requests = []

    def handle(request):
        assert str(request.url) == "https://search.parallel.ai/mcp"
        assert request.headers["User-Agent"] == "Leeway/0.1.0"
        assert "authorization" not in request.headers
        assert "x-api-key" not in request.headers
        if request.method != "POST":
            return httpx.Response(405)
        body = json.loads(request.content)
        requests.append(body)
        if "id" not in body:
            return httpx.Response(202)
        method = body["method"]
        if method == "initialize":
            result = {
                "protocolVersion": body["params"]["protocolVersion"],
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "fixture", "version": "1"},
            }
        elif method == "tools/list":
            result = {"tools": TOOLS}
        else:
            assert method == "tools/call"
            result = {"content": [{"type": "text", "text": "Example: https://example.com"}]}
        return httpx.Response(200, json={"jsonrpc": "2.0", "id": body["id"], "result": result})

    def factory(headers=None, timeout=None, auth=None):
        return httpx.AsyncClient(
            headers=headers, timeout=timeout, auth=auth, transport=httpx.MockTransport(handle),
        )

    real_transport = streamable_http.streamablehttp_client

    def transport(url, **kwargs):
        return real_transport(url, httpx_client_factory=factory, **kwargs)

    monkeypatch.setattr(streamable_http, "streamablehttp_client", transport)
    monkeypatch.setenv("AGENTTREE_CONFIG_DIR", str(tmp_path))
    monkeypatch.setenv("AGENTTREE_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.chdir(tmp_path)
    for key in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "PARALLEL_API_KEY"):
        monkeypatch.delenv(key, raising=False)
    (tmp_path / "settings.json").write_text(json.dumps({"mcp_servers": [{
        "name": "parallel", "transport": "streamable_http",
        "url": "https://search.parallel.ai/mcp",
    }]}))
    approvals = []

    async def approve(name, reason):
        approvals.append(name)
        return True

    model = ScriptedModel()
    bundle = await build_runtime(api_client=model, permission_prompt=approve)
    manager = bundle.engine._tool_metadata["mcp_manager"]
    try:
        events = [event async for event in bundle.engine.submit_message("Find and fetch an example")]
        results = [event for event in events if isinstance(event, ToolExecutionCompleted)]
        assert len(results) == 2
        assert all(not result.is_error for result in results)
        assert len(approvals) == 2
        assert model.turn == 3
        schema = bundle.tool_registry.get("mcp_parallel_web_search").to_api_schema()
        assert schema["input_schema"]["properties"]["objective"]["description"] == "Information to find"
        calls = [r["params"] for r in requests if r["method"] == "tools/call"]
        assert [call["name"] for call in calls] == ["web_search", "web_fetch"]
        assert calls[1]["arguments"]["search_queries"] == ["example domain page"]
    finally:
        await close_runtime(bundle)
    assert manager.list_all_tools() == {}
    assert not manager._sessions
    assert not manager._connections


@pytest.mark.asyncio
@pytest.mark.parametrize("transport", ["stdio", "sse", "streamable_http"])
async def test_connection_lifecycle(transport, monkeypatch):
    """All transports enter the session and release it before the transport."""
    from mcp.client import sse, stdio, streamable_http

    events = []

    @asynccontextmanager
    async def fake_transport(*args, **kwargs):
        events.append("transport entered")
        try:
            yield (None, None)
        finally:
            events.append("transport exited")

    class Session:
        def __init__(self, *args):
            pass

        async def __aenter__(self):
            events.append("session entered")
            return self

        async def __aexit__(self, *args):
            events.append("session exited")

        async def initialize(self):
            assert events[-1] == "session entered"

        async def list_tools(self):
            return SimpleNamespace(tools=[])

    monkeypatch.setattr(mcp, "ClientSession", Session)
    monkeypatch.setattr(stdio, "stdio_client", fake_transport)
    monkeypatch.setattr(sse, "sse_client", fake_transport)
    monkeypatch.setattr(streamable_http, "streamablehttp_client", fake_transport)
    manager = McpClientManager()
    assert McpServerConfig(name="default").transport == "stdio"
    await manager.connect_all([McpServerConfig(
        name="server", transport=transport, command="unused", url="https://example.com/mcp",
    )])
    await manager.close_all()
    assert events == ["transport entered", "session entered", "session exited", "transport exited"]


@pytest.mark.asyncio
async def test_disabled_and_invalid_http_servers():
    manager = McpClientManager()
    await manager.connect_all([
        McpServerConfig(name="disabled", transport="streamable_http", enabled=False),
        McpServerConfig(name="invalid", transport="streamable_http"),
    ])
    assert manager.list_all_tools() == {}
    assert not manager._connections


@pytest.mark.asyncio
async def test_remote_tool_error_is_not_success():
    from unittest.mock import AsyncMock

    from leeway.mcp.adapter import McpToolAdapter
    from leeway.tools.base import ToolExecutionContext
    from pathlib import Path

    manager = McpClientManager()
    manager._sessions["server"] = SimpleNamespace(call_tool=AsyncMock(return_value=SimpleNamespace(
        content=[SimpleNamespace(text="Rate limit reached")], isError=True,
    )))
    adapter = McpToolAdapter(
        server_name="server", tool_name="search", description="", input_schema={},
        mcp_manager=manager,
    )
    result = await adapter.execute(adapter.input_model(), ToolExecutionContext(cwd=Path.cwd()))
    assert result.is_error
    assert result.output == "MCP tool error: Rate limit reached"


@pytest.mark.asyncio
async def test_failed_initialization_releases_connection(monkeypatch):
    from mcp.client import streamable_http

    events = []

    @asynccontextmanager
    async def transport(*args, **kwargs):
        try:
            yield (None, None)
        finally:
            events.append("transport closed")

    class Session:
        def __init__(self, *args):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            events.append("session closed")

        async def initialize(self):
            raise RuntimeError("Connection failed")

    monkeypatch.setattr(streamable_http, "streamablehttp_client", transport)
    monkeypatch.setattr(mcp, "ClientSession", Session)
    manager = McpClientManager()
    await manager.connect_all([McpServerConfig(
        name="broken", transport="streamable_http", url="https://example.com/mcp",
    )])
    assert events == ["session closed", "transport closed"]
    assert manager.list_all_tools() == {}
    assert not manager._connections
