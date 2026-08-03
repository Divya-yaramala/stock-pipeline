# ADR 085 - Pipeline Validation Framework

## Status
Accepted

## Context
Data quality issues catch downstream without systematic validation. Without a structured validation layer, bad data (inverted high/low prices, future dates, missing fields) flows through the pipeline and corrupts downstream analytics, ML model inputs, and financial reports.

## Decision
Built an 8-rule validation framework with contract enforcement. Each validation rule targets a specific data quality dimension: structural, statistical, relational, temporal, business, completeness, uniqueness, and outlier detection.

## Reasons
- 8 rules cover all major data quality dimensions — a single failing check is easy to miss; a suite catches compound failures
- Business rules catch financial data anomalies (high < low is impossible and indicates a data source error)
- Temporal consistency prevents out-of-order data from corrupting time-series models
- Contract enforcement blocks invalid data proactively before it reaches S3 or Postgres
- Violation history enables quality trend analysis — repeated violations signal upstream source degradation
- Pass rate percentage gives a single number for pipeline health dashboards

## Consequences
- Validation adds latency to pipeline (one validation pass per ticker per run)
- Strict rules may block valid edge cases (e.g., trading halts produce zero volume)
- Future: make rules configurable per ticker with per-rule thresholds
