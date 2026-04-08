"""Built-in tool registration."""

from agenttree.tools.agent_tool import AgentTool
from agenttree.tools.ask_user_question_tool import AskUserQuestionTool
from agenttree.tools.bash_tool import BashTool
from agenttree.tools.base import BaseTool, ToolExecutionContext, ToolRegistry, ToolResult
from agenttree.tools.cron_create_tool import CronCreateTool
from agenttree.tools.cron_delete_tool import CronDeleteTool
from agenttree.tools.cron_list_tool import CronListTool
from agenttree.tools.cron_toggle_tool import CronToggleTool
from agenttree.tools.file_edit_tool import FileEditTool
from agenttree.tools.file_read_tool import FileReadTool
from agenttree.tools.file_write_tool import FileWriteTool
from agenttree.tools.glob_tool import GlobTool
from agenttree.tools.grep_tool import GrepTool
from agenttree.tools.memory_tool import MemoryReadTool, MemoryWriteTool
from agenttree.tools.remote_trigger_tool import RemoteTriggerTool
from agenttree.tools.skill_tool import SkillTool
from agenttree.tools.task_create_tool import TaskCreateTool
from agenttree.tools.task_get_tool import TaskGetTool
from agenttree.tools.task_list_tool import TaskListTool
from agenttree.tools.task_stop_tool import TaskStopTool
from agenttree.tools.web_fetch_tool import WebFetchTool
from agenttree.tools.web_search_tool import WebSearchTool
from agenttree.tools.workflow_tool import WorkflowTool


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
