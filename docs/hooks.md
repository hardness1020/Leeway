# Hooks

Lifecycle callbacks that fire before or after tool execution. Hooks can be defined globally (in `settings.json`), at the workflow level (`global_hooks`), or per-node/branch:

```yaml
# Workflow-level hooks (fire for all nodes)
global_hooks:
  - type: command
    match: { event: workflow_start }
    command: "echo 'workflow started' >> /tmp/hooks.log"

nodes:
  tests:
    hooks:   # Node-level hook (only fires within this node)
      - type: command
        match: { event: after_tool_use, tool_name: bash }
        command: "echo 'bash executed in tests' >> /tmp/hooks.log"
```

Settings-level hooks in `settings.json`:
```json
{
  "hooks": [
    {
      "type": "http",
      "match": { "event": "before_tool_use" },
      "url": "https://example.com/webhook",
      "method": "POST"
    }
  ]
}
```

| Hook Type | Execution | Use Case |
|-----------|-----------|----------|
| `command` | Shell command with payload on stdin | Logging, notifications, auditing |
| `http` | HTTP POST with JSON payload | External integrations, webhooks |

Hooks are merged from all levels: settings, workflow globals, then node/branch. Errors are logged but never block execution.
