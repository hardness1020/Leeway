# Writing Workflows

Place YAML files in `~/.leeway/workflows/` or `<project>/.leeway/workflows/`. They are automatically discovered.

## Five Patterns

**Linear** (unconditional transition):
```yaml
scan:
  prompt: "Scan the project structure."
  tools: [glob, bash]
  edges:
    - target: assess
      when: { always: true }
```

**Branch** (signal-based split):
```yaml
assess:
  prompt: "Signal 'well_documented', 'needs_investigation', or 'trivial'."
  edges:
    - target: deep_dive
      when: { signal: needs_investigation }
    - target: summarize
      when: { signal: well_documented }
```

**Loop** (back-edge to self or earlier node):
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

**Terminal** (no edges, workflow ends):
```yaml
summarize:
  prompt: "Write a summary with ## Overview, ## Key Files, ## Architecture."
```

**Parallel** (condition-based concurrent branches):
```yaml
review:
  parallel:
    branches:
      quality:
        when: { always: true }
        prompt: "Review code quality"
        tools: [grep, glob]
        skills: [code_review]
      security:
        when: { signal: security_risk }
        prompt: "Security audit"
        tools: [grep, web_fetch]
        requires_approval: true
      tests:
        when: { signal: has_tests }
        prompt: "Run tests"
        tools: [bash]
    timeout: 300
  edges:
    - target: report
      when: { always: true }
```

All matching branches run concurrently. All triggered branches must complete before transitioning. Branches with `requires_approval: true` ask the user first.

## Full Example

See [`.leeway/workflows/code-health.yaml`](../.leeway/workflows/code-health.yaml). It covers all five patterns in one workflow with skills, hooks, and approval gates.

```
> /workflows
```

<p align="center">
  <img src="../assets/workflow_graph.png" alt="Code-health workflow graph" width="1000">
</p>

## Workflow Properties

Top-level fields in the YAML file:

| Property | Default | Description |
|----------|---------|-------------|
| `name` | required | Workflow identifier (used in commands and logs) |
| `description` | `""` | Human-readable description of the workflow |
| `start_node` | required | Name of the first node to execute |
| `nodes` | required | Dictionary mapping node names to node definitions |
| `global_tools` | `[]` | Tools available in every node (merged with per-node tools) |
| `global_skills` | `[]` | Skills available in every node (merged with per-node skills) |
| `global_hooks` | `[]` | Hooks active in every node (merged with per-node hooks) |
| `global_mcp_servers` | `[]` | MCP servers available in every node (merged with per-node MCP servers) |

## Node Properties

| Property | Default | Description |
|----------|---------|-------------|
| `prompt` | required | Task instructions for the LLM at this step |
| `tools` | `[]` | Tool whitelist (only these tools are available) |
| `max_turns` | `50` | Max LLM turns within this node |
| `carry_context` | `true` | Pass prior node's summary as context |
| `interactive` | `true` | When `true`, the agent can use `ask_user_question` and permission prompts are shown. When `false`, the node runs fully automatically. User prompts are suppressed and parallel approval gates are auto-approved |
| `edges` | `[]` | Outgoing transitions (empty = terminal node) |
| `skills` | `[]` | Skill names scoped to this node |
| `hooks` | `[]` | Node-specific hook definitions |
| `mcp_servers` | `[]` | MCP server names scoped to this node |
| `parallel` | `null` | Parallel execution spec (branches, timeout) |

## Transition Conditions

| Condition | Description |
|-----------|-------------|
| `signal: <value>` | LLM called `workflow_signal` with this decision |
| `output_matches: <regex>` | LLM's final text matches the pattern |
| `tool_was_called: <name>` | A specific tool was used during the node |
| `always: true` | Unconditional transition |

All conditions support `negate: true` to invert the match.

**Turn-budget awareness:** For nodes with signal-based edges, the engine automatically tells the LLM how many turns it has and injects an urgent reminder when 2 turns remain. This prevents the LLM from exhausting its turn budget on investigation without signalling a decision.

## Edge Properties

| Property | Default | Description |
|----------|---------|-------------|
| `target` | required | Name of the destination node |
| `when` | `always` | Transition condition (see table above) |
| `priority` | `0` | Evaluation order: higher-priority edges are checked first |

## Branch Properties

Each branch inside a `parallel` block supports:

| Property | Default | Description |
|----------|---------|-------------|
| `when` | `always` | Condition that triggers this branch |
| `prompt` | required | Branch-specific task instructions |
| `tools` | `[]` | Tool whitelist for this branch |
| `max_turns` | `50` | Max LLM turns within this branch |
| `skills` | `[]` | Skill names scoped to this branch |
| `hooks` | `[]` | Branch-scoped hook definitions |
| `mcp_servers` | `[]` | MCP server names scoped to this branch |
| `requires_approval` | `false` | Human-in-the-loop gate: ask user before executing |

The `parallel` block itself also accepts a `timeout` (default `600` seconds) for how long to wait for all triggered branches to complete.

## Workflow Progress

<p align="center">
  <img src="../assets/workflow_process.png" alt="Workflow execution progress" width="1000">
</p>
