---
name: coding-standards
description: General coding standards and best practices checklist
---

# Coding Standards

When reviewing or writing code, check against these standards.

## Naming
- Variables and functions use clear, descriptive names
- Boolean variables start with `is_`, `has_`, `can_`, `should_`
- Constants are UPPER_SNAKE_CASE
- Classes are PascalCase, functions are snake_case (Python) or camelCase (JS/TS)

## Structure
- Functions do one thing and are under 50 lines
- No deeply nested logic (max 3 levels of indentation)
- Related code is grouped; unrelated code is separated
- Imports are organized (stdlib, third-party, local)

## Error Handling
- Errors are handled at the appropriate level, not swallowed
- Error messages are descriptive and actionable
- Resources are properly cleaned up (context managers, try/finally)

## Documentation
- Public APIs have docstrings/JSDoc
- Complex logic has inline comments explaining *why*, not *what*
- README is up to date with setup instructions

For language-specific conventions, see [python.md](python.md) or [typescript.md](typescript.md).
