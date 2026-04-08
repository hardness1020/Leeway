"""Workflow definition schema -- the user-facing YAML contract."""

from __future__ import annotations

from enum import Enum
from typing import Literal, Self

from pydantic import BaseModel, Field, model_validator


class ConditionType(str, Enum):
    """Supported transition condition types."""

    SIGNAL = "signal"
    OUTPUT_MATCHES = "output_matches"
    TOOL_WAS_CALLED = "tool_was_called"
    ALWAYS = "always"


class ConditionSpec(BaseModel):
    """One transition condition.

    Exactly one field must be set (or ``always=True``).
    """

    signal: str | None = None
    output_matches: str | None = None
    tool_was_called: str | None = None
    always: bool = False
    negate: bool = False

    # ------------------------------------------------------------------
    @model_validator(mode="after")
    def _exactly_one(self) -> Self:
        set_fields = sum(
            [
                self.signal is not None,
                self.output_matches is not None,
                self.tool_was_called is not None,
                self.always,
            ]
        )
        if set_fields != 1:
            raise ValueError(
                "Exactly one of signal / output_matches / tool_was_called / always must be set"
            )
        return self

    @property
    def type(self) -> ConditionType:
        if self.signal is not None:
            return ConditionType.SIGNAL
        if self.output_matches is not None:
            return ConditionType.OUTPUT_MATCHES
        if self.tool_was_called is not None:
            return ConditionType.TOOL_WAS_CALLED
        return ConditionType.ALWAYS

    @property
    def value(self) -> str:
        """Return the match value for the active condition field."""
        if self.signal is not None:
            return self.signal
        if self.output_matches is not None:
            return self.output_matches
        if self.tool_was_called is not None:
            return self.tool_was_called
        return ""


class EdgeSpec(BaseModel):
    """One outgoing edge from a node."""

    target: str
    when: ConditionSpec | Literal["always"] = "always"
    priority: int = 0

    @model_validator(mode="after")
    def _normalise_always(self) -> Self:
        if self.when == "always":
            object.__setattr__(self, "when", ConditionSpec(always=True))
        return self

    @property
    def condition(self) -> ConditionSpec:
        assert isinstance(self.when, ConditionSpec)
        return self.when


class NodeSpec(BaseModel):
    """One node in the workflow graph."""

    prompt: str
    tools: list[str] = Field(default_factory=list, description="Tool whitelist for this node")
    max_turns: int = Field(50, description="Max LLM turns within this node")
    carry_context: bool = Field(True, description="Pass prior node summary as context")
    edges: list[EdgeSpec] = Field(default_factory=list)


class WorkflowDefinition(BaseModel):
    """Complete workflow graph -- the schema users write in YAML."""

    name: str
    description: str = ""
    start_node: str
    nodes: dict[str, NodeSpec]
    global_tools: list[str] = Field(
        default_factory=list,
        description="Tools available in every node (merged with per-node tools)",
    )

    @model_validator(mode="after")
    def _validate_graph(self) -> Self:
        errors: list[str] = []

        if self.start_node not in self.nodes:
            errors.append(f"start_node '{self.start_node}' not found in nodes")

        for node_name, node in self.nodes.items():
            for edge in node.edges:
                if edge.target not in self.nodes:
                    errors.append(
                        f"node '{node_name}' has edge targeting unknown node '{edge.target}'"
                    )

        # Check for unreachable nodes (not reachable from start_node)
        if self.start_node in self.nodes:
            reachable: set[str] = set()
            stack = [self.start_node]
            while stack:
                current = stack.pop()
                if current in reachable:
                    continue
                reachable.add(current)
                for edge in self.nodes[current].edges:
                    if edge.target in self.nodes and edge.target not in reachable:
                        stack.append(edge.target)
            unreachable = set(self.nodes.keys()) - reachable
            if unreachable:
                errors.append(f"unreachable nodes: {sorted(unreachable)}")

        if errors:
            raise ValueError("Invalid workflow graph: " + "; ".join(errors))
        return self

    def signal_decisions_for_node(self, node_name: str) -> list[str]:
        """Return the valid signal values for a node's edges."""
        node = self.nodes[node_name]
        return [
            edge.condition.value
            for edge in node.edges
            if edge.condition.type == ConditionType.SIGNAL
        ]

    def is_terminal(self, node_name: str) -> bool:
        """Return whether a node has no outgoing edges."""
        return len(self.nodes[node_name].edges) == 0
