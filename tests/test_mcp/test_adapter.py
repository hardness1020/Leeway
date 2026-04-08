"""Tests for MCP tool adapter."""

from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from agenttree.mcp.adapter import McpToolAdapter, _build_input_model, register_mcp_tools
from agenttree.mcp.client import McpClientManager
from agenttree.tools.base import ToolExecutionContext, ToolRegistry


def test_build_input_model_basic():
    model = _build_input_model("test", {
        "properties": {
            "query": {"type": "string", "description": "Search query"},
            "count": {"type": "integer", "default": 5},
        },
        "required": ["query"],
    })
    assert "query" in model.model_fields
    assert "count" in model.model_fields

    instance = model(query="hello")
    assert instance.query == "hello"


def test_build_input_model_empty():
    model = _build_input_model("empty", {})
    instance = model()
    assert instance is not None


@pytest.mark.asyncio
async def test_adapter_execute():
    manager = McpClientManager()
    manager.call_tool = AsyncMock(return_value="result text")

    adapter = McpToolAdapter(
        server_name="test_server",
        tool_name="search",
        description="Search things",
        input_schema={
            "properties": {"query": {"type": "string"}},
            "required": ["query"],
        },
        mcp_manager=manager,
    )

    assert adapter.name == "mcp_test_server_search"
    ctx = ToolExecutionContext(cwd=Path("/tmp"))
    args = adapter.input_model(query="hello")
    result = await adapter.execute(args, ctx)

    assert not result.is_error
    assert result.output == "result text"
    manager.call_tool.assert_called_once_with("test_server", "search", {"query": "hello"})


@pytest.mark.asyncio
async def test_adapter_execute_error():
    manager = McpClientManager()
    manager.call_tool = AsyncMock(side_effect=RuntimeError("connection lost"))

    adapter = McpToolAdapter(
        server_name="srv",
        tool_name="broken",
        description="",
        input_schema={},
        mcp_manager=manager,
    )

    ctx = ToolExecutionContext(cwd=Path("/tmp"))
    args = adapter.input_model()
    result = await adapter.execute(args, ctx)
    assert result.is_error
    assert "connection lost" in result.output


def test_register_mcp_tools():
    manager = McpClientManager()
    manager._tools = {
        "server1": [
            {"name": "tool_a", "description": "A", "inputSchema": {}},
            {"name": "tool_b", "description": "B", "inputSchema": {}},
        ]
    }

    registry = ToolRegistry()
    count = register_mcp_tools(registry, manager)
    assert count == 2
    assert registry.get("mcp_server1_tool_a") is not None
    assert registry.get("mcp_server1_tool_b") is not None
