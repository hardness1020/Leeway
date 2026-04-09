"""Built-in tool registration."""

from leeway.tools.agent_tool import AgentTool
from leeway.tools.ask_user_question_tool import AskUserQuestionTool
from leeway.tools.bash_tool import BashTool
from leeway.tools.base import BaseTool, ToolExecutionContext, ToolRegistry, ToolResult
from leeway.tools.cron_create_tool import CronCreateTool
from leeway.tools.cron_delete_tool import CronDeleteTool
from leeway.tools.cron_list_tool import CronListTool
from leeway.tools.cron_toggle_tool import CronToggleTool
from leeway.tools.file_edit_tool import FileEditTool
from leeway.tools.file_read_tool import FileReadTool
from leeway.tools.file_write_tool import FileWriteTool
from leeway.tools.glob_tool import GlobTool
from leeway.tools.grep_tool import GrepTool
from leeway.tools.memory_tool import MemoryReadTool, MemoryWriteTool
from leeway.tools.remote_trigger_tool import RemoteTriggerTool
from leeway.tools.skill_tool import SkillTool
from leeway.tools.task_create_tool import TaskCreateTool
from leeway.tools.task_get_tool import TaskGetTool
from leeway.tools.task_list_tool import TaskListTool
from leeway.tools.task_stop_tool import TaskStopTool
from leeway.tools.web_fetch_tool import WebFetchTool
from leeway.tools.web_search_tool import WebSearchTool
from leeway.tools.workflow_tool import WorkflowTool


def create_default_tool_registry() -> ToolRegistry:
    """Return the default built-in tool registry."""
    registry = ToolRegistry()
    for tool in (
        BashTool(),
        AskUserQuestionTool(),
        FileReadTool(),
        FileWriteTool(),
        FileEditTool(),
        GlobTool(),
        GrepTool(),
        WebFetchTool(),
        WebSearchTool(),
        TaskCreateTool(),
        TaskListTool(),
        TaskGetTool(),
        TaskStopTool(),
        CronCreateTool(),
        CronListTool(),
        CronDeleteTool(),
        CronToggleTool(),
        RemoteTriggerTool(),
        AgentTool(),
        MemoryReadTool(),
        MemoryWriteTool(),
    ):
        registry.register(tool)
    return registry


__all__ = [
    "BaseTool",
    "SkillTool",
    "ToolExecutionContext",
    "ToolRegistry",
    "ToolResult",
    "WorkflowTool",
    "create_default_tool_registry",
]
