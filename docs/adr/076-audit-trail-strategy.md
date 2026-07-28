# ADR 076 - Audit Trail Strategy

## Status

Accepted

## Context

Regulatory compliance requires comprehensive audit logging of all data lifecycle events.
Auditors need to trace who accessed what data, when, and why — without logging sensitive
values that could themselves create a security risk.

## Decision

Built 8-category audit system with S3 storage, suspicious activity detection, and daily
audit summaries.

## Reasons

- 8 categories cover all data lifecycle events (access, modification, training, secrets)
- S3 storage provides tamper-evident audit trail (no in-place edits)
- Suspicious activity detection catches security issues (repeated failures, off-hours)
- Never logs sensitive values (only metadata like category, actor, resource, outcome)
- Audit summary enables daily security review without reading all entries

## Consequences

- S3 read required to search audit logs (no real-time query)
- No real-time alerting on suspicious activity (batch detection only)
- Future: stream audit logs to CloudWatch for real-time monitoring
