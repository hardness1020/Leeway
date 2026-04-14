# Scheduling & Cron

Leeway includes a standalone cron scheduler daemon for running workflows and commands on a schedule.

```bash
# Start the scheduler daemon
uv run leeway scheduler start

# Check status
uv run leeway scheduler status

# Stop
uv run leeway scheduler stop
```

**Schedule types:**

| Type | Example | Description |
|------|---------|-------------|
| Cron expression | `*/5 * * * *` | Every 5 minutes |
| Interval | `300` seconds | Every 5 minutes |
| One-shot | `2026-04-15T09:00:00` | Run once at a specific time |

**Action types:** shell commands, workflow executions, or webhook calls.

## Remote Triggers

Create webhook endpoints that trigger workflows from external systems:

```bash
# The agent creates triggers via the remote_trigger tool
# Each trigger gets a unique ID and secret

POST /trigger/<id>
Header: X-Trigger-Secret: <secret>
```

Use `remote_trigger` tool with `action: "create"` to set up a new endpoint.
