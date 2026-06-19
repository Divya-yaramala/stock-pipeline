# ADR 017 - Data Governance Pattern

## Status

Accepted

## Context

As the pipeline grew to manage multiple datasets (raw prices, anomalies, predictions, insights), there was no systematic way to classify data sensitivity, track who accessed what, enforce retention policies, or generate a compliance score. Governance tooling was needed to meet data management best practices.

## Decision

Build a custom governance module in `ingestion/data_governance.py` with S3-based audit logs, data classification (PUBLIC / INTERNAL / CONFIDENTIAL), SHA-256 field masking, retention policy checks, and a compliance report. A companion `ingestion/compliance_checker.py` evaluates 5 compliance rules and produces a percentage score.

## Reasons

- **No additional tools needed**: S3 is already the pipeline's primary storage layer — audit logs stored there require no new infrastructure.
- **Audit logs persist indefinitely**: S3 objects survive process restarts and container redeploys, giving a durable, queryable audit trail.
- **Classification rules easy to customize**: PII field detection is a simple set intersection; adding new sensitive fields requires one line of code.
- **Compliance score gives clear metric**: A single `score_pct` float makes it easy to set thresholds, alert on regressions, and track improvement over time.

## Consequences

- **Less feature-rich than enterprise tools like Collibra**: Purpose-built governance platforms offer data lineage graphs, business glossary, stewardship workflows, and role-based access — none of which are in this module.
- **Manual classification process**: Datasets must be explicitly classified by calling `classify_data`; there is no automatic discovery or ML-based inference.
- **No real-time compliance alerts**: The compliance check runs on demand or as a scheduled pipeline step — it does not emit events when a violation first occurs.
