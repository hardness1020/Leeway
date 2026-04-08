"""Simple usage aggregation."""

from __future__ import annotations

from agenttree.api.usage import UsageSnapshot


class CostTracker:
    """Accumulate usage over the lifetime of a session."""

    def __init__(self) -> None:
        self._usage = UsageSnapshot()

    def add(self, usage: UsageSnapshot) -> None:
        """Add a usage snapshot to the running total."""
        self._usage = UsageSnapshot(
            input_tokens=self._usage.input_tokens + usage.input_tokens,
            output_tokens=self._usage.output_tokens + usage.output_tokens,
        )

    @property
    def total(self) -> UsageSnapshot:
        """Return the aggregated usage."""
        return self._usage
