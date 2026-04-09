---
name: security-audit
description: Security vulnerability audit — check for OWASP top risks and secrets
---

# Security Audit

When auditing code for security, follow these steps:

## Workflow

1. **Search for secrets** — grep for API keys, tokens, passwords in source
2. **Check injection points** — find user input flowing into commands, queries, HTML
3. **Review auth & crypto** — verify password hashing, session management, TLS
4. **Check dependencies** — look for known CVEs, unpinned versions
5. **Write findings** — categorize by severity, cite evidence

## Quick Checks

```bash
# Hardcoded secrets
grep -rn "password\|secret\|api_key\|token" --include="*.py" --include="*.ts" .

# Dangerous functions
grep -rn "eval\|exec\|os.system\|subprocess.call" --include="*.py" .

# SQL injection risk
grep -rn "f\".*SELECT\|f\".*INSERT\|f\".*UPDATE" --include="*.py" .
```

## Rules

- **Critical findings block merge** — hardcoded secrets, RCE, SQL injection
- Cite file:line for every finding
- False positives are OK to flag — better safe than sorry
- Check test files too — test secrets sometimes leak to production

## Output Format

Structure findings by severity:
- **Critical**: Must fix before merge
- **High**: Should fix
- **Medium**: Recommend fixing

For the full OWASP-based checklist, read [owasp.md](owasp.md).
