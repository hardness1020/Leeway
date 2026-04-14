# Permissions

Multi-level safety with fine-grained control:

| Mode | Behavior | Use Case |
|------|----------|----------|
| **Default** | Ask before write/execute | Daily development |
| **Full Auto** | Allow everything | Sandboxed environments |
| **Plan Mode** | Block all writes | Review before acting |

**Path-level rules** in `settings.json`:
```json
{
  "permission": {
    "mode": "default",
    "path_rules": [{ "pattern": "/etc/*", "allow": false }],
    "denied_commands": ["rm -rf /"]
  }
}
```
