"""Tests for workflow transition evaluator."""

from agenttree.workflow.evaluator import NodeResult, evaluate_transitions
from agenttree.workflow.signal_tool import WorkflowSignalInput
from agenttree.workflow.types import ConditionSpec, EdgeSpec, NodeSpec


def test_signal_match():
    node = NodeSpec(
        prompt="test",
        edges=[
            EdgeSpec(target="yes", when=ConditionSpec(signal="approve")),
            EdgeSpec(target="no", when=ConditionSpec(signal="reject")),
        ],
    )
    result = NodeResult(signal=WorkflowSignalInput(decision="approve"))
    assert evaluate_transitions(node, result) == "yes"


def test_always_fallback():
    node = NodeSpec(
        prompt="test",
        edges=[EdgeSpec(target="next", when=ConditionSpec(always=True))],
    )
    result = NodeResult()
    assert evaluate_transitions(node, result) == "next"


def test_output_matches():
    node = NodeSpec(
        prompt="test",
        edges=[EdgeSpec(target="found", when=ConditionSpec(output_matches="ERROR"))],
    )
    result = NodeResult(final_text="Something ERROR happened")
    assert evaluate_transitions(node, result) == "found"


def test_tool_was_called():
    node = NodeSpec(
        prompt="test",
        edges=[EdgeSpec(target="done", when=ConditionSpec(tool_was_called="bash"))],
    )
    result = NodeResult(tools_called=["bash", "read_file"])
    assert evaluate_transitions(node, result) == "done"


def test_no_match_returns_none():
    node = NodeSpec(
        prompt="test",
        edges=[EdgeSpec(target="x", when=ConditionSpec(signal="missing"))],
    )
    result = NodeResult(signal=WorkflowSignalInput(decision="other"))
    assert evaluate_transitions(node, result) is None


def test_negate():
    node = NodeSpec(
        prompt="test",
        edges=[EdgeSpec(target="clean", when=ConditionSpec(output_matches="ERROR", negate=True))],
    )
    result = NodeResult(final_text="All good")
    assert evaluate_transitions(node, result) == "clean"
