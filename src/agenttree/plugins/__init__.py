"""Plugin system — bundle skills, hooks, and MCP servers."""

from agenttree.plugins.loader import PluginLoader
from agenttree.plugins.types import PluginManifest

__all__ = [
    "PluginLoader",
    "PluginManifest",
]
