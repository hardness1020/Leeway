"""Web search tool — search the web via Brave Search API."""

from __future__ import annotations

from pydantic import BaseModel, Field

from leeway.tools.base import BaseTool, ToolExecutionContext, ToolResult


class WebSearchInput(BaseModel):
    """Input for the web search tool."""

    query: str = Field(description="Search query")
    num_results: int = Field(default=5, description="Number of results to return")


class WebSearchTool(BaseTool):
    """Search the web and return results.

    Requires a Brave Search API key configured via
    ``web_search_api_key`` in settings or ``BRAVE_SEARCH_API_KEY`` env var.
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

        import os

        api_key = os.environ.get("BRAVE_SEARCH_API_KEY", "")
        if not api_key:
            return ToolResult(
                output=(
                    "No search API key found. Set BRAVE_SEARCH_API_KEY environment "
                    "variable or configure web_search_api_key in settings."
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
            return ToolResult(output=f"Search failed: {exc}", is_error=True)

        data = resp.json()
        results = data.get("web", {}).get("results", [])
        if not results:
            return ToolResult(output="No results found.")

        lines: list[str] = []
        for i, r in enumerate(results[: args.num_results], 1):
            title = r.get("title", "")
            url = r.get("url", "")
            desc = r.get("description", "")
            lines.append(f"{i}. {title}\n   {url}\n   {desc}")

        return ToolResult(output="\n\n".join(lines))
