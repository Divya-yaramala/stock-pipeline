# ADR 019 - Automated Testing Framework

## Status

Accepted

## Context

The pipeline runs daily and produces data consumed by downstream systems and dashboards. Without a systematic way to test pipeline health each day, failures in data quality, AI output coverage, SLA compliance, or API availability were only discovered reactively — after bad data had already propagated. A consistent, automated testing layer was needed to catch these issues proactively and track health trends over time.

## Decision

Build a custom test suite in `ingestion/test_framework.py` with 8 tests across 4 categories: `data_quality`, `ai_quality`, `performance`, and `infrastructure`. Tests run as part of the pipeline, results are saved to S3 under `testing/YYYY/MM/DD/test_results.json`, and a 7-day trend is computed on each run to show whether pipeline health is improving, stable, or declining.

## Reasons

- **Tests run automatically as part of pipeline**: No manual step required — the suite executes on every pipeline run and results land in S3 alongside all other pipeline outputs.
- **Results saved to S3 for trending**: Storing daily pass rates enables `calculate_quality_trend` to compare first-half vs second-half of the history window and classify direction as improving, stable, or declining.
- **Four categories cover the full pipeline**: `data_quality` (freshness, completeness, consistency), `ai_quality` (anomaly detection, prediction accuracy, sentiment coverage), `performance` (pipeline SLA), and `infrastructure` (API health) together exercise every major system component.
- **Pass rate trends show pipeline health over time**: A single daily metric (pass rate %) provides an at-a-glance view of whether the pipeline is getting healthier or degrading, without requiring manual inspection of logs.

## Consequences

- **Must maintain test logic alongside pipeline code**: As pipeline steps change, test assertions must be updated in lockstep — stale tests can produce false-positive pass rates.
- **False positives possible if thresholds not tuned**: Tests that check for data presence rely on S3 path conventions; if a step writes to a new path, the test fails even if data is present.
- **Additional S3 storage for test results**: Each daily run writes one JSON file per day under `testing/`. Storage cost is minimal but accumulates over long time periods without a retention policy.
