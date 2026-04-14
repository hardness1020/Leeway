# Plugins

Bundle skills, hooks, and MCP servers into distributable packages:

```
my-plugin/
  plugin.json
  skills/
    review.md
```

```json
{
  "name": "my-plugin",
  "version": "1.0.0",
  "skills": ["skills/review.md"],
  "hooks": [],
  "mcp_servers": []
}
```

Place in `~/.leeway/plugins/<name>/` or `<project>/.leeway/plugins/<name>/`.

## Custom Plugin

Create `<project>/.leeway/plugins/my-plugin/plugin.json` with skills, hooks, and MCP servers.
