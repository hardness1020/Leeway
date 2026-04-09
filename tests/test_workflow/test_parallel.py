"""Tests for parallel execution models."""

import pytest
from leeway.workflow.parallel import BranchSpec, ParallelSpec, BranchResult
from leeway.workflow.types import ConditionSpec, ConditionType, NodeSpec, WorkflowDefinition, EdgeSpec


# -- BranchSpec --

def test_branch_spec_always_default():
    b = BranchSpec(prompt="test")
    assert b.condition.type == ConditionType.ALWAYS


def test_branch_spec_with_signal():
    b = BranchSpec(when={"signal": "needs_review"}, prompt="review")
    assert b.condition.type == ConditionType.SIGNAL
    assert b.condition.value == "needs_review"


def test_branch_spec_with_output_matches():
    b = BranchSpec(when={"output_matches": "ERROR"}, prompt="handle error")
    assert b.condition.type == ConditionType.OUTPUT_MATCHES


def test_branch_spec_requires_approval():
    b = BranchSpec(prompt="deploy", requires_approval=True)
    assert b.requires_approval is True


def test_branch_spec_with_scoping():
    b = BranchSpec(
        prompt="test",
        tools=["bash", "grep"],
        skills=["security"],
        hooks=[{"type": "command", "match": {"event": "after_tool_use"}, "command": "echo x"}],
        mcp_servers=["snyk"],
    )
    assert b.tools == ["bash", "grep"]
    assert b.skills == ["security"]
    assert len(b.hooks) == 1
    assert b.mcp_servers == ["snyk"]


# -- ParallelSpec --

def test_parallel_spec_valid():
    p = ParallelSpec(branches={
        "a": BranchSpec(prompt="task a"),
        "b": BranchSpec(prompt="task b"),
    })
    assert len(p.branches) == 2
    assert p.timeout == 600


def test_parallel_spec_empty_branches():
    with pytest.raises(ValueError, match="at least one branch"):
        ParallelSpec(branches={})


def test_parallel_spec_custom_timeout():
    p = ParallelSpec(
        branches={"a": BranchSpec(prompt="task")},
        timeout=120,
    )
    assert p.timeout == 120


# -- NodeSpec with parallel --

def test_node_spec_with_parallel():
    n = NodeSpec(
        parallel={
            "branches": {
                "a": {"prompt": "task a", "tools": ["bash"]},
                "b": {"when": {"signal": "flag"}, "prompt": "task b"},
            },
            "timeout": 300,
        },
        edges=[{"target": "next"}],
    )
    spec = n.get_parallel_spec()
    assert len(spec.branches) == 2
    assert spec.timeout == 300
    assert spec.branches["a"].condition.type == ConditionType.ALWAYS
    assert spec.branches["b"].condition.value == "flag"


def test_node_spec_parallel_none():
    n = NodeSpec(prompt="normal node")
    assert n.get_parallel_spec() is None


# -- WorkflowDefinition with parallel node --

def test_workflow_with_parallel_node():
    w = WorkflowDefinition(
        name="test",
        start_node="start",
        nodes={
            "start": NodeSpec(
                prompt="assess",
                edges=[EdgeSpec(target="parallel_step")],
            ),
            "parallel_step": NodeSpec(
                parallel={
                    "branches": {
                        "a": {"prompt": "branch a"},
                        "b": {"when": {"signal": "flag"}, "prompt": "branch b"},
                    },
                },
                edges=[EdgeSpec(target="end")],
            ),
            "end": NodeSpec(prompt="summarize"),
        },
    )
    assert w.nodes["parallel_step"].parallel is not None
    spec = w.nodes["parallel_step"].get_parallel_spec()
    assert len(spec.branches) == 2


def test_workflow_parallel_invalid_spec():
    with pytest.raises(ValueError, match="parallel node"):
        WorkflowDefinition(
            name="test",
            start_node="a",
            nodes={
                "a": NodeSpec(
                    parallel={"branches": {}},
                    edges=[EdgeSpec(target="b")],
                ),
                "b": NodeSpec(prompt="end"),
            },
        )


# -- BranchResult --

def test_branch_result_defaults():
    br = BranchResult(branch_name="test")
    assert br.triggered is True
    assert br.approved is True
    assert br.success is True
    assert br.final_text == ""
    assert br.tools_called == []


def test_branch_result_not_triggered():
    br = BranchResult(branch_name="test", triggered=False)
    assert br.triggered is False


def test_branch_result_failed():
    br = BranchResult(branch_name="test", success=False, error="timeout")
    assert br.success is False
    assert br.error == "timeout"
