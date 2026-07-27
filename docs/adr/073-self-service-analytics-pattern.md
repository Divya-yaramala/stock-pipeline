# ADR 073 - Self-Service Analytics Pattern

## Status

Accepted

## Context

Business users need access to pipeline metrics without requiring engineering help for every
query. Ad-hoc requests for metric trends, cross-ticker comparisons, and custom reports were
consuming engineering time that should go toward pipeline development.

## Decision

Built self-service analytics with 8 predefined metrics and a custom report builder that
any team can use without code changes.

## Reasons

- 8 metrics cover key business concerns (price, risk, quality, ML, operations)
- Custom report builder combines any metrics for any tickers
- Metric comparison identifies best/worst performing tickers across the portfolio
- Trend analysis shows metric movement over configurable time windows
- All data served from S3 (no database access required)

## Consequences

- Metrics must be pre-computed by pipeline (not real-time)
- Custom reports limited to available metrics
- Future: add SQL interface for ad-hoc queries
