# Tools (21+)

| Category | Tools | Description |
|----------|-------|-------------|
| **File I/O** | `bash`, `read_file`, `write_file`, `edit_file`, `glob`, `grep` | Core file operations with permission checks |
| **Web** | `web_fetch`, `web_search` | HTTP content retrieval and Brave search |
| **Interaction** | `ask_user_question`, `skill` | User input and on-demand knowledge loading |
| **Tasks** | `task_create`, `task_list`, `task_get`, `task_stop` | Background task lifecycle management |
| **Scheduling** | `cron_create`, `cron_list`, `cron_delete`, `cron_toggle` | Cron job management |
| **Agents** | `agent`, `remote_trigger` | Subagent spawning and webhook triggers |
| **Memory** | `memory_read`, `memory_write` | Persistent cross-session knowledge |
| **MCP** | `mcp_<server>_<tool>` (dynamic) | Auto-registered from MCP servers |

Every tool has **Pydantic input validation**, **self-describing JSON Schema**, **permission integration**, and **hook support**.

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
