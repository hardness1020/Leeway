"""Plugin loader — discovers and loads plugins from directories."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from leeway.config.paths import get_config_dir
from leeway.hooks.registry import HookRegistry
from leeway.hooks.types import CommandHookDefinition, HttpHookDefinition
from leeway.plugins.types import PluginManifest
from leeway.skills.registry import SkillRegistry, _parse_skill_file

logger = logging.getLogger(__name__)


class PluginLoader:
    """Discovers plugins and merges their resources into registries."""

    def __init__(self, cwd: str | Path) -> None:
        self._cwd = Path(cwd).resolve()

    def _discover_dirs(self) -> list[Path]:
        """Return all plugin directories to scan."""
        dirs: list[Path] = []
        user_plugins = get_config_dir() / "plugins"
        if user_plugins.is_dir():
            dirs.extend(sorted(d for d in user_plugins.iterdir() if d.is_dir()))
        project_plugins = self._cwd / ".leeway" / "plugins"
        if project_plugins.is_dir():
            dirs.extend(sorted(d for d in project_plugins.iterdir() if d.is_dir()))
        return dirs

    def load_all(
        self,
        skill_registry: SkillRegistry,
        hook_registry: HookRegistry,
    ) -> list[PluginManifest]:
        """Load all plugins and merge their resources.

        Returns the list of loaded manifests.
        """
        loaded: list[PluginManifest] = []
        for plugin_dir in self._discover_dirs():
            manifest = self._load_manifest(plugin_dir)
            if manifest is None:
                continue

            # Skills — validate paths stay within plugin directory
            resolved_plugin_dir = plugin_dir.resolve()
            for skill_path in manifest.skills:
                full_path = (plugin_dir / skill_path).resolve()
                if not str(full_path).startswith(str(resolved_plugin_dir)):
                    logger.warning(
                        "Plugin '%s': skill path escapes plugin dir: %s",
                        manifest.name, skill_path,
                    )
                    continue
                if full_path.is_dir():
                    # Folder-per-skill: <skill>/SKILL.md
                    skill_md = full_path / "SKILL.md"
                    if skill_md.is_file():
                        skill = _parse_skill_file(skill_md, "plugin", dir_path=full_path)
                        if skill is not None:
                            skill_registry.register(skill)
                elif full_path.is_file():
                    # Legacy flat file
                    skill = _parse_skill_file(full_path, "plugin")
                    if skill is not None:
                        skill_registry.register(skill)

            # Hooks
            for hook_def in manifest.hooks:
                hook_type = hook_def.get("type")
                try:
                    if hook_type == "command":
                        hook_registry.register(CommandHookDefinition.model_validate(hook_def))
                    elif hook_type == "http":
                        hook_registry.register(HttpHookDefinition.model_validate(hook_def))
                except Exception:
                    logger.warning(
                        "Invalid hook in plugin '%s': %s", manifest.name, hook_def
                    )

            loaded.append(manifest)
            logger.info("Loaded plugin: %s v%s", manifest.name, manifest.version)

        return loaded

    def _load_manifest(self, plugin_dir: Path) -> PluginManifest | None:
        """Load plugin.json from a plugin directory."""
        manifest_path = plugin_dir / "plugin.json"
        if not manifest_path.exists():
            return None
        try:
            raw = json.loads(manifest_path.read_text(encoding="utf-8"))
            return PluginManifest.model_validate(raw)
        except (json.JSONDecodeError, Exception) as exc:
            logger.warning("Failed to load plugin from %s: %s", plugin_dir, exc)
            return None
