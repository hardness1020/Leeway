"""Remote trigger system — webhook server for external workflow triggers."""

from leeway.triggers.registry import TriggerRegistry
from leeway.triggers.types import TriggerDefinition

__all__ = [
    "TriggerDefinition",
    "TriggerRegistry",
]
