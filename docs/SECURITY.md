# TradeCraft — Security Policy

> Version: 1.0.0 | Status: APPROVED | Last Updated: 2026-07-28

## 1. Secrets Management

### Never Commit
- API keys (Kite, AI providers)
- API secrets
- Access tokens
- Passwords
- Private credentials
- Database passwords

### Storage
- Use **environment variables** via `.env` file
- `.env` is in `.gitignore` — never committed
- `.env.example` documents required variables without values

### No OS-Specific Secret Storage
Do not depend on Windows Credential Manager, macOS Keychain, or Linux-specific secret storage for core functionality. OS-native secure storage may later be supported through adapters.

## 2. Credential Handling

| Rule | Implementation |
|------|---------------|
| Never hard-code secrets | All secrets from environment variables |
| Never log secrets | Redact in all log output |
| Never expose in UI | Dashboard never displays raw credentials |
| Never send to AI | API keys never included in LLM prompts |
| Never commit to Git | `.gitignore` enforced |
| Session tokens are ephemeral | Kite access tokens refreshed per session |

## 3. Audit Trail

### Durable Records
Every important trading decision produces an audit record:
- What decision was made
- Who/what made it (system, strategy, user, AI)
- When (UTC timestamp)
- What data was used
- What policy version was active
- What the outcome was

### Tamper Evidence
Audit records are append-only. Deletion of audit records should be detectable.

## 4. Least Privilege

- Zerodha API: Only use required permissions
- Database: Application user has only necessary grants
- AI providers: Only model/completion access
- File system: Application writes only to configured directories

## 5. Log Redaction

All logging must redact:
- API keys and secrets (even partial)
- Access tokens
- Database passwords
- Personal identifiable information

Redaction patterns:
```
api_key="abc...xyz" → api_key="[REDACTED]"
password="secret"   → password="[REDACTED]"
```

## 6. Network Security

- All external API calls over HTTPS
- Certificate validation enabled
- No custom CA bundles without explicit documentation
- Timeout configuration for all network calls

## 7. Dashboard Security

- Dashboard must authenticate users (even in local mode)
- No default passwords in production
- Session management with appropriate timeouts
- CSRF protection on state-changing endpoints
