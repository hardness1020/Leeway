"""Memory read/write tools."""

from __future__ import annotations

from pydantic import BaseModel, Field

from leeway.tools.base import BaseTool, ToolExecutionContext, ToolResult


class MemoryReadInput(BaseModel):
    """Input for reading memory."""

    action: str = Field(description="Action: 'get', 'list', 'search', or 'delete'")
    name: str | None = Field(default=None, description="Memory name (for get/delete)")
    query: str | None = Field(default=None, description="Search query (for search)")


class MemoryReadTool(BaseTool):
    """Read, list, search, or delete persistent memory entries."""

    name = "memory_read"
    description = "Read, list, search, or delete persistent memory entries."
    input_model = MemoryReadInput

    def is_read_only(self, arguments: BaseModel) -> bool:
        args = arguments if isinstance(arguments, MemoryReadInput) else MemoryReadInput.model_validate(arguments)
        return args.action != "delete"

    async def execute(self, arguments: BaseModel, context: ToolExecutionContext) -> ToolResult:
        args = arguments if isinstance(arguments, MemoryReadInput) else MemoryReadInput.model_validate(arguments)

        from leeway.memory.store import MemoryStore

        store: MemoryStore | None = context.metadata.get("memory_store")
        if store is None:
            store = MemoryStore()

        if args.action == "list":
            entries = store.list()
            if not entries:
                return ToolResult(output="No memory entries.")
            lines = [f"{'Name':<25} {'Description'}"]
            lines.append("-" * 60)
            for e in entries:
                lines.append(f"{e.name[:23]:<25} {e.description[:35]}")
            return ToolResult(output="\n".join(lines))

        if args.action == "get":
            if not args.name:
                return ToolResult(output="'name' required for get.", is_error=True)
            entry = store.get(args.name)
            if entry is None:
                return ToolResult(output=f"Memory not found: {args.name}", is_error=True)
            return ToolResult(output=f"# {entry.name}\n\n{entry.content}")

        if args.action == "search":
            if not args.query:
                return ToolResult(output="'query' required for search.", is_error=True)
            results = store.search(args.query)
            if not results:
                return ToolResult(output=f"No memories matching '{args.query}'.")
            lines = [f"Found {len(results)} result(s):"]
            for e in results:
                lines.append(f"  - {e.name}: {e.description}")
            return ToolResult(output="\n".join(lines))

        if args.action == "delete":
            if not args.name:
                return ToolResult(output="'name' required for delete.", is_error=True)
            if store.delete(args.name):
                return ToolResult(output=f"Memory '{args.name}' deleted.")
            return ToolResult(output=f"Memory not found: {args.name}", is_error=True)

        return ToolResult(output=f"Unknown action: {args.action}", is_error=True)


class MemoryWriteInput(BaseModel):
    """Input for writing memory."""

    name: str = Field(description="Memory entry name")
    content: str = Field(description="Memory content (markdown)")
    description: str = Field(default="", description="One-line description")
    tags: list[str] = Field(default_factory=list, description="Tags for categorization")


class MemoryWriteTool(BaseTool):
    """Save a persistent memory entry."""

    name = "memory_write"
    description = "Save a persistent memory entry that persists across sessions."
    input_model = MemoryWriteInput

    async def execute(self, arguments: BaseModel, context: ToolExecutionContext) -> ToolResult:
        args = arguments if isinstance(arguments, MemoryWriteInput) else MemoryWriteInput.model_validate(arguments)

        from leeway.memory.store import MemoryStore
        from leeway.memory.types import MemoryEntry

        store: MemoryStore | None = context.metadata.get("memory_store")
        if store is None:
            store = MemoryStore()

        entry = MemoryEntry(
            name=args.name,
            description=args.description,
            content=args.content,
            tags=args.tags,
        )
        path = store.save(entry)
        return ToolResult(output=f"Memory saved: '{args.name}' at {path}")
