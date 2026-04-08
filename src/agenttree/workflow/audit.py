"""Workflow execution audit trail for traceability."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone


@dataclass
class NodeExecution:
    """Record of one node's execution."""

    node_name: str
    signal_decision: str | None = None
    signal_summary: str = ""
    tools_called: list[str] = field(default_factory=list)
    next_node: str | None = None
    turns_used: int = 0


@dataclass
class WorkflowAuditTrail:
    """Full execution trace of a workflow run."""

    workflow_name: str
    started_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    completed_at: str | None = None
    node_executions: list[NodeExecution] = field(default_factory=list)
    path_taken: list[str] = field(default_factory=list)
    final_output: str = ""

    def mark_complete(self) -> None:
        self.completed_at = datetime.now(timezone.utc).isoformat()
        self.path_taken = [ne.node_name for ne in self.node_executions]

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2)

    def to_summary(self) -> str:
        """Human-readable summary."""
        lines = [
            f"Workflow: {self.workflow_name}",
            f"Path: {' -> '.join(self.path_taken)}",
            f"Nodes executed: {len(self.node_executions)}",
        ]
        for ne in self.node_executions:
            signal = f" [signal={ne.signal_decision}]" if ne.signal_decision else ""
            next_label = f" -> {ne.next_node}" if ne.next_node else " (terminal)"
            lines.append(f"  {ne.node_name}{signal}{next_label}")
        return "\n".join(lines)
