# ADR 008 - ML Model Registry Pattern

## Status

Accepted

## Context

As the pipeline grew to include three ML components (Isolation Forest, Prophet, and GPT-3.5), there was no formal way to track which model version was in production, what hyperparameters it was trained with, or how it performed against previous versions. Promoting a new model meant manually updating code and hoping the previous version could be recovered from git history.

## Decision

Build a custom S3-based model registry in `ingestion/model_registry.py` instead of adopting MLflow or a managed registry service. Model metadata (version, params, metrics, status) is stored as JSON under `models/registry/{model_name}/{version}/metadata.json`. Models move through a defined lifecycle: `active` → `staging` → `production` → `archived`.

## Reasons

- **No additional infrastructure required**: S3 is already used for all pipeline data; no new service to run or maintain.
- **S3 already used for data storage**: Keeping model metadata in S3 means one consistent storage layer across data and models.
- **Simple JSON metadata easy to query**: Any Python script can load and inspect model records with a single `get_object` call.
- **MLflow overkill for 3 models**: MLflow introduces a tracking server, artifact store, and UI that add operational complexity not justified for a three-model pipeline.

## Consequences

- **Less feature-rich than MLflow**: No built-in metric comparison charts, run diff views, or model serving integration.
- **No built-in UI for model comparison**: Comparing runs requires querying S3 directly or writing a custom reporting script.
- **Manual promotion process**: Advancing a model from staging to production requires an explicit `promote_model()` call rather than a UI action or automated gate.
