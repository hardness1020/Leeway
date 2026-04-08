"""Skill tool — loads skill content on demand."""

from __future__ import annotations

from pydantic import BaseModel, Field

from agenttree.skills.registry import SkillRegistry
from agenttree.tools.base import BaseTool, ToolExecutionContext, ToolResult


class SkillToolInput(BaseModel):
    """Input for the skill tool."""

    name: str = Field(description="Name of the skill to load")


class SkillTool(BaseTool):
    """Load a skill's content into the conversation.

    Skills are markdown files stored in ~/.agenttree/skills/ or
    <project>/.agenttree/skills/ that provide reusable prompts,
    instructions, or knowledge the agent can reference on demand.
    """

    name = "skill"
    description = (
        "Load a skill by name. Skills are reusable prompt templates "
        "and knowledge stored as markdown files."
    )
    input_model = SkillToolInput

    def __init__(self, *, skill_registry: SkillRegistry) -> None:
        self._registry = skill_registry

    def is_read_only(self, arguments: BaseModel) -> bool:
        return True

    async def execute(self, arguments: BaseModel, context: ToolExecutionContext) -> ToolResult:
        args = arguments if isinstance(arguments, SkillToolInput) else SkillToolInput.model_validate(arguments)
        skill = self._registry.get(args.name)
        if skill is None:
            available = ", ".join(s.name for s in self._registry.list_skills())
            return ToolResult(
                output=f"Skill '{args.name}' not found. Available skills: {available or '(none)'}",
                is_error=True,
            )
        return ToolResult(output=skill.content)
