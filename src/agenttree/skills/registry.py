"""Skill registry and discovery."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from agenttree.config.paths import get_config_dir
from agenttree.skills.types import SkillDefinition


def _parse_skill_file(path: Path, source: str, dir_path: Path | None = None) -> SkillDefinition | None:
    """Parse a markdown file with optional YAML frontmatter into a SkillDefinition."""
    try:
        raw = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None

    name = path.stem if dir_path is None else dir_path.name
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
        dir_path=dir_path,
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
        """Return a skill by name (tries exact, lowercase, hyphenated)."""
        return (
            self._skills.get(name)
            or self._skills.get(name.lower())
            or self._skills.get(name.replace("_", "-"))
        )

    def list_skills(self) -> list[SkillDefinition]:
        """Return all registered skills."""
        return list(self._skills.values())


def _scan_directory(directory: Path, source: str, registry: SkillRegistry) -> None:
    """Scan a directory for skill folders and legacy flat .md files.

    Discovery order:
    1. Folder-per-skill: ``<name>/SKILL.md`` (preferred)
    2. Legacy flat file: ``<name>.md`` (backward compatible)
    """
    if not directory.is_dir():
        return

    # Folder-per-skill: <name>/SKILL.md
    folder_names: set[str] = set()
    for child in sorted(directory.iterdir()):
        if child.is_dir() and not child.name.startswith("_"):
            skill_md = child / "SKILL.md"
            if skill_md.is_file():
                skill = _parse_skill_file(skill_md, source, dir_path=child)
                if skill is not None:
                    registry.register(skill)
                    folder_names.add(child.name)

    # Legacy flat files: <name>.md (skip if same name found as folder in this dir)
    for path in sorted(directory.glob("*.md")):
        if path.name.startswith("_"):
            continue
        if path.stem in folder_names:
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
