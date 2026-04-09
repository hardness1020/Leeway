"""Skill definition model."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field


class SkillDefinition(BaseModel):
    """A skill loaded from a SKILL.md file inside a named folder.

    Folder structure (progressive disclosure)::

        .leeway/skills/<skill-name>/
            SKILL.md          # required — main instructions
            reference.md      # optional — detailed docs
            examples.md       # optional — example outputs
            ...

    Legacy flat files (``<name>.md``) are also supported.
    """

    name: str
    description: str = ""
    content: str  # SKILL.md content
    source: Literal["bundled", "user", "project", "plugin"] = "project"
    path: Path | None = None  # path to the SKILL.md file
    dir_path: Path | None = None  # path to the skill folder (for progressive disclosure)
    metadata: dict[str, Any] = Field(default_factory=dict)

    def list_files(self) -> list[str]:
        """Return names of supporting files in the skill folder (excluding SKILL.md)."""
        if self.dir_path is None or not self.dir_path.is_dir():
            return []
        return sorted(
            f.name
            for f in self.dir_path.iterdir()
            if f.is_file() and f.name != "SKILL.md" and not f.name.startswith("_")
        )

    def read_file(self, filename: str) -> str | None:
        """Read a supporting file from the skill folder (path-safe)."""
        if self.dir_path is None or not self.dir_path.is_dir():
            return None
        # Prevent path traversal
        target = (self.dir_path / filename).resolve()
        if not str(target).startswith(str(self.dir_path.resolve())):
            return None
        if not target.is_file():
            return None
        try:
            return target.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            return None
