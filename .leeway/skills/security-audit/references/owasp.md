# OWASP-Based Security Checklist

## A01: Broken Access Control
- [ ] Authorization checks on every endpoint/handler
- [ ] Principle of least privilege applied
- [ ] CORS properly configured
- [ ] Directory listing disabled

## A02: Cryptographic Failures
- [ ] Passwords hashed with bcrypt/argon2 (not MD5/SHA1)
- [ ] Secrets loaded from environment, not hardcoded
- [ ] HTTPS enforced for all external communication
- [ ] Sensitive data not in logs or error messages

## A03: Injection
- [ ] SQL: parameterized queries, no string concatenation
- [ ] Command: no os.system/eval/exec with user input
- [ ] XSS: output encoding, CSP headers
- [ ] Path traversal: validate file paths, reject `../`

## A04: Insecure Design
- [ ] Input validation at system boundaries
- [ ] Rate limiting on authentication endpoints
- [ ] Fail securely (deny by default)

## A05: Security Misconfiguration
- [ ] Debug mode disabled in production
- [ ] Default credentials changed
- [ ] Error messages don't leak stack traces
- [ ] Security headers set (X-Content-Type-Options, etc.)

## A06: Vulnerable Components
- [ ] No known CVEs in dependencies
- [ ] Dependencies pinned to specific versions
- [ ] Regular dependency update process

## A08: Software and Data Integrity
- [ ] Deserialization uses safe loaders (yaml.safe_load, not yaml.load)
- [ ] File uploads validated (type, size, content)
- [ ] CI/CD pipeline protected from injection
