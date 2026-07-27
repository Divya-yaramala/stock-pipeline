# ADR 074 - Data Mesh Access Control Pattern

## Status

Accepted

## Context

Data products need controlled access between teams. Without a formal process, any team
could consume any data product without the producer's knowledge, making schema changes
risky and compliance difficult to audit.

## Decision

Built request-approval workflow for data product access using S3-based records.

## Reasons

- Access requests create audit trail of who accessed what and why
- Approval workflow enforces data ownership (producer controls access)
- Sample data allows consumer evaluation before committing to full access
- Versioned changelogs notify consumers of schema changes
- S3-based storage requires no additional infrastructure

## Consequences

- Manual approval process (no automated rules yet)
- Access control is advisory (not enforced at S3 level)
- Future: integrate with AWS IAM for enforced access control
