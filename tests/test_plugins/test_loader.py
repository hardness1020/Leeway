"""Tests for plugin loader."""

import json
from pathlib import Path

from leeway.hooks.registry import HookRegistry
from leeway.plugins.loader import PluginLoader
from leeway.skills.registry import SkillRegistry


def test_load_plugin_with_skills(tmp_path: Path):
    plugin_dir = tmp_path / ".leeway" / "plugins" / "my-plugin"
    plugin_dir.mkdir(parents=True)

    (plugin_dir / "plugin.json").write_text(json.dumps({
        "name": "my-plugin",
        "version": "1.0.0",
        "skills": ["skills/review.md"],
    }))

    skills_dir = plugin_dir / "skills"
    skills_dir.mkdir()
    (skills_dir / "review.md").write_text(
        "---\nname: plugin-review\ndescription: Review from plugin\n---\n"
        "Review the code carefully."
    )

    skill_registry = SkillRegistry()
    hook_registry = HookRegistry()
    loader = PluginLoader(tmp_path)
    loaded = loader.load_all(skill_registry, hook_registry)

    assert len(loaded) == 1
    assert loaded[0].name == "my-plugin"
    assert skill_registry.get("plugin-review") is not None


def test_load_plugin_with_hooks(tmp_path: Path):
    plugin_dir = tmp_path / ".leeway" / "plugins" / "hook-plugin"
    plugin_dir.mkdir(parents=True)

    (plugin_dir / "plugin.json").write_text(json.dumps({
        "name": "hook-plugin",
        "hooks": [
            {
                "type": "command",
                "match": {"event": "before_tool_use"},
                "command": "echo hook",
            }
        ],
    }))

    skill_registry = SkillRegistry()
    hook_registry = HookRegistry()
    loader = PluginLoader(tmp_path)
    loader.load_all(skill_registry, hook_registry)

    from leeway.hooks.types import HookEvent

    assert len(hook_registry.get_matching(HookEvent.BEFORE_TOOL_USE)) == 1


def test_no_plugins(tmp_path: Path):
    skill_registry = SkillRegistry()
    hook_registry = HookRegistry()
    loader = PluginLoader(tmp_path)
    loaded = loader.load_all(skill_registry, hook_registry)
    assert loaded == []


def test_invalid_manifest(tmp_path: Path):
    plugin_dir = tmp_path / ".leeway" / "plugins" / "bad"
    plugin_dir.mkdir(parents=True)
    (plugin_dir / "plugin.json").write_text("not json")

    skill_registry = SkillRegistry()
    hook_registry = HookRegistry()
    loader = PluginLoader(tmp_path)
    loaded = loader.load_all(skill_registry, hook_registry)
    assert loaded == []
