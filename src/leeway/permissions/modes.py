"""Permission mode definitions."""

from __future__ import annotations

from enum import Enum


class PermissionMode(str, Enum):
    """Permission mode controls how tool execution is gated."""

    DEFAULT = "default"
    PLAN = "plan"
    FULL_AUTO = "full_auto"
