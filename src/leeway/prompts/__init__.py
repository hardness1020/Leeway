"""System prompt builder for Leeway."""

from __future__ import annotations

from pathlib import Path

from leeway.config.settings import Settings
from leeway.prompts.claudemd import discover_claude_md_files, load_claude_md_prompt
from leeway.prompts.environment import get_environment_info
from leeway.prompts.system_prompt import build_system_prompt


def build_runtime_system_prompt(
    settings: Settings,
    *,
    cwd: str | Path,
    latest_user_prompt: str | None = None,
) -> str:
    """Build the runtime system prompt with project instructions."""
    sections = [build_system_prompt(custom_prompt=settings.system_prompt, cwd=str(cwd))]

    if settings.fast_mode:
        sections.append(
            "# Session Mode\nFast mode is enabled. Prefer concise replies, minimal tool use, and quicker progress over exhaustive exploration."
        )

    sections.append(
        "# Reasoning Settings\n"
        f"- Effort: {settings.effort}\n"
        f"- Passes: {settings.passes}\n"
        "Adjust depth and iteration count to match these settings while still completing the task."
    )

    claude_md = load_claude_md_prompt(cwd)
    if claude_md:
        sections.append(claude_md)

    return "\n\n".join(section for section in sections if section.strip())


__all__ = [
    "build_runtime_system_prompt",
    "build_system_prompt",
    "discover_claude_md_files",
    "get_environment_info",
    "load_claude_md_prompt",
]
