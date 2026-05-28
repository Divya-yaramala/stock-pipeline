# ADR 006 - S3 Cost Optimization Strategy

## Status

Accepted

## Context

S3 storage costs grow over time as raw OHLCV data accumulates daily for all tracked tickers. Without a retention policy, every raw JSON file written since pipeline inception remains in standard S3 storage indefinitely, accruing cost at the standard $0.023/GB/month rate. Monitoring and reporting files also accumulate but are only consulted for short-term observability.

## Decision

Apply a two-tier retention policy:

- **Raw data**: archive files under `raw/stocks/` that are older than 30 days by moving them to the `archive/raw/stocks/` prefix.
- **Monitoring data**: delete files under `monitoring/` that are older than 7 days.

Monthly cost is estimated by summing all object sizes in the bucket and multiplying by $0.023/GB.

## Reasons

- Raw stock data is rarely accessed after 30 days; historical analysis typically reads from the Postgres/Snowflake layer, not raw S3 JSON.
- Monitoring data (pipeline run metrics, resource snapshots, SLA records) is only useful for short-term debugging and alerting; 7 days covers any reasonable incident investigation window.
- Moving to an `archive/` prefix keeps files accessible without the operational complexity of S3 Glacier transitions.

## Consequences

- Archived raw data remains accessible under the `archive/raw/stocks/` prefix — no data is permanently lost.
- Monitoring files older than 7 days are permanently deleted; ensure any long-term observability needs are met by the Snowflake sync before deletion.
- The `run_s3_optimization` task runs at the end of every daily DAG execution with `TriggerRule.ALL_DONE`, so optimization happens regardless of upstream failures.
