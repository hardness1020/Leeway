"""MCP tool adapter — wraps an MCP server tool as an Leeway BaseTool."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, create_model

from leeway.mcp.client import McpClientManager
from leeway.tools.base import BaseTool, ToolExecutionContext, ToolResult


def _build_input_model(
    tool_name: str,
    input_schema: dict[str, Any],
) -> type[BaseModel]:
    """Dynamically create a Pydantic model from a JSON Schema."""
    properties = input_schema.get("properties", {})
    required = set(input_schema.get("required", []))

    fields: dict[str, Any] = {}
    for prop_name, prop_schema in properties.items():
        python_type = _json_type_to_python(prop_schema.get("type", "string"))
        if prop_name in required:
            fields[prop_name] = (python_type, ...)
        else:
            default = prop_schema.get("default")
            fields[prop_name] = (python_type | None, default)

    model_name = f"Mcp_{tool_name}_Input"
    return create_model(model_name, **fields)


def _json_type_to_python(json_type: str) -> type:
    mapping: dict[str, type] = {
        "string": str,
        "integer": int,
        "number": float,
        "boolean": bool,
        "object": dict,
        "array": list,
    }
    return mapping.get(json_type, str)


class McpToolAdapter(BaseTool):
    """Wraps a single MCP server tool as an Leeway BaseTool."""

    def __init__(
        self,
        *,
        server_name: str,
        tool_name: str,
        description: str,
        input_schema: dict[str, Any],
        mcp_manager: McpClientManager,
    ) -> None:
        self._server_name = server_name
        self._tool_name = tool_name
        self._mcp_manager = mcp_manager

        self.name = f"mcp_{server_name}_{tool_name}"
        self.description = description or f"MCP tool: {tool_name} from {server_name}"
        self.input_model = _build_input_model(tool_name, input_schema)

    def is_read_only(self, arguments: BaseModel) -> bool:
        # MCP tools are treated as potentially mutating by default
        return False

    async def execute(self, arguments: BaseModel, context: ToolExecutionContext) -> ToolResult:
        args_dict = arguments.model_dump(exclude_none=True)
        try:
            output = await self._mcp_manager.call_tool(
                self._server_name,
                self._tool_name,
                args_dict,
            )
            return ToolResult(output=output)
        except Exception as exc:
            return ToolResult(output=f"MCP tool error: {exc}", is_error=True)


def register_mcp_tools(
    registry: Any,  # ToolRegistry
    mcp_manager: McpClientManager,
) -> int:
    """Register all discovered MCP tools into a ToolRegistry.

    Returns the number of tools registered.
    """
    count = 0
    for server_name, tools in mcp_manager.list_all_tools().items():
        for tool_spec in tools:
            adapter = McpToolAdapter(
                server_name=server_name,
                tool_name=tool_spec["name"],
                description=tool_spec.get("description", ""),
                input_schema=tool_spec.get("inputSchema", {}),
                mcp_manager=mcp_manager,
            )
            registry.register(adapter)
            count += 1
    return count
