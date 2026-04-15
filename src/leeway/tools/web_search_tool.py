"""Web search tool — search the web via Brave or you.com Search API."""

from __future__ import annotations

import os

from pydantic import BaseModel, Field

from leeway.tools.base import BaseTool, ToolExecutionContext, ToolResult


class WebSearchInput(BaseModel):
    """Input for the web search tool."""

    query: str = Field(description="Search query")
    num_results: int = Field(default=5, description="Number of results to return")


class WebSearchTool(BaseTool):
    """Search the web and return results.

    Provider selection:
    - ``WEB_SEARCH_PROVIDER=brave`` (default) requires ``BRAVE_SEARCH_API_KEY``
    - ``WEB_SEARCH_PROVIDER=you`` requires ``YOU_SEARCH_API_KEY``
    """

    name = "web_search"
    description = "Search the web for information. Returns titles, URLs, and snippets."
    input_model = WebSearchInput

    def is_read_only(self, arguments: BaseModel) -> bool:
        return True

    async def execute(self, arguments: BaseModel, context: ToolExecutionContext) -> ToolResult:
        args = arguments if isinstance(arguments, WebSearchInput) else WebSearchInput.model_validate(arguments)

        try:
            import httpx
        except ImportError:
            return ToolResult(
                output="httpx is not installed. Add httpx to dependencies.",
                is_error=True,
            )

        provider = os.environ.get("WEB_SEARCH_PROVIDER", "brave").strip().lower()
        if provider not in {"brave", "you"}:
            return ToolResult(
                output="Unsupported WEB_SEARCH_PROVIDER. Use 'brave' or 'you'.",
                is_error=True,
            )

        if provider == "you":
            api_key = os.environ.get("YOU_SEARCH_API_KEY", "")
            if not api_key:
                return ToolResult(
                    output=(
                        "No API key found for you.com search. Set YOU_SEARCH_API_KEY "
                        "or switch WEB_SEARCH_PROVIDER=brave."
                    ),
                    is_error=True,
                )

            try:
                async with httpx.AsyncClient(timeout=15.0) as client:
                    resp = await client.get(
                        "https://api.ydc-index.io/v1/search",
                        params={"query": args.query, "count": args.num_results},
                        headers={"X-API-Key": api_key},
                    )
                    resp.raise_for_status()
            except Exception as exc:
                return ToolResult(output=f"you.com search failed: {exc}", is_error=True)

            data = resp.json()
            results = data.get("hits", [])
        else:
            api_key = os.environ.get("BRAVE_SEARCH_API_KEY", "")
            if not api_key:
                return ToolResult(
                    output=(
                        "No API key found for Brave search. Set BRAVE_SEARCH_API_KEY "
                        "or switch WEB_SEARCH_PROVIDER=you with YOU_SEARCH_API_KEY."
                    ),
                    is_error=True,
                )

            try:
                async with httpx.AsyncClient(timeout=15.0) as client:
                    resp = await client.get(
                        "https://api.search.brave.com/res/v1/web/search",
                        params={"q": args.query, "count": args.num_results},
                        headers={
                            "Accept": "application/json",
                            "X-Subscription-Token": api_key,
                        },
                    )
                    resp.raise_for_status()
            except Exception as exc:
                return ToolResult(output=f"Brave search failed: {exc}", is_error=True)

            data = resp.json()
            results = data.get("web", {}).get("results", [])

        if not results:
            return ToolResult(output="No results found.")

        lines: list[str] = []
        for i, r in enumerate(results[: args.num_results], 1):
            title = r.get("title") or r.get("name", "")
            url = r.get("url", "")
            snippets = r.get("snippets") or []
            first_snippet = snippets[0] if snippets else ""
            desc = first_snippet or r.get("description") or r.get("snippet") or ""
            lines.append(f"{i}. {title}\n   {url}\n   {desc}")

        return ToolResult(output="\n\n".join(lines))
