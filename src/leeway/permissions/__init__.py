"""Permission system."""

from leeway.permissions.modes import PermissionMode


def __getattr__(name: str):
    if name == "PermissionChecker":
        from leeway.permissions.checker import PermissionChecker
        return PermissionChecker
    if name == "PermissionDecision":
        from leeway.permissions.checker import PermissionDecision
        return PermissionDecision
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = ["PermissionChecker", "PermissionDecision", "PermissionMode"]
