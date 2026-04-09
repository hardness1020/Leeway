# Code Review Checklist

## Quality Patterns (good — note when found)
- [ ] Single responsibility per function/class
- [ ] Dependency injection over hard-coded dependencies
- [ ] Composition over inheritance
- [ ] Immutable data structures where possible
- [ ] Early returns to reduce nesting
- [ ] Descriptive error messages

## Anti-Patterns (flag these)
- [ ] God objects (classes doing too many things)
- [ ] Shotgun surgery (one change requires edits in many places)
- [ ] Copy-paste duplication (3+ similar blocks)
- [ ] Magic numbers/strings without constants
- [ ] Premature optimization at the cost of readability
- [ ] Dead code (unused functions, unreachable branches)
- [ ] Feature envy (method uses another class's data more than its own)

## Complexity Indicators
- [ ] Cyclomatic complexity > 10 per function
- [ ] Function length > 50 lines
- [ ] Nesting depth > 3 levels
- [ ] Parameter count > 5
- [ ] File length > 500 lines
