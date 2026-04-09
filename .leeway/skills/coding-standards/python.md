# Python Conventions

## Style
- Follow PEP 8 (enforced by ruff/flake8)
- Use type hints on all public functions
- Prefer `pathlib.Path` over `os.path`
- Use f-strings over `.format()` or `%`

## Patterns
- Use `@dataclass` or Pydantic `BaseModel` for data containers
- Prefer `contextlib.contextmanager` for resource cleanup
- Use `from __future__ import annotations` for deferred type evaluation
- Prefer `Enum` over string constants for fixed choices

## Anti-Patterns
- Bare `except:` (always catch specific exceptions)
- Mutable default arguments (`def f(items=[])`)
- `import *` (always import explicitly)
- Ignoring return values of functions with side effects
