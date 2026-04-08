"""MCP client manager — connects to MCP servers and discovers tools."""

from __future__ import annotations

import logging
import os
from typing import Any

from agenttree.mcp.types import McpServerConfig

logger = logging.getLogger(__name__)


class McpClientManager:
    """Manages connections to one or more MCP servers."""

    def __init__(self) -> None:
        self._sessions: dict[str, Any] = {}  # name -> (client, session) or transport objects
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

        if config.transport == "stdio":
            if not config.command:
                raise ValueError(f"MCP server '{config.name}' requires 'command' for stdio transport")

            env = {**os.environ, **config.env}
            server_params = StdioServerParameters(
                command=config.command,
                args=config.args,
                env=env,
            )

            read_stream, write_stream = await self._start_stdio(server_params)
            session = ClientSession(read_stream, write_stream)
            await session.initialize()
            self._sessions[config.name] = session

            # Discover tools
            tools_result = await session.list_tools()
            self._tools[config.name] = [
                {
                    "name": t.name,
                    "description": t.description or "",
                    "inputSchema": t.inputSchema if hasattr(t, "inputSchema") else {},
                }
                for t in tools_result.tools
            ]

        elif config.transport == "sse":
            if not config.url:
                raise ValueError(f"MCP server '{config.name}' requires 'url' for sse transport")

            from mcp.client.sse import sse_client  # noqa: F401

            read_stream, write_stream = await self._start_sse(config.url)
            session = ClientSession(read_stream, write_stream)
            await session.initialize()
            self._sessions[config.name] = session

            tools_result = await session.list_tools()
            self._tools[config.name] = [
                {
                    "name": t.name,
                    "description": t.description or "",
                    "inputSchema": t.inputSchema if hasattr(t, "inputSchema") else {},
                }
                for t in tools_result.tools
            ]

    async def _start_stdio(self, params: Any) -> tuple[Any, Any]:
        """Start a stdio transport. Returns (read_stream, write_stream)."""
        from mcp.client.stdio import stdio_client

        # stdio_client is an async context manager that yields (read, write)
        ctx = stdio_client(params)
        streams = await ctx.__aenter__()
        # Store the context manager so we can close it later
        self._sessions[f"_ctx_{id(streams)}"] = ctx
        return streams

    async def _start_sse(self, url: str) -> tuple[Any, Any]:
        """Start an SSE transport."""
        from mcp.client.sse import sse_client

        ctx = sse_client(url)
        streams = await ctx.__aenter__()
        self._sessions[f"_ctx_{id(streams)}"] = ctx
        return streams

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
        return "\n".join(parts)

    async def close_all(self) -> None:
        """Close all MCP server connections."""
        for name, session in list(self._sessions.items()):
            if name.startswith("_ctx_"):
                try:
                    await session.__aexit__(None, None, None)
                except Exception:
                    pass
            else:
                try:
                    # ClientSession doesn't always have a close method,
                    # but the context manager handles cleanup
                    pass
                except Exception:
                    pass
        self._sessions.clear()
        self._tools.clear()
