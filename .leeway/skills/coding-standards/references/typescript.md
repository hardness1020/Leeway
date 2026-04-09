# TypeScript Conventions

## Style
- Strict mode enabled (`"strict": true` in tsconfig)
- Use `interface` for object shapes, `type` for unions/intersections
- Prefer `const` over `let`; never use `var`
- Use optional chaining (`?.`) and nullish coalescing (`??`)

## Patterns
- Prefer `readonly` properties for immutable data
- Use discriminated unions for state machines
- Prefer `unknown` over `any` at type boundaries
- Use `satisfies` operator for type checking without widening

## Anti-Patterns
- `any` without justification
- Non-null assertion (`!`) hiding potential bugs
- Type casting (`as`) to bypass type errors
- Unused `@ts-ignore` comments
