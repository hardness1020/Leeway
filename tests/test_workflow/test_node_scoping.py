"""Tests for node-level skills, hooks, and MCP scoping."""

import pytest
from leeway.workflow.types import NodeSpec, WorkflowDefinition, EdgeSpec, ConditionSpec


def test_node_spec_with_skills():
    n = NodeSpec(prompt="test", skills=["code_review", "security"])
    assert n.skills == ["code_review", "security"]


def test_node_spec_with_hooks():
    hook = {"type": "command", "match": {"event": "after_tool_use"}, "command": "echo hi"}
    n = NodeSpec(prompt="test", hooks=[hook])
    assert len(n.hooks) == 1
    assert n.hooks[0]["type"] == "command"


def test_node_spec_with_mcp_servers():
    n = NodeSpec(prompt="test", mcp_servers=["github", "snyk"])
    assert n.mcp_servers == ["github", "snyk"]


def test_node_spec_defaults_empty():
    n = NodeSpec(prompt="test")
    assert n.skills == []
    assert n.hooks == []
    assert n.mcp_servers == []
    assert n.parallel is None


def test_workflow_global_skills():
    w = WorkflowDefinition(
        name="test",
        start_node="a",
        nodes={"a": NodeSpec(prompt="x")},
        global_skills=["coding_standards"],
    )
    assert w.global_skills == ["coding_standards"]


def test_workflow_global_hooks():
    hook = {"type": "http", "match": {"event": "before_tool_use"}, "url": "http://example.com"}
    w = WorkflowDefinition(
        name="test",
        start_node="a",
        nodes={"a": NodeSpec(prompt="x")},
        global_hooks=[hook],
    )
    assert len(w.global_hooks) == 1


def test_workflow_global_mcp_servers():
    w = WorkflowDefinition(
        name="test",
        start_node="a",
        nodes={"a": NodeSpec(prompt="x")},
        global_mcp_servers=["github"],
    )
    assert w.global_mcp_servers == ["github"]


def test_backward_compatible_no_new_fields():
    """Existing workflows without new fields still parse correctly."""
    w = WorkflowDefinition(
        name="test",
        start_node="a",
        nodes={
            "a": NodeSpec(
                prompt="do something",
                tools=["bash"],
                edges=[EdgeSpec(target="b", when=ConditionSpec(signal="done"))],
            ),
            "b": NodeSpec(prompt="finish"),
        },
        global_tools=["read_file"],
    )
    assert w.nodes["a"].skills == []
    assert w.nodes["a"].hooks == []
    assert w.nodes["a"].mcp_servers == []
    assert w.global_skills == []
    assert w.global_hooks == []
    assert w.global_mcp_servers == []
