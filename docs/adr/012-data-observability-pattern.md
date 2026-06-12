# ADR 012 - Data Observability Pattern

## Status

Accepted

## Context

The pipeline needed visibility into data freshness, completeness, and consistency across all five tickers and multiple S3 paths. The industry-standard tool for data quality and observability is Great Expectations, which provides a rich framework for defining expectations, running validation suites, and generating data docs.

## Decision

Build custom observability checks in `ingestion/data_observatory.py` instead of integrating Great Expectations into the pipeline.

## Reasons

- **Great Expectations requires heavy setup and configuration**: Great Expectations requires initialising a data context, defining expectation suites, configuring datasources, and managing checkpoint YAML files — significant overhead for a pipeline of this scope.
- **Custom checks tailored to our specific S3 structure**: Our checks are written directly against our S3 path conventions (`raw/stocks/YYYY/MM/DD/ticker.json`, `processed/anomalies/...`, etc.), making them precise and easy to understand without abstraction layers.
- **No additional dependencies needed**: Great Expectations pulls in a large dependency tree. Our checks use only boto3 and the standard library, which are already in `requirements.txt`.
- **Simpler to maintain and extend**: Adding a new check (e.g., a new processed S3 path) is a one-line change to `REQUIRED_PATHS`. There is no YAML config or expectation suite to update in parallel.

## Consequences

- **Less feature-rich than Great Expectations**: Great Expectations provides built-in data docs, column-level statistics, and a large library of pre-built expectations that we would need to implement ourselves.
- **Must maintain our own check logic**: Any bugs in freshness, completeness, or consistency logic are our responsibility.
- **No built-in UI for observability results**: Great Expectations generates HTML data docs automatically; our results are JSON saved to S3 with no visualisation layer.
