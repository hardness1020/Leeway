---
name: code-review
description: Code quality review — identify patterns, anti-patterns, and improvements
---

# Code Review

When performing a code review, follow these steps:

## Workflow

1. **Scan structure** — use `glob` and `grep` to understand the scope of changes
2. **Read changed files** — focus on logic, not formatting
3. **Check against patterns** — see [checklist.md](checklist.md) for the full checklist
4. **Identify issues** — categorize by severity (critical, major, minor, suggestion)
5. **Write report** — structured as Summary, Issues, Suggestions

## Rules

- Evidence before opinion — cite file:line for every issue
- One issue per point — don't bundle unrelated problems
- Suggest fixes, not just problems — "consider X" is better than "this is wrong"
- Praise good patterns — reinforce what works

## Output Format

```markdown
## Summary
[1-2 sentence overall assessment]

## Issues
- **[severity]** file:line — description

## Suggestions
- file:line — recommendation
```

For the full quality checklist, read [checklist.md](checklist.md).
