"""CLAUDE.md discovery and loading."""

from __future__ import annotations

from pathlib import Path


def discover_claude_md_files(cwd: str | Path) -> list[Path]:
    """Discover relevant CLAUDE.md instruction files from the cwd upward."""
    current = Path(cwd).resolve()
    results: list[Path] = []
    seen: set[Path] = set()

    for directory in [current, *current.parents]:
        for candidate in (
            directory / "CLAUDE.md",
            directory / ".claude" / "CLAUDE.md",
        ):
            if candidate.exists() and candidate not in seen:
                results.append(candidate)
                seen.add(candidate)

        rules_dir = directory / ".claude" / "rules"
        if rules_dir.is_dir():
            for rule in sorted(rules_dir.glob("*.md")):
                if rule not in seen:
                    results.append(rule)
                    seen.add(rule)

        if directory.parent == directory:
            break

    return results


def load_claude_md_prompt(cwd: str | Path, *, max_chars_per_file: int = 12000) -> str | None:
    """Load discovered instruction files into one prompt section."""
    files = discover_claude_md_files(cwd)
    if not files:
        return None

    lines = ["# Project Instructions"]
    for path in files:
        content = path.read_text(encoding="utf-8", errors="replace")
        if len(content) > max_chars_per_file:
            content = content[:max_chars_per_file] + "\n...[truncated]..."
        lines.extend(["", f"## {path}", "```md", content.strip(), "```"])
    return "\n".join(lines)
