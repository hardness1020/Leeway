# MCP Support

Connect to [Model Context Protocol](https://modelcontextprotocol.io/) servers for external tool integration:

```json
{
  "mcp_servers": [
    {
      "name": "my-server",
      "transport": "stdio",
      "command": "npx",
      "args": ["-y", "@my/mcp-server"]
    }
  ]
}
```

MCP tools auto-register as `mcp_<server>_<tool>` and are available in workflow node `tools:` lists.

```bash
uv pip install leeway[mcp]  # Install MCP support
```

## Streamable HTTP: keyless web search

From a source checkout, install the optional MCP dependencies:

```bash
uv sync --extra mcp
```

Add this entry to `mcp_servers` in `~/.leeway/settings.json` (merge it with any
existing settings and servers):

```json
{
  "mcp_servers": [
    {
      "name": "parallel",
      "transport": "streamable_http",
      "url": "https://search.parallel.ai/mcp"
    }
  ]
}
```

Restart Leeway, then ask it to use `mcp_parallel_web_search` to find current
information, or `mcp_parallel_web_fetch` to read a specific URL. These tools are
also available in workflow node `tools:` lists; include `parallel` in that node's
`mcp_servers:` list to scope access. MCP calls follow the existing permission
checks, so approve the call when prompted.

[Parallel Search MCP](https://docs.parallel.ai/integrations/mcp/search-mcp)
provides search excerpts and URL content without a Parallel API key or OAuth.
The anonymous endpoint is rate limited and intended for exploration and light
use. Leeway still needs its separately configured LLM credentials. Existing
servers and the default `stdio` transport are unchanged. Streamable HTTP requests
identify the client as `Leeway/0.1.0`.
