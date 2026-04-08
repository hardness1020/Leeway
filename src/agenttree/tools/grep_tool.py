"""Content search tool with a pure-Python fallback."""

from __future__ import annotations

import re
from pathlib import Path

from pydantic import BaseModel, Field

from agenttree.tools.base import BaseTool, ToolExecutionContext, ToolResult


class GrepToolInput(BaseModel):
    """Arguments for the grep tool."""

    pattern: str = Field(description="Regular expression to search for")
    root: str | None = Field(default=None, description="Search root directory")
    file_glob: str = Field(default="**/*")
    case_sensitive: bool = Field(default=True)
    limit: int = Field(default=200, ge=1, le=2000)


class GrepTool(BaseTool):
    """Search text files for a regex pattern."""

    name = "grep"
    description = "Search file contents with a regular expression."
    input_model = GrepToolInput

    def is_read_only(self, arguments: GrepToolInput) -> bool:
        del arguments
        return True

    async def execute(self, arguments: GrepToolInput, context: ToolExecutionContext) -> ToolResult:
        root = _resolve_path(context.cwd, arguments.root) if arguments.root else context.cwd
        flags = 0 if arguments.case_sensitive else re.IGNORECASE
        pattern = re.compile(arguments.pattern, flags)
        matches: list[str] = []

        for path in sorted(root.glob(arguments.file_glob)):
            if len(matches) >= arguments.limit:
                break
            if not path.is_file():
                continue
            try:
                raw = path.read_bytes()
            except OSError:
                continue
            if b"\x00" in raw:
                continue
            text = raw.decode("utf-8", errors="replace")
            for line_no, line in enumerate(text.splitlines(), start=1):
                if pattern.search(line):
                    matches.append(f"{path.relative_to(root)}:{line_no}:{line}")
                    if len(matches) >= arguments.limit:
                        break

        if not matches:
            return ToolResult(output="(no matches)")
        return ToolResult(output="\n".join(matches))


def _resolve_path(base: Path, candidate: str | None) -> Path:
    path = Path(candidate or ".").expanduser()
    if not path.is_absolute():
        path = base / path
    return path.resolve()
