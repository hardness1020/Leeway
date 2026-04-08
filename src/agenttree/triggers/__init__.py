"""Remote trigger system — webhook server for external workflow triggers."""

from agenttree.triggers.registry import TriggerRegistry
from agenttree.triggers.types import TriggerDefinition

__all__ = [
    "TriggerDefinition",
    "TriggerRegistry",
]
