# ADR 038 - Environment-Based Configuration

## Status
Accepted

## Context
The pipeline requires credentials for AWS, Snowflake, PostgreSQL, OpenAI, and Slack. These
values differ across developer machines, CI/CD, and production. Hardcoding or committing
credentials creates security risk and makes multi-environment deployments fragile.

## Decision
All configuration is loaded exclusively from environment variables, sourced from a `.env`
file in development and from the deployment environment in production. The `.env` file is
listed in `.gitignore` and is never committed.

## Reasons
- **12-factor app methodology**: Environment is the standard place for config — separates
  code from config across dev, staging, and production
- **Security**: `.env` never committed to git; no credentials in version history
- **Same code everywhere**: Identical application code runs locally, in CI, and in production
- **Fail-fast validation**: `scripts/validate_secrets.py` checks all required vars at startup
  before the pipeline attempts any network calls
- **python-dotenv compatibility**: `.env.example` documents every variable; `python-dotenv`
  loads `.env` automatically in local development
- **Two-tier secrets model**: Required secrets block the pipeline on absence; optional secrets
  degrade gracefully (e.g. Slack alerts disabled, not a hard failure)

## Consequences
- Developers must manually copy `.env.example` to `.env` and fill in values on first setup
- No config validation until runtime (mitigated by `validate_secrets.py` pre-flight check)
- CI secrets must be configured separately as GitHub Actions secrets
- Future: migrate production secrets to AWS Parameter Store or Secrets Manager for
  centralized rotation and audit logging
