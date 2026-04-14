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
