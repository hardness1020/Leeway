"""Tests for parallel node execution in the workflow engine."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from leeway.workflow.engine import WorkflowEngine, _branch_result_to_dict
from leeway.workflow.evaluator import NodeResult, _matches
from leeway.workflow.parallel import BranchResult, BranchSpec, ParallelSpec
from leeway.workflow.signal_tool import WorkflowSignalInput
from leeway.workflow.types import ConditionSpec, ConditionType, NodeSpec


# -- Condition matching for branches --

def test_branch_always_matches_any_result():
    branch = BranchSpec(prompt="test")  # default: always
    result = NodeResult(signal=WorkflowSignalInput(decision="anything"))
    assert _matches(branch.condition, result) is True


def test_branch_signal_matches():
    branch = BranchSpec(when={"signal": "security_risk"}, prompt="audit")
    result = NodeResult(signal=WorkflowSignalInput(decision="security_risk"))
    assert _matches(branch.condition, result) is True


def test_branch_signal_no_match():
    branch = BranchSpec(when={"signal": "security_risk"}, prompt="audit")
    result = NodeResult(signal=WorkflowSignalInput(decision="has_tests"))
    assert _matches(branch.condition, result) is False


def test_branch_tool_was_called_matches():
    branch = BranchSpec(when={"tool_was_called": "bash"}, prompt="check")
    result = NodeResult(tools_called=["bash", "read_file"])
    assert _matches(branch.condition, result) is True


def test_branch_output_matches():
    branch = BranchSpec(when={"output_matches": "ERROR"}, prompt="handle")
    result = NodeResult(final_text="Found ERROR in output")
    assert _matches(branch.condition, result) is True


# -- Branch result serialization --

def test_branch_result_to_dict():
    br = BranchResult(
        branch_name="test",
        triggered=True,
        approved=True,
        success=True,
        tools_called=["bash"],
        turns_used=3,
    )
    d = _branch_result_to_dict(br)
    assert d["branch_name"] == "test"
    assert d["triggered"] is True
    assert d["tools_called"] == ["bash"]
    assert d["turns_used"] == 3


def test_branch_result_to_dict_failed():
    br = BranchResult(
        branch_name="test",
        success=False,
        error="Timed out",
    )
    d = _branch_result_to_dict(br)
    assert d["success"] is False
    assert d["error"] == "Timed out"


# -- Merge branch results --

def test_merge_branch_results():
    results = {
        "a": BranchResult(branch_name="a", final_text="Result A"),
        "b": BranchResult(branch_name="b", triggered=False),
        "c": BranchResult(branch_name="c", approved=False),
        "d": BranchResult(branch_name="d", success=False, error="timeout"),
    }
    merged = WorkflowEngine._merge_branch_results(results)
    assert "### Branch: a" in merged
    assert "Result A" in merged
    assert "Not triggered" in merged
    assert "approval denied" in merged
    assert "Failed: timeout" in merged


# -- Parallel spec from NodeSpec --

def test_node_spec_parallel_round_trip():
    n = NodeSpec(
        parallel={
            "branches": {
                "analyze": {"prompt": "analyze code", "tools": ["grep"]},
                "test": {
                    "when": {"signal": "has_tests"},
                    "prompt": "run tests",
                    "tools": ["bash"],
                    "requires_approval": True,
                },
            },
            "timeout": 120,
        },
        edges=[{"target": "done"}],
    )
    spec = n.get_parallel_spec()
    assert isinstance(spec, ParallelSpec)
    assert len(spec.branches) == 2
    assert spec.timeout == 120
    assert spec.branches["analyze"].condition.type == ConditionType.ALWAYS
    assert spec.branches["test"].condition.value == "has_tests"
    assert spec.branches["test"].requires_approval is True
