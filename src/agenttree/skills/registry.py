"""Skill registry and discovery."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from agenttree.config.paths import get_config_dir
from agenttree.skills.types import SkillDefinition


def _parse_skill_file(path: Path, source: str) -> SkillDefinition | None:
    """Parse a markdown file with optional YAML frontmatter into a SkillDefinition."""
    try:
        raw = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None

    name = path.stem
    description = ""
    content = raw
    metadata: dict[str, Any] = {}

    stripped = raw.lstrip()
    if stripped.startswith("---"):
        # Find closing --- after the opening one
        after_open = stripped[3:]
        end_idx = after_open.find("\n---")
        if end_idx >= 0:
            frontmatter_str = after_open[:end_idx]
            content = after_open[end_idx + 4:].lstrip("\n")
            try:
                fm = yaml.safe_load(frontmatter_str)
                if isinstance(fm, dict):
                    name = fm.pop("name", name)
                    description = fm.pop("description", description)
                    metadata = fm
            except yaml.YAMLError:
                pass

    if not content.strip():
        return None

    return SkillDefinition(
        name=name,
        description=description,
        content=content,
        source=source,  # type: ignore[arg-type]
        path=path,
        metadata=metadata,
    )


class SkillRegistry:
    """Map skill names to definitions."""

    def __init__(self) -> None:
        self._skills: dict[str, SkillDefinition] = {}

    def register(self, skill: SkillDefinition) -> None:
        """Register a skill (overwrites on name collision)."""
        self._skills[skill.name] = skill

    def get(self, name: str) -> SkillDefinition | None:
        """Return a skill by name."""
        return self._skills.get(name)

    def list_skills(self) -> list[SkillDefinition]:
        """Return all registered skills."""
        return list(self._skills.values())


def _scan_directory(directory: Path, source: str, registry: SkillRegistry) -> None:
    """Scan a directory for .md skill files and register them."""
    if not directory.is_dir():
        return
    for path in sorted(directory.glob("*.md")):
        if path.name.startswith("_"):
            continue
        skill = _parse_skill_file(path, source)
        if skill is not None:
            registry.register(skill)


def load_skill_registry(cwd: str | Path) -> SkillRegistry:
    """Load skills from user-level and project-level directories.

    Discovery order (later overrides earlier on name collision):
    1. ~/.agenttree/skills/
    2. <cwd>/.agenttree/skills/
    """
    registry = SkillRegistry()
    _scan_directory(get_config_dir() / "skills", "user", registry)
    _scan_directory(Path(cwd).resolve() / ".agenttree" / "skills", "project", registry)
    return registry
