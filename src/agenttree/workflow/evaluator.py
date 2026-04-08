"""Deterministic transition evaluation."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from agenttree.workflow.signal_tool import WorkflowSignalInput
from agenttree.workflow.types import ConditionType, NodeSpec


@dataclass(frozen=True)
class NodeResult:
    """Captured output from a single workflow node execution."""

    signal: WorkflowSignalInput | None = None
    tools_called: list[str] = field(default_factory=list)
    final_text: str = ""


def evaluate_transitions(node: NodeSpec, result: NodeResult) -> str | None:
    """Return the target node name for the first matching edge, or ``None``.

    Edges are evaluated by priority (highest first).  The first match wins.
    """
    sorted_edges = sorted(node.edges, key=lambda e: e.priority, reverse=True)

    for edge in sorted_edges:
        cond = edge.condition
        if _matches(cond, result):
            return edge.target
    return None


def _matches(cond, result: NodeResult) -> bool:
    match cond.type:
        case ConditionType.SIGNAL:
            hit = result.signal is not None and result.signal.decision == cond.value
        case ConditionType.OUTPUT_MATCHES:
            hit = bool(re.search(cond.value, result.final_text, re.IGNORECASE))
        case ConditionType.TOOL_WAS_CALLED:
            hit = cond.value in result.tools_called
        case ConditionType.ALWAYS:
            hit = True
        case _:
            hit = False
    return hit if not cond.negate else not hit
