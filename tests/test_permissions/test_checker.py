"""Tests for permission checker."""

from agenttree.config.settings import PermissionSettings
from agenttree.permissions.checker import PermissionChecker
from agenttree.permissions.modes import PermissionMode


def test_full_auto_allows_all():
    settings = PermissionSettings(mode=PermissionMode.FULL_AUTO)
    checker = PermissionChecker(settings)
    decision = checker.evaluate("bash", is_read_only=False)
    assert decision.allowed


def test_default_allows_read_only():
    settings = PermissionSettings(mode=PermissionMode.DEFAULT)
    checker = PermissionChecker(settings)
    decision = checker.evaluate("read_file", is_read_only=True)
    assert decision.allowed


def test_default_requires_confirmation_for_mutating():
    settings = PermissionSettings(mode=PermissionMode.DEFAULT)
    checker = PermissionChecker(settings)
    decision = checker.evaluate("bash", is_read_only=False)
    assert not decision.allowed
    assert decision.requires_confirmation


def test_plan_blocks_mutating():
    settings = PermissionSettings(mode=PermissionMode.PLAN)
    checker = PermissionChecker(settings)
    decision = checker.evaluate("bash", is_read_only=False)
    assert not decision.allowed
    assert not decision.requires_confirmation


def test_explicit_allow():
    settings = PermissionSettings(
        mode=PermissionMode.DEFAULT,
        allowed_tools=["bash"],
    )
    checker = PermissionChecker(settings)
    decision = checker.evaluate("bash", is_read_only=False)
    assert decision.allowed


def test_explicit_deny():
    settings = PermissionSettings(
        mode=PermissionMode.FULL_AUTO,
        denied_tools=["bash"],
    )
    checker = PermissionChecker(settings)
    decision = checker.evaluate("bash", is_read_only=False)
    assert not decision.allowed
