"""Web fetch tool — retrieve content from a URL."""

from __future__ import annotations

import re

from pydantic import BaseModel, Field

from agenttree.tools.base import BaseTool, ToolExecutionContext, ToolResult


class WebFetchInput(BaseModel):
    """Input for the web fetch tool."""

    url: str = Field(description="URL to fetch")
    max_length: int = Field(default=10000, description="Maximum characters to return")


def _strip_html(html: str) -> str:
    """Crude HTML → plain text conversion."""
    text = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"&nbsp;", " ", text)
    text = re.sub(r"&amp;", "&", text)
    text = re.sub(r"&lt;", "<", text)
    text = re.sub(r"&gt;", ">", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


class WebFetchTool(BaseTool):
    """Fetch and return the text content of a URL."""

    name = "web_fetch"
    description = "Fetch content from a URL and return it as text."
    input_model = WebFetchInput

    def is_read_only(self, arguments: BaseModel) -> bool:
        return True

    async def execute(self, arguments: BaseModel, context: ToolExecutionContext) -> ToolResult:
        args = arguments if isinstance(arguments, WebFetchInput) else WebFetchInput.model_validate(arguments)

        from urllib.parse import urlparse

        parsed = urlparse(args.url)
        if parsed.scheme not in ("http", "https"):
            return ToolResult(output=f"URL scheme must be http or https, got: {parsed.scheme!r}", is_error=True)

        hostname = parsed.hostname or ""
        if hostname in ("localhost", "127.0.0.1", "0.0.0.0", "::1") or hostname.startswith("169.254."):
            return ToolResult(output="Requests to localhost and link-local addresses are not allowed.", is_error=True)

        try:
            import httpx
        except ImportError:
            return ToolResult(
                output="httpx is not installed. Add httpx to dependencies.",
                is_error=True,
            )

        try:
            async with httpx.AsyncClient(follow_redirects=True, timeout=30.0) as client:
                resp = await client.get(args.url)
                resp.raise_for_status()
        except Exception as exc:
            return ToolResult(output=f"Fetch failed: {exc}", is_error=True)

        content_type = resp.headers.get("content-type", "")
        body = resp.text

        if "html" in content_type:
            body = _strip_html(body)

        if len(body) > args.max_length:
            body = body[: args.max_length] + f"\n\n... (truncated, {len(resp.text)} total chars)"

        return ToolResult(output=body)
