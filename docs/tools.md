# Tools (21+)

| Category | Tools | Description |
|----------|-------|-------------|
| **File I/O** | `bash`, `read_file`, `write_file`, `edit_file`, `glob`, `grep` | Core file operations with permission checks |
| **Web** | `web_fetch`, `web_search` | HTTP content retrieval and configurable web search (Brave or you.com) |
| **Interaction** | `ask_user_question`, `skill` | User input and on-demand knowledge loading |
| **Tasks** | `task_create`, `task_list`, `task_get`, `task_stop` | Background task lifecycle management |
| **Scheduling** | `cron_create`, `cron_list`, `cron_delete`, `cron_toggle` | Cron job management |
| **Agents** | `agent`, `remote_trigger` | Subagent spawning and webhook triggers |
| **Memory** | `memory_read`, `memory_write` | Persistent cross-session knowledge |
| **MCP** | `mcp_<server>_<tool>` (dynamic) | Auto-registered from MCP servers |

Every tool has **Pydantic input validation**, **self-describing JSON Schema**, **permission integration**, and **hook support**.

## Web Search Provider Setup

`web_search` supports two providers via environment variables:

```bash
# Default provider (backward compatible)
export WEB_SEARCH_PROVIDER=brave
export BRAVE_SEARCH_API_KEY=your_brave_key

# Optional provider: you.com Search API
export WEB_SEARCH_PROVIDER=you
export YDC_API_KEY=your_you_api_key
```

Usage in prompts/workflows remains unchanged:

```text
Use web_search with query: "latest model context protocol updates"
```

## Custom Tool

```python
from pydantic import BaseModel, Field
from leeway.tools.base import BaseTool, ToolExecutionContext, ToolResult

class MyToolInput(BaseModel):
    query: str = Field(description="Search query")

class MyTool(BaseTool):
    name = "my_tool"
    description = "Does something useful"
    input_model = MyToolInput

    async def execute(self, arguments: MyToolInput, context: ToolExecutionContext) -> ToolResult:
        return ToolResult(output=f"Result for: {arguments.query}")
```
