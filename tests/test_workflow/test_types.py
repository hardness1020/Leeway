"""Tests for workflow type definitions."""

import pytest
from leeway.workflow.types import (
    ConditionSpec,
    ConditionType,
    EdgeSpec,
    NodeSpec,
    WorkflowDefinition,
)


def test_condition_spec_signal():
    c = ConditionSpec(signal="approve")
    assert c.type == ConditionType.SIGNAL
    assert c.value == "approve"


def test_condition_spec_always():
    c = ConditionSpec(always=True)
    assert c.type == ConditionType.ALWAYS


def test_condition_spec_exactly_one():
    with pytest.raises(ValueError, match="Exactly one"):
        ConditionSpec(signal="a", always=True)


def test_edge_spec_always_shorthand():
    e = EdgeSpec(target="next")
    assert e.condition.type == ConditionType.ALWAYS


def test_workflow_definition_valid():
    w = WorkflowDefinition(
        name="test",
        start_node="a",
        nodes={
            "a": NodeSpec(
                prompt="do something",
                edges=[EdgeSpec(target="b", when=ConditionSpec(signal="done"))],
            ),
            "b": NodeSpec(prompt="finish"),
        },
    )
    assert w.start_node == "a"
    assert w.is_terminal("b")
    assert not w.is_terminal("a")
    assert w.signal_decisions_for_node("a") == ["done"]


def test_workflow_definition_invalid_start():
    with pytest.raises(ValueError, match="start_node"):
        WorkflowDefinition(
            name="bad",
            start_node="missing",
            nodes={"a": NodeSpec(prompt="x")},
        )


def test_workflow_definition_unreachable():
    with pytest.raises(ValueError, match="unreachable"):
        WorkflowDefinition(
            name="bad",
            start_node="a",
            nodes={
                "a": NodeSpec(prompt="x"),
                "orphan": NodeSpec(prompt="y"),
            },
        )
