"""Tests for workflow resource validation."""

from unittest.mock import MagicMock

from agenttree.permissions.checker import PermissionChecker
from agenttree.skills.registry import SkillRegistry
from agenttree.skills.types import SkillDefinition
from agenttree.tools.base import BaseTool, ToolRegistry, ToolExecutionContext, ToolResult
from agenttree.workflow.engine import WorkflowEngine
from agenttree.workflow.types import EdgeSpec, NodeSpec, WorkflowDefinition

from pathlib import Path
from pydantic import BaseModel


class _DummyInput(BaseModel):
    pass


class _DummyTool(BaseTool):
    input_model = _DummyInput

    def __init__(self, name: str):
        self.name = name
        self.description = name

    async def execute(self, arguments, context):
        return ToolResult(output="ok")


def _make_tool_registry(*names: str) -> ToolRegistry:
    reg = ToolRegistry()
    for n in names:
        reg.register(_DummyTool(n))
    return reg


def _make_skill_registry(*names: str) -> SkillRegistry:
    reg = SkillRegistry()
    for n in names:
        reg.register(SkillDefinition(name=n, content=f"Skill {n}"))
    return reg


def _make_engine(
    wf: WorkflowDefinition,
    tools: list[str] | None = None,
    skills: list[str] | None = None,
    mcp_tools: list[str] | None = None,
) -> WorkflowEngine:
    tool_names = list(tools or []) + [f"mcp_{n}" for n in (mcp_tools or [])]
    tool_reg = _make_tool_registry(*tool_names)
    skill_reg = _make_skill_registry(*(skills or []))
    return WorkflowEngine(
        workflow=wf,
        api_client=MagicMock(),
        full_tool_registry=tool_reg,
        permission_checker=PermissionChecker({}),
        cwd=Path("."),
        model="test",
        tool_metadata={
            "skill_registry": skill_reg,
        },
    )


# -- Valid workflows --

def test_validate_clean_workflow():
    wf = WorkflowDefinition(
        name="test", start_node="a",
        nodes={
            "a": NodeSpec(prompt="do", tools=["bash"]),
        },
    )
    engine = _make_engine(wf, tools=["bash"])
    assert engine.validate_resources() == []


def test_validate_clean_with_skills():
    wf = WorkflowDefinition(
        name="test", start_node="a",
        nodes={
            "a": NodeSpec(prompt="do", skills=["review"]),
        },
    )
    engine = _make_engine(wf, skills=["review"])
    assert engine.validate_resources() == []


# -- Missing tools --

def test_validate_missing_tool():
    wf = WorkflowDefinition(
        name="test", start_node="a",
        nodes={
            "a": NodeSpec(prompt="do", tools=["nonexistent"]),
        },
    )
    engine = _make_engine(wf, tools=["bash"])
    warnings = engine.validate_resources()
    assert len(warnings) == 1
    assert "nonexistent" in warnings[0]
    assert "not found" in warnings[0]


# -- Missing skills --

def test_validate_missing_skill():
    wf = WorkflowDefinition(
        name="test", start_node="a",
        nodes={
            "a": NodeSpec(prompt="do", skills=["nonexistent"]),
        },
    )
    engine = _make_engine(wf, skills=["review"])
    warnings = engine.validate_resources()
    assert len(warnings) == 1
    assert "nonexistent" in warnings[0]


def test_validate_missing_global_skill():
    wf = WorkflowDefinition(
        name="test", start_node="a",
        nodes={"a": NodeSpec(prompt="do")},
        global_skills=["missing_skill"],
    )
    engine = _make_engine(wf, skills=["other"])
    warnings = engine.validate_resources()
    assert any("missing_skill" in w for w in warnings)


# -- Missing MCP servers --

def test_validate_missing_mcp_server():
    wf = WorkflowDefinition(
        name="test", start_node="a",
        nodes={
            "a": NodeSpec(prompt="do", mcp_servers=["nonexistent"]),
        },
    )
    engine = _make_engine(wf, mcp_tools=["github_issues"])
    warnings = engine.validate_resources()
    assert len(warnings) == 1
    assert "nonexistent" in warnings[0]


def test_validate_mcp_server_present():
    wf = WorkflowDefinition(
        name="test", start_node="a",
        nodes={
            "a": NodeSpec(prompt="do", mcp_servers=["github"]),
        },
    )
    engine = _make_engine(wf, mcp_tools=["github_issues"])
    assert engine.validate_resources() == []


# -- Invalid hooks --

def test_validate_invalid_hook_type():
    wf = WorkflowDefinition(
        name="test", start_node="a",
        nodes={
            "a": NodeSpec(prompt="do", hooks=[{"type": "fax"}]),
        },
    )
    engine = _make_engine(wf)
    warnings = engine.validate_resources()
    assert any("unknown type" in w for w in warnings)


def test_validate_invalid_hook_definition():
    wf = WorkflowDefinition(
        name="test", start_node="a",
        nodes={
            "a": NodeSpec(prompt="do", hooks=[
                {"type": "command"}  # missing 'match' and 'command' fields
            ]),
        },
    )
    engine = _make_engine(wf)
    warnings = engine.validate_resources()
    assert any("invalid" in w.lower() for w in warnings)


def test_validate_valid_hook():
    wf = WorkflowDefinition(
        name="test", start_node="a",
        nodes={
            "a": NodeSpec(prompt="do", hooks=[
                {
                    "type": "command",
                    "match": {"event": "after_tool_use"},
                    "command": "echo hi",
                }
            ]),
        },
    )
    engine = _make_engine(wf)
    assert engine.validate_resources() == []


# -- Parallel branch validation --

def test_validate_parallel_branch_missing_skill():
    wf = WorkflowDefinition(
        name="test", start_node="a",
        nodes={
            "a": NodeSpec(
                parallel={
                    "branches": {
                        "review": {
                            "prompt": "review",
                            "skills": ["nonexistent"],
                        },
                    },
                },
                edges=[{"target": "b"}],
            ),
            "b": NodeSpec(prompt="end"),
        },
    )
    engine = _make_engine(wf, skills=["other"])
    warnings = engine.validate_resources()
    assert any("nonexistent" in w and "branch 'review'" in w for w in warnings)


def test_validate_parallel_branch_missing_tool():
    wf = WorkflowDefinition(
        name="test", start_node="a",
        nodes={
            "a": NodeSpec(
                parallel={
                    "branches": {
                        "test": {
                            "prompt": "run tests",
                            "tools": ["missing_tool"],
                        },
                    },
                },
                edges=[{"target": "b"}],
            ),
            "b": NodeSpec(prompt="end"),
        },
    )
    engine = _make_engine(wf, tools=["bash"])
    warnings = engine.validate_resources()
    assert any("missing_tool" in w and "branch 'test'" in w for w in warnings)
