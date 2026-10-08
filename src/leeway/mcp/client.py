"""MCP client manager — connects to MCP servers and discovers tools."""

from __future__ import annotations

from contextlib import AsyncExitStack
import logging
import os
from typing import Any

from leeway.mcp.types import McpServerConfig

logger = logging.getLogger(__name__)


class McpClientManager:
    """Manages connections to one or more MCP servers."""

    def __init__(self) -> None:
        self._sessions: dict[str, Any] = {}  # name -> ClientSession
        self._connections: list[AsyncExitStack] = []
        self._tools: dict[str, list[dict[str, Any]]] = {}  # name -> tool list from server

    async def connect_all(self, configs: list[McpServerConfig]) -> None:
        """Connect to all configured MCP servers."""
        for config in configs:
            if not config.enabled:
                continue
            try:
                await self._connect(config)
                logger.info("Connected to MCP server: %s", config.name)
            except Exception:
                logger.warning("Failed to connect to MCP server: %s", config.name, exc_info=True)

    async def _connect(self, config: McpServerConfig) -> None:
        """Connect to a single MCP server and discover its tools."""
        try:
            from mcp import ClientSession, StdioServerParameters  # noqa: F401
            from mcp.client.stdio import stdio_client  # noqa: F401
        except ImportError:
            logger.warning(
                "mcp package not installed. Install with: pip install mcp"
            )
            return

        # Sessions run a background receive loop and must stay entered for calls.
        # Close each session before its transport, in reverse connection order.
        stack = AsyncExitStack()
        try:
            if config.transport == "stdio":
                if not config.command:
                    raise ValueError(
                        f"MCP server '{config.name}' requires 'command' for stdio transport"
                    )
                params = StdioServerParameters(
                    command=config.command,
                    args=config.args,
                    env={**os.environ, **config.env},
                )
                streams = await stack.enter_async_context(stdio_client(params))
            elif config.transport == "sse":
                if not config.url:
                    raise ValueError(f"MCP server '{config.name}' requires 'url' for sse transport")
                from mcp.client.sse import sse_client

                streams = await stack.enter_async_context(sse_client(config.url))
            else:
                if not config.url:
                    raise ValueError(
                        f"MCP server '{config.name}' requires 'url' for streamable_http transport"
                    )
                from mcp.client.streamable_http import streamablehttp_client

                streams = await stack.enter_async_context(
                    streamablehttp_client(config.url, headers={"User-Agent": "Leeway/0.1.0"})
                )

            session = await stack.enter_async_context(ClientSession(streams[0], streams[1]))
            await session.initialize()
            tools_result = await session.list_tools()
            tools = [
                {
                    "name": t.name,
                    "description": t.description or "",
                    "inputSchema": t.inputSchema,
                }
                for t in tools_result.tools
            ]
        except BaseException:
            await stack.aclose()
            raise
        self._connections.append(stack)
        self._sessions[config.name] = session
        self._tools[config.name] = tools

    def discover_tools(self, server_name: str) -> list[dict[str, Any]]:
        """Return the tool list for a connected server."""
        return self._tools.get(server_name, [])

    def list_all_tools(self) -> dict[str, list[dict[str, Any]]]:
        """Return all discovered tools grouped by server name."""
        return dict(self._tools)

    async def call_tool(
        self,
        server_name: str,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> str:
        """Call a tool on a connected MCP server."""
        session = self._sessions.get(server_name)
        if session is None:
            raise RuntimeError(f"MCP server not connected: {server_name}")

        result = await session.call_tool(tool_name, arguments)
        # Extract text content from the result
        parts: list[str] = []
        for content in result.content:
            if hasattr(content, "text"):
                parts.append(content.text)
            else:
                parts.append(str(content))
        output = "\n".join(parts)
        if result.isError:
            raise RuntimeError(output or f"MCP tool failed: {tool_name}")
        return output

    async def close_all(self) -> None:
        """Close all MCP server connections."""
        while self._connections:
            await self._connections.pop().aclose()
        self._sessions.clear()
        self._tools.clear()
