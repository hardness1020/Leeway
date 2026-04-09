"""Tests for HitlBroker — human-in-the-loop multiplexer."""

import asyncio

import pytest
from leeway.workflow.hitl import HitlBroker


@pytest.fixture
def mock_ask():
    """Mock upstream ask_user_prompt that records calls."""
    calls = []

    async def _ask(question: str) -> str:
        calls.append(question)
        return "yes"

    _ask.calls = calls
    return _ask


@pytest.mark.asyncio
async def test_branch_ask_prompt_prefixes_name(mock_ask):
    broker = HitlBroker(upstream_ask=mock_ask)
    ask = broker.make_branch_ask_prompt("security")
    result = await ask("Check dependencies?")
    assert result == "yes"
    assert mock_ask.calls[-1] == "[Branch: security] Check dependencies?"


@pytest.mark.asyncio
async def test_branch_ask_prompt_no_upstream():
    broker = HitlBroker(upstream_ask=None)
    ask = broker.make_branch_ask_prompt("test")
    assert ask is None


@pytest.mark.asyncio
async def test_request_approval_yes(mock_ask):
    broker = HitlBroker(upstream_ask=mock_ask)
    assert await broker.request_approval("deploy") is True
    assert "deploy" in mock_ask.calls[-1]


@pytest.mark.asyncio
async def test_request_approval_no():
    async def _deny(question: str) -> str:
        return "no"

    broker = HitlBroker(upstream_ask=_deny)
    assert await broker.request_approval("deploy") is False


@pytest.mark.asyncio
async def test_request_approval_auto_approve_headless():
    broker = HitlBroker(upstream_ask=None)
    assert await broker.request_approval("deploy") is True


@pytest.mark.asyncio
async def test_lock_serializes_concurrent_asks():
    """Two concurrent branch asks should be serialized by the lock."""
    order = []

    async def _slow_ask(question: str) -> str:
        branch = question.split("]")[0].split(": ")[1] if ": " in question else "unknown"
        order.append(f"start:{branch}")
        await asyncio.sleep(0.05)
        order.append(f"end:{branch}")
        return "ok"

    broker = HitlBroker(upstream_ask=_slow_ask)
    ask_a = broker.make_branch_ask_prompt("alpha")
    ask_b = broker.make_branch_ask_prompt("beta")

    await asyncio.gather(ask_a("q1"), ask_b("q2"))

    # Because of the lock, one must fully complete before the other starts
    assert order[0].startswith("start:")
    assert order[1].startswith("end:")
    assert order[2].startswith("start:")
    assert order[3].startswith("end:")
