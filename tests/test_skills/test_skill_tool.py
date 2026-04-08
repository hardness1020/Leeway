"""Tests for the skill tool."""

from pathlib import Path

import pytest

from agenttree.skills.registry import SkillRegistry
from agenttree.skills.types import SkillDefinition
from agenttree.tools.base import ToolExecutionContext
from agenttree.tools.skill_tool import SkillTool, SkillToolInput


@pytest.fixture
def skill_registry():
    registry = SkillRegistry()
    registry.register(SkillDefinition(name="review", content="Review the PR for bugs."))
    registry.register(SkillDefinition(name="test", content="Write tests for the code."))
    return registry


@pytest.fixture
def context(tmp_path: Path):
    return ToolExecutionContext(cwd=tmp_path)


@pytest.mark.asyncio
async def test_load_existing_skill(skill_registry, context):
    tool = SkillTool(skill_registry=skill_registry)
    result = await tool.execute(SkillToolInput(name="review"), context)
    assert not result.is_error
    assert "Review the PR" in result.output


@pytest.mark.asyncio
async def test_skill_not_found(skill_registry, context):
    tool = SkillTool(skill_registry=skill_registry)
    result = await tool.execute(SkillToolInput(name="missing"), context)
    assert result.is_error
    assert "not found" in result.output
    assert "review" in result.output  # lists available skills


@pytest.mark.asyncio
async def test_skill_tool_is_read_only(skill_registry):
    tool = SkillTool(skill_registry=skill_registry)
    assert tool.is_read_only(SkillToolInput(name="review")) is True
