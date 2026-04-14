# Skills

Skills are **folder-per-skill** packages with a `SKILL.md` entry point and optional supporting files for **progressive disclosure**. The agent loads the main instructions first, then reads detailed references on demand.

## Structure

```
.leeway/skills/
  code-review/
    SKILL.md              # main instructions (loaded first)
    references/
      checklist.md        # detailed checklist (loaded on demand)
  security-audit/
    SKILL.md              # main instructions
    references/
      owasp.md            # OWASP checklist (loaded on demand)
  coding-standards/
    SKILL.md              # main instructions
    references/
      python.md           # Python-specific conventions
      typescript.md       # TypeScript-specific conventions
```

This project includes 3 skills in [`.leeway/skills/`](../.leeway/skills/):

| Skill | Description | References | Used by |
|-------|-------------|------------|---------|
| [`coding-standards`](../.leeway/skills/coding-standards/SKILL.md) | Coding standards checklist | `references/python.md`, `references/typescript.md` | Global (all nodes) |
| [`code-review`](../.leeway/skills/code-review/SKILL.md) | Quality review patterns | `references/checklist.md` | `quality` branch |
| [`security-audit`](../.leeway/skills/security-audit/SKILL.md) | Security vulnerability audit | `references/owasp.md` | `security` branch |

## How Progressive Disclosure Works

1. Agent calls `skill(name="code-review")` and gets SKILL.md content plus a list of reference files
2. SKILL.md says *"For the full checklist, read references/checklist.md"*
3. Agent calls `skill(name="code-review", file="references/checklist.md")` and gets the detailed checklist
4. Only the content needed right now is loaded into context

## SKILL.md Format

```markdown
---
name: code-review
description: Code quality review: identify patterns, anti-patterns, and improvements. Use when performing code reviews, auditing code quality, or evaluating pull requests.
---

# Code Review

## Workflow

1. Scan structure: use `glob` and `grep` to understand the scope of changes
...

For the full quality checklist, read [references/checklist.md](references/checklist.md).
```

The `description` field is the primary trigger: include both what the skill does and when to use it. Supporting files go in `references/`, `scripts/`, or `assets/` subdirectories.

## Scoping

Skills can be scoped per-node or per-branch in workflows:
```yaml
global_skills: [coding-standards]     # available in every node

nodes:
  review:
    parallel:
      branches:
        quality:
          skills: [code-review]       # only this branch gets code-review
```

Place in `~/.leeway/skills/` or `<project>/.leeway/skills/`. Legacy flat `.md` files are also supported. List with `/skills`, load via the `skill` tool.

## Custom Skill

Create `~/.leeway/skills/my-skill.md` with YAML frontmatter.
