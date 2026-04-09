"""Human-in-the-loop broker for parallel branch execution."""

from __future__ import annotations

import asyncio
from typing import Awaitable, Callable

AskUserPrompt = Callable[[str], Awaitable[str]]


class HitlBroker:
    """Multiplexes a single ask_user_prompt callback across concurrent branches.

    Uses an asyncio lock to serialize user interaction — only one branch
    can talk to the user at a time.  Other branches that need input block
    on the lock until the current interaction completes.
    """

    def __init__(self, upstream_ask: AskUserPrompt | None) -> None:
        self._upstream = upstream_ask
        self._lock = asyncio.Lock()

    def make_branch_ask_prompt(self, branch_name: str) -> AskUserPrompt | None:
        """Return a per-branch ask_user_prompt that routes through the broker."""
        if self._upstream is None:
            return None

        async def _ask(question: str) -> str:
            async with self._lock:
                assert self._upstream is not None
                return await self._upstream(f"[Branch: {branch_name}] {question}")

        return _ask

    async def request_approval(self, branch_name: str) -> bool:
        """Gate: ask user whether to approve branch execution."""
        async with self._lock:
            if self._upstream is None:
                return True  # auto-approve in headless mode
            answer = await self._upstream(
                f"Branch '{branch_name}' requires approval to execute. Allow? (yes/no)"
            )
            return answer.strip().lower() in ("yes", "y", "true", "1")
