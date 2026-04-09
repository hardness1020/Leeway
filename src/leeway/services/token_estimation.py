"""Simple token estimation utilities."""

from __future__ import annotations


def estimate_tokens(text: str) -> int:
    """Estimate tokens from plain text using a rough character heuristic."""
    if not text:
        return 0
    return max(1, (len(text) + 3) // 4)


def estimate_message_tokens(messages: list[str]) -> int:
    """Estimate tokens for a collection of message strings."""
    return sum(estimate_tokens(message) for message in messages)
