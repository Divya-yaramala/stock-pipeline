# ADR 022 - Secrets Management Pattern

## Status
Accepted

## Context
The stock pipeline requires API keys, database passwords, and other credentials at runtime. Hardcoding
these values is a critical security risk, and storing them only in environment variables provides no
audit trail, rotation support, or centralised inventory. We needed a secure, auditable mechanism for
storing and retrieving secrets without adding new infrastructure dependencies.

## Decision
Built a custom S3-based secrets manager (`ingestion/secrets_manager.py`) with XOR encryption, audit
logging, and secret rotation support. All secrets are encrypted before storage and never logged in
plaintext. Access events are recorded to an S3 audit trail under `secrets/audit/YYYY/MM/DD/`.

## Reasons
- No additional infrastructure needed — S3 is already used for all pipeline storage
- S3 already used for all storage — reusing it avoids new service dependencies
- Audit logging built-in — every read and write is recorded with timestamp and action
- Secret rotation supported — `rotate_secret()` updates the encrypted value and saves a rotation timestamp
- Never logs actual secret values — all logging references secret names only, never their contents

## Consequences
- XOR encryption less secure than AWS KMS — acceptable for a portfolio project, not for production at scale
- Future improvement: migrate to AWS Secrets Manager or HashiCorp Vault for production-grade encryption
- Manual rotation process required — no automated expiry or rotation scheduling is implemented yet
