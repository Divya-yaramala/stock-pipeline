# ADR 018 - S3-Based Feature Store

## Status

Accepted

## Context

ML models in the pipeline (anomaly detection, price prediction, sentiment analysis) each compute their own features independently. There was no centralized place to store, retrieve, or share ML features across models and pipeline runs. A feature store was needed to avoid redundant computation and provide a consistent input layer for model serving.

## Decision

Build an S3-based feature store in `ingestion/feature_store.py` instead of adopting a dedicated platform like Feast. Features are stored as JSON objects under `features/{feature_group}/{YYYY}/{MM}/{DD}/{ticker}.json`, with feature groups providing logical organization by feature type.

## Reasons

- **No additional infrastructure needed**: Feast requires a Redis online store and a database offline store. S3 is already provisioned and used for all pipeline storage.
- **S3 already used for all storage**: Keeping all persistence in one place simplifies operations — no second or third data store to monitor, back up, or secure.
- **Simple JSON format easy to query**: Feature files can be read directly with boto3 and parsed as plain Python dicts — no SDK, schema registry, or serialization format to manage.
- **Feature groups provide organization**: The `feature_group` path component logically separates price features, technical features, sentiment features, etc., without requiring a database schema.

## Consequences

- **Less feature-rich than Feast**: Feast provides point-in-time correct joins, online/offline store separation, feature monitoring, and a web UI — none of which are available here.
- **No built-in feature versioning UI**: Feature versions are implicit in the S3 date path; there is no dashboard showing feature drift, staleness, or schema changes over time.
- **Manual feature freshness management**: Nothing automatically flags a feature as stale or re-computes it when upstream data changes — this must be managed by pipeline scheduling.
