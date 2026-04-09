"""Memory store — markdown files with YAML frontmatter."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

from leeway.config.paths import get_config_dir
from leeway.memory.types import MemoryEntry


class MemoryStore:
    """Read/write memory entries as markdown files in ~/.leeway/memory/."""

    def __init__(self, directory: Path | None = None) -> None:
        self._dir = directory or (get_config_dir() / "memory")
        self._dir.mkdir(parents=True, exist_ok=True)

    def save(self, entry: MemoryEntry) -> Path:
        """Save a memory entry to disk. Returns the file path."""
        slug = re.sub(r"[^a-z0-9]+", "_", entry.name.lower()).strip("_")
        path = self._dir / f"{slug}.md"

        frontmatter = {
            "name": entry.name,
            "description": entry.description,
            "tags": entry.tags,
            "created_at": entry.created_at.isoformat(),
            "updated_at": entry.updated_at.isoformat(),
        }
        if entry.metadata:
            frontmatter.update(entry.metadata)

        text = f"---\n{yaml.dump(frontmatter, default_flow_style=False).strip()}\n---\n\n{entry.content}\n"
        path.write_text(text, encoding="utf-8")
        entry.path = path
        return path

    def get(self, name: str) -> MemoryEntry | None:
        """Find a memory entry by name."""
        for entry in self.list():
            if entry.name == name:
                return entry
        return None

    def list(self) -> list[MemoryEntry]:
        """Load all memory entries from disk."""
        entries: list[MemoryEntry] = []
        for path in sorted(self._dir.glob("*.md")):
            if path.name.startswith("_"):
                continue
            entry = self._parse_file(path)
            if entry is not None:
                entries.append(entry)
        return entries

    def delete(self, name: str) -> bool:
        """Delete a memory entry by name."""
        entry = self.get(name)
        if entry is None or entry.path is None:
            return False
        entry.path.unlink(missing_ok=True)
        return True

    def search(self, query: str) -> list[MemoryEntry]:
        """Simple keyword search across memory entries."""
        query_lower = query.lower()
        results: list[MemoryEntry] = []
        for entry in self.list():
            score = 0
            if query_lower in entry.name.lower():
                score += 3
            if query_lower in entry.description.lower():
                score += 2
            if query_lower in entry.content.lower():
                score += 1
            if any(query_lower in t.lower() for t in entry.tags):
                score += 2
            if score > 0:
                results.append(entry)
        return results

    def _parse_file(self, path: Path) -> MemoryEntry | None:
        """Parse a markdown file with YAML frontmatter into a MemoryEntry."""
        try:
            raw = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            return None

        name = path.stem
        description = ""
        content = raw
        tags: list[str] = []
        metadata: dict[str, Any] = {}

        stripped = raw.lstrip()
        if stripped.startswith("---"):
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
                        tags = fm.pop("tags", tags)
                        fm.pop("created_at", None)
                        fm.pop("updated_at", None)
                        metadata = fm
                except yaml.YAMLError:
                    pass

        return MemoryEntry(
            name=name,
            description=description,
            content=content.strip(),
            tags=tags,
            path=path,
            metadata=metadata,
        )
