# Key Technology Decisions — Stock Pipeline

## Why These Technologies?

### Apache Airflow (not Prefect/Luigi)
ADR 001: Broader adoption, better UI, native dbt integration.
Used by: Google, Airbnb, Twitter, NASA.

### Snowflake (not Redshift)
ADR 002: Separates compute from storage, better dbt integration.
Pay per query vs always-on cluster.

### dbt Core (not custom SQL)
ADR 003: Version-controlled transformations, lineage built-in.
Tests on models prevent silent data corruption.

### Isolation Forest (not rule-based anomaly)
ADR 004: Unsupervised — no labeled data needed.
Works well for multivariate financial time series.

### Prophet (not ARIMA)
ADR 005: Handles seasonality + trend + holidays automatically.
Facebook's production forecasting library.

### S3 for everything
ADRs 006, 015, 030...: No additional infrastructure.
Already paying for S3 — use it for cache, audit, lineage, features.

### FastAPI (not Flask/Django)
Native async, auto Swagger UI, Pydantic validation built-in.
Type hints throughout = self-documenting API.

### pytest (not unittest)
Fixtures, parametrize, plugins ecosystem.
716 tests with clean syntax and excellent reporting.

### GitHub Actions (not Jenkins/CircleCI)
Free for public repos, YAML-based, tight GitHub integration.
Matrix builds, caching, artifact upload all built-in.

## Architecture Philosophy
1. Fail fast: validate at ingestion, not serving
2. Immutable data: never overwrite, always version
3. Observable: log everything, trace every run
4. Recoverable: checkpoints + DLQ + rollback
5. Documented: ADR for every major choice
