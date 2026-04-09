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


# ── Progressive disclosure tests ─────────────────────────────────────────────


@pytest.fixture
def folder_skill_registry(tmp_path: Path):
    """Registry with a folder-per-skill that has supporting files."""
    skill_dir = tmp_path / "security"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text("Main security instructions.")
    (skill_dir / "owasp.md").write_text("OWASP checklist content.")
    (skill_dir / "examples.md").write_text("Example findings.")

    registry = SkillRegistry()
    registry.register(SkillDefinition(
        name="security",
        content="Main security instructions.",
        dir_path=skill_dir,
    ))
    return registry


@pytest.mark.asyncio
async def test_load_skill_lists_supporting_files(folder_skill_registry, context):
    tool = SkillTool(skill_registry=folder_skill_registry)
    result = await tool.execute(SkillToolInput(name="security"), context)
    assert not result.is_error
    assert "Main security instructions" in result.output
    assert "owasp.md" in result.output
    assert "examples.md" in result.output
    assert "Supporting files available" in result.output


@pytest.mark.asyncio
async def test_read_supporting_file(folder_skill_registry, context):
    tool = SkillTool(skill_registry=folder_skill_registry)
    result = await tool.execute(SkillToolInput(name="security", file="owasp.md"), context)
    assert not result.is_error
    assert "OWASP checklist content" in result.output


@pytest.mark.asyncio
async def test_read_missing_supporting_file(folder_skill_registry, context):
    tool = SkillTool(skill_registry=folder_skill_registry)
    result = await tool.execute(SkillToolInput(name="security", file="nonexistent.md"), context)
    assert result.is_error
    assert "not found" in result.output
    assert "owasp.md" in result.output  # lists available files
