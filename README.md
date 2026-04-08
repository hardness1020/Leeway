<h1 align="center">AgentTree</h1>

<p align="center">
  <strong>Human-defined workflows. AI-powered execution.</strong><br>
  YAML decision trees with scheduling, hooks, MCP, and 21 built-in tools.
</p>

<p align="center">
  <a href="#-quick-start"><img src="https://img.shields.io/badge/Quick_Start-3_min-blue?style=for-the-badge" alt="Quick Start"></a>
  <a href="#-writing-workflows"><img src="https://img.shields.io/badge/Workflows-YAML-ff69b4?style=for-the-badge" alt="Workflows"></a>
  <a href="#-tools-21"><img src="https://img.shields.io/badge/Tools-21+-green?style=for-the-badge" alt="Tools"></a>
  <a href="#-test-results"><img src="https://img.shields.io/badge/Tests-119_Passing-brightgreen?style=for-the-badge" alt="Tests"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge" alt="License"></a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/python-≥3.10-blue?logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/React+Ink-TUI-61DAFB?logo=react&logoColor=white" alt="React">
  <img src="https://img.shields.io/badge/output-text_|_json_|_stream--json-blueviolet" alt="Output">
</p>

---

## Why AgentTree?

Most AI agent tools fall into two extremes:

| | Agent-controlled (e.g. OpenClaw) | Human-designed (e.g. n8n) | **AgentTree** |
|---|---|---|---|
| **Who decides the flow?** | The AI | The human | **Human** (YAML decision trees) |
| **Who executes steps?** | The AI | Rigid scripts | **AI** (flexible within each node) |
| **Predictable?** | No — might do anything | Yes — but no AI flexibility | **Yes** — deterministic transitions |
| **Flexible?** | Yes — but unpredictable | No — locked to the design | **Yes** — AI reasons within bounds |

**AgentTree** gives you the reliability of a state machine with the flexibility of an LLM at each step.

---

## Key Features

<table align="center" width="100%">
<tr>
<td width="20%" align="center" style="vertical-align: top; padding: 15px;">

<h3>Workflow Engine</h3>

<p align="center"><strong>YAML Decision Trees</strong></p>
<p align="center">Signal-based transitions</p>
<p align="center">Branching, merging, loops</p>
<p align="center">Per-node tool scoping</p>
<p align="center">ASCII graph visualization</p>

</td>
<td width="20%" align="center" style="vertical-align: top; padding: 15px;">

<h3>Scheduling</h3>

<p align="center"><strong>Cron Daemon</strong></p>
<p align="center">Cron expressions & intervals</p>
<p align="center">Background task manager</p>
<p align="center">Webhook triggers</p>
<p align="center">One-shot timers</p>

</td>
<td width="20%" align="center" style="vertical-align: top; padding: 15px;">

<h3>21+ Tools</h3>

<p align="center"><strong>File, Shell, Web, MCP</strong></p>
<p align="center">On-demand skill loading</p>
<p align="center">Plugin ecosystem</p>
<p align="center">Persistent memory</p>
<p align="center">Subagent spawning</p>

</td>
<td width="20%" align="center" style="vertical-align: top; padding: 15px;">

<h3>Extensibility</h3>

<p align="center"><strong>Hooks & MCP</strong></p>
<p align="center">Before/after tool hooks</p>
<p align="center">MCP server integration</p>
<p align="center">Plugin bundles</p>
<p align="center">Custom tools via BaseTool</p>

</td>
<td width="20%" align="center" style="vertical-align: top; padding: 15px;">

<h3>Governance</h3>

<p align="center"><strong>Multi-level Permissions</strong></p>
<p align="center">Path & command rules</p>
<p align="center">Interactive approval</p>
<p align="center">Plan mode (read-only)</p>
<p align="center">Multi-provider support</p>

</td>
</tr>
</table>

---

## Quick Start

### Prerequisites

- **Python 3.10+** and [uv](https://docs.astral.sh/uv/)
- **Node.js 18+** (optional, for the React terminal UI)
- An LLM API key

### Install & Run

```bash
# Clone and install
git clone https://github.com/your-org/AgentTree.git
cd AgentTree
uv sync --extra dev

# Set your API key
export ANTHROPIC_API_KEY=sk-...

# Launch interactive mode
uv run agenttree

# Or run a single prompt
uv run agenttree -p "explain this codebase"

# Use OpenAI-compatible provider
uv run agenttree --api-format openai --base-url https://api.openai.com/v1
```

### One-Command Demo

```bash
ANTHROPIC_API_KEY=your_key uv run agenttree -p "Inspect this repository and list the top 3 improvements"
```

---

## Architecture

```mermaid
flowchart LR
    U[User Prompt] --> C[CLI / React TUI]
    C --> R[RuntimeBundle]
    R --> Q[QueryEngine]
    Q --> A[Anthropic / OpenAI API]
    A -->|tool_use| T[Tool Registry — 21+ tools]
    T --> P[Permissions + Hooks]
    P --> X[Files | Shell | Web | MCP | Tasks | Cron]
    X --> Q
```

### The Agent Loop

```python
while True:
    response = await api.stream(messages, tools)
    
    if response.stop_reason != "tool_use":
        break  # Model is done
    
    for tool_call in response.tool_uses:
        # Hook(before) → Permission check → Execute → Hook(after)
        result = await execute_tool(tool_call)
    
    messages.append(tool_results)
    # Loop continues — model sees results, decides next action
```

### Workflow Execution

```
User YAML ──► WorkflowEngine ──► Node 1 (scoped tools, max turns)
                                    │
                                    ▼ signal / pattern / tool match
                                 Node 2 ──► ... ──► Terminal Node
                                    │
                                    ▼ audit trail + progress events
                                 Result
```

The **human** defines the graph. The **AI** operates within each node. **Deterministic transitions** connect them.

---

## Writing Workflows

Place YAML files in `~/.agenttree/workflows/` or `<project>/.agenttree/workflows/`. They are automatically discovered.

### Four Patterns

**Linear** — unconditional transition:
```yaml
scan:
  prompt: "Scan the project structure."
  tools: [glob, bash]
  edges:
    - target: assess
      when: { always: true }
```

**Branch** — signal-based split:
```yaml
assess:
  prompt: "Signal 'well_documented', 'needs_investigation', or 'trivial'."
  edges:
    - target: deep_dive
      when: { signal: needs_investigation }
    - target: summarize
      when: { signal: well_documented }
```

**Loop** — back-edge to self or earlier node:
```yaml
deep_dive:
  prompt: "Read key files. Signal 'dig_deeper' to loop, 'enough' to move on."
  tools: [read_file, grep, glob]
  edges:
    - target: deep_dive
      when: { signal: dig_deeper }
    - target: summarize
      when: { signal: enough }
```

**Terminal** — no edges, workflow ends:
```yaml
summarize:
  prompt: "Write a summary with ## Overview, ## Key Files, ## Architecture."
```

### Full Example

See [`examples/workflows/explore_codebase.yaml`](examples/workflows/explore_codebase.yaml) — all four patterns in one workflow:

```
         ┌────────────┐
         │ scan start │
         └────────────┘
                │
                ▼
         ┌────────────┐
         │   assess   │
         └────────────┘
                │
     ┌──────────┴─────────┐
     │                    │
  needs_investigation   well_documented/trivial
     ▼                    ▼
┌────────────┐     ┌───────────────┐
│ deep_dive  │────►│ summarize end │
└────────────┘     └───────────────┘
     │  ▲
     └──┘ dig_deeper
```

### Transition Conditions

| Condition | Description |
|-----------|-------------|
| `signal: <value>` | LLM called `workflow_signal` with this decision |
| `output_matches: <regex>` | LLM's final text matches the pattern |
| `tool_was_called: <name>` | A specific tool was used during the node |
| `always: true` | Unconditional transition |

All conditions support `negate: true` to invert the match.

### Node Properties

| Property | Default | Description |
|----------|---------|-------------|
| `prompt` | required | Task instructions for the LLM at this step |
| `tools` | `[]` | Tool whitelist (only these tools are available) |
| `max_turns` | `50` | Max LLM turns within this node |
| `carry_context` | `true` | Pass prior node's summary as context |
| `edges` | `[]` | Outgoing transitions (empty = terminal node) |

### Workflow Progress

```
▶ Starting workflow 'pull_request_review' at node 'analyze'
  ● Node 'analyze' — 4 tools, max 10 turns
  ⇢ Transition → 'decide'
  ● Node 'decide' — 0 tools, max 3 turns
  ⇢ Signal 'approve' → moving to 'approve'
✓ Workflow complete. Path: analyze → decide → approve → report
```

---

## Tools (21+)

| Category | Tools | Description |
|----------|-------|-------------|
| **File I/O** | `bash`, `read_file`, `write_file`, `edit_file`, `glob`, `grep` | Core file operations with permission checks |
| **Web** | `web_fetch`, `web_search` | HTTP content retrieval and Brave search |
| **Interaction** | `ask_user_question`, `skill` | User input and on-demand knowledge loading |
| **Tasks** | `task_create`, `task_list`, `task_get`, `task_stop` | Background task lifecycle management |
| **Scheduling** | `cron_create`, `cron_list`, `cron_delete`, `cron_toggle` | Cron job management |
| **Agents** | `agent`, `remote_trigger` | Subagent spawning and webhook triggers |
| **Memory** | `memory_read`, `memory_write` | Persistent cross-session knowledge |
| **MCP** | `mcp_<server>_<tool>` (dynamic) | Auto-registered from MCP servers |

Every tool has **Pydantic input validation**, **self-describing JSON Schema**, **permission integration**, and **hook support**.

---

## Scheduling & Cron

AgentTree includes a standalone cron scheduler daemon for running workflows and commands on a schedule.

```bash
# Start the scheduler daemon
uv run agenttree scheduler start

# Check status
uv run agenttree scheduler status

# Stop
uv run agenttree scheduler stop
```

**Schedule types:**

| Type | Example | Description |
|------|---------|-------------|
| Cron expression | `*/5 * * * *` | Every 5 minutes |
| Interval | `300` seconds | Every 5 minutes |
| One-shot | `2026-04-15T09:00:00` | Run once at a specific time |

**Action types:** shell commands, workflow executions, or webhook calls.

---

## Skills

Skills are **on-demand knowledge** loaded from markdown files with YAML frontmatter.

```markdown
---
name: code-review
description: Review code for correctness and style
---

Review the code changes for:
1. Correctness — does the logic do what's intended?
2. Style — does it follow project conventions?
3. Edge cases — are boundary conditions handled?
```

Place in `~/.agenttree/skills/` or `<project>/.agenttree/skills/`. List with `/skills`, load via the `skill` tool.

---

## Hooks

Lifecycle callbacks that fire before or after tool execution.

```json
{
  "hooks": [
    {
      "type": "command",
      "match": { "event": "after_tool_use", "tool_name": "bash" },
      "command": "echo 'bash was called'",
      "timeout": 10
    },
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

---

## MCP Support

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
uv pip install agenttree[mcp]  # Install MCP support
```

---

## Plugins

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

Place in `~/.agenttree/plugins/<name>/` or `<project>/.agenttree/plugins/<name>/`.

---

## Remote Triggers

Create webhook endpoints that trigger workflows from external systems:

```bash
# The agent creates triggers via the remote_trigger tool
# Each trigger gets a unique ID and secret

POST /trigger/<id>
Header: X-Trigger-Secret: <secret>
```

Use `remote_trigger` tool with `action: "create"` to set up a new endpoint.

---

## Permissions

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

---

## Commands

| Command | Description |
|---------|-------------|
| `/help` | Show all available commands |
| `/workflows` | Browse workflows (interactive picker) |
| `/workflows <name>` | Show workflow graph |
| `/<name> <context>` | Run a workflow directly |
| `/skills` | List available skills |
| `/tasks` | List background tasks |
| `/cron` | List scheduled cron jobs |
| `/model` / `/model <name>` | Show or switch model |
| `/status` | Show session info |
| `/compact` | Compact conversation (reduce tokens) |
| `/permissions set <mode>` | Set permission mode |
| `/clear` | Clear conversation history |
| `/exit` | Exit the session |

---

## Extending AgentTree

### Custom Tool

```python
from pydantic import BaseModel, Field
from agenttree.tools.base import BaseTool, ToolExecutionContext, ToolResult

class MyToolInput(BaseModel):
    query: str = Field(description="Search query")

class MyTool(BaseTool):
    name = "my_tool"
    description = "Does something useful"
    input_model = MyToolInput

    async def execute(self, arguments: MyToolInput, context: ToolExecutionContext) -> ToolResult:
        return ToolResult(output=f"Result for: {arguments.query}")
```

### Custom Skill

Create `~/.agenttree/skills/my-skill.md` with YAML frontmatter.

### Custom Plugin

Create `<project>/.agenttree/plugins/my-plugin/plugin.json` with skills, hooks, and MCP servers.

---

## Test Results

| Suite | Tests | Status |
|-------|-------|--------|
| Skills (registry + tool) | 10 | All passing |
| Tasks (manager + store) | 9 | All passing |
| Hooks (registry + executor) | 7 | All passing |
| Cron (scheduler + store) | 8 | All passing |
| MCP (adapter) | 5 | All passing |
| Triggers (registry) | 3 | All passing |
| Agents (spawner) | 2 | All passing |
| Plugins (loader) | 4 | All passing |
| Memory (store) | 5 | All passing |
| Workflow (evaluator + graph + types) | 44 | All passing |
| Core (engine + permissions + tools) | 22 | All passing |
| **Total** | **119** | **All passing** |

```bash
uv run pytest -q  # Run all tests
```

---

## Project Structure

```
src/agenttree/
  agents/       # Subagent spawning with worktree isolation
  api/          # LLM provider clients (Anthropic, OpenAI)
  config/       # Settings and path management
  cron/         # Cron scheduler daemon and job management
  engine/       # Core agent loop (query, messages, streaming)
  hooks/        # Lifecycle event hooks (command, HTTP)
  mcp/          # Model Context Protocol client integration
  memory/       # Persistent cross-session knowledge
  permissions/  # Permission checking system
  plugins/      # Plugin loader and manifest system
  prompts/      # System prompt builder
  services/     # Auto-compaction service
  skills/       # Skill registry and markdown parser
  state/        # Application state
  tasks/        # Background task manager
  tools/        # 21 built-in tools + base abstraction
  triggers/     # Webhook trigger server and registry
  ui/           # React TUI + backend host + print mode
  workflow/     # Decision tree engine, YAML parser, graph renderer
```

---

## License

MIT

