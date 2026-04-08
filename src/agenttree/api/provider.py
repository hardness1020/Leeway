"""Provider detection helpers."""

from __future__ import annotations

from dataclasses import dataclass

from agenttree.config.settings import Settings


@dataclass(frozen=True)
class ProviderInfo:
    """Resolved provider metadata for UI and diagnostics."""

    name: str
    auth_kind: str


def detect_provider(settings: Settings) -> ProviderInfo:
    """Infer the active provider from settings."""
    base_url = (settings.base_url or "").lower()
    model = settings.model.lower()

    if settings.api_format == "openai":
        if "moonshot" in base_url or model.startswith("kimi"):
            return ProviderInfo(name="moonshot-openai-compatible", auth_kind="api_key")
        if "dashscope" in base_url or model.startswith("qwen"):
            return ProviderInfo(name="dashscope-openai-compatible", auth_kind="api_key")
        if "models.inference.ai.azure.com" in base_url or "github" in base_url:
            return ProviderInfo(name="github-models-openai-compatible", auth_kind="api_key")
        return ProviderInfo(name="openai-compatible", auth_kind="api_key")

    if base_url:
        return ProviderInfo(name="anthropic-compatible", auth_kind="api_key")

    return ProviderInfo(name="anthropic", auth_kind="api_key")


def auth_status(settings: Settings) -> str:
    """Return a compact auth status string."""
    if settings.api_key:
        return "configured"
    return "missing"
