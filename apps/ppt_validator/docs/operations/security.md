# Security — NOW

## Purpose

Protect API keys, customer data, PII, and confidential proposal information.

## Secrets Management

| Secret | Storage | Rule |
|--------|---------|------|
| LLM API keys | `.env` file (gitignored) | Never committed to source |
| Database passwords | `.env` file (gitignored) | Never committed |
| LangSmith key | `.env` file (gitignored) | Never committed |
| TruLens eval provider key | `.env` file (gitignored) | Never committed |

`.env.example` uses `<placeholder>` for all secret values. No real values in examples.

## PII in PPT Content

PPT files and proposal contexts may contain:
- Client names, contact details
- Financial figures and projections
- Confidential business requirements
- Contract terms and pricing

### Controls

1. **LangSmith payload capture**: configurable (see [../prompts/prompt-security.md](../prompts/prompt-security.md))
2. **TruLens eval**: receives only evaluation inputs, not full PPT content
3. **Logging**: slide content is not logged to application logs by default
4. **Storage**: PPT files stored with access controls (user/project isolation)

### PII Redaction Filter

When `LANGSMITH_REDACT_PII=true`:
- Email addresses → `[EMAIL]`
- Phone numbers → `[PHONE]`
- Client names (from Review Profile) → `[CLIENT_NAME]`
- Applied before sending to any external observability tool

## Customer Isolation

Each review run is scoped to a user/project. Users cannot access other users' review results,
PPT files, or proposal contexts.

## Access Control

| Role | Capabilities |
|------|------------|
| `reviewer` | Submit PPTs for review; view own results |
| `prompt_admin` | Create/activate prompt versions |
| `admin` | Full access including user management and budget configuration |

## API Security

- Authentication required for all API endpoints
- JWT or session token (configured at deployment)
- Rate limiting per user/IP
- Request size limit: `MAX_UPLOAD_SIZE_MB=50` for PPT files

## Audit Logs

All security-relevant events are logged in `audit_logs`:
- User authentication events
- Prompt version activation
- Budget configuration changes
- Admin actions

## Prompt Injection

See: [../prompts/prompt-security.md](../prompts/prompt-security.md) for prompt injection controls.

## Retention

| Data | Retention |
|------|----------|
| PPT files | Configurable (default: 90 days) |
| Review results | Indefinite (audit trail) |
| LLM request logs | Indefinite (audit trail) |
| Human feedback | Indefinite |
| LangSmith traces | Per LangSmith project settings |

## Production Checklist

- [ ] `.env` not committed (`.gitignore` includes `.env`)
- [ ] `.env.example` has no real values
- [ ] `LANGSMITH_REDACT_PII=true` for customer-data environments
- [ ] `LANGSMITH_CAPTURE_INPUTS` and `CAPTURE_OUTPUTS` reviewed before production
- [ ] Database access restricted to application user only
- [ ] PPT file storage access restricted to application service

## Related Documents

- See: [../prompts/prompt-security.md](../prompts/prompt-security.md) for prompt-specific security
- See: [../operations/observability.md](../operations/observability.md) for observability payload controls
