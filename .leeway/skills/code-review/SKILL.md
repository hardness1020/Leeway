---
name: code-review
description: Code quality review — identify patterns, anti-patterns, and improvements. Use when performing code reviews, auditing code quality, or evaluating pull requests for readability, maintainability, and correctness.
---

# Code Review

## Workflow

1. **Scan structure** — use `glob` and `grep` to understand the scope of changes
2. **Read changed files** — focus on logic, not formatting
3. **Check against patterns** — see [references/checklist.md](references/checklist.md) for the full checklist
4. **Identify issues** — categorize by severity (critical, major, minor, suggestion)
5. **Write report** — structured as Summary, Issues, Suggestions

## Rules

- Cite file:line for every issue — evidence before opinion
- Keep one issue per point — don't bundle unrelated problems
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

For the full quality checklist, read [references/checklist.md](references/checklist.md).
