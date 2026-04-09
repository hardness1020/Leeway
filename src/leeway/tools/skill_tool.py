"""Skill tool — loads skill content on demand with progressive disclosure."""

from __future__ import annotations

from pydantic import BaseModel, Field

from leeway.skills.registry import SkillRegistry
from leeway.tools.base import BaseTool, ToolExecutionContext, ToolResult


class SkillToolInput(BaseModel):
    """Input for the skill tool."""

    name: str = Field(description="Name of the skill to load")
    file: str | None = Field(
        default=None,
        description="Optional: read a supporting file from the skill folder (e.g. 'reference.md')",
    )


class SkillTool(BaseTool):
    """Load a skill's content into the conversation.

    Skills are folders in ~/.leeway/skills/ or <project>/.leeway/skills/
    containing a SKILL.md file with instructions the agent follows on demand.

    Supports progressive disclosure: SKILL.md is the main entry point,
    and supporting files (reference.md, examples.md, etc.) can be read
    on demand by passing the ``file`` parameter.
    """

    name = "skill"
    description = (
        "Load a skill by name. Returns the SKILL.md content. "
        "Pass file='<name>.md' to read a supporting file from the skill folder."
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

        # Read a supporting file from the skill folder
        if args.file is not None:
            content = skill.read_file(args.file)
            if content is None:
                files = skill.list_files()
                available_files = ", ".join(files) if files else "(none)"
                return ToolResult(
                    output=(
                        f"File '{args.file}' not found in skill '{args.name}'. "
                        f"Available files: {available_files}"
                    ),
                    is_error=True,
                )
            return ToolResult(output=content)

        # Return the main SKILL.md content + list supporting files if any
        output = skill.content
        files = skill.list_files()
        if files:
            output += f"\n\n---\nSupporting files available (use skill(name='{skill.name}', file='<name>') to read):\n"
            for f in files:
                output += f"  - {f}\n"
        return ToolResult(output=output)
