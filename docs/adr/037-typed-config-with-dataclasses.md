# ADR 037 - Typed Configuration with Python Dataclasses

## Status
Accepted

## Context
The pipeline spans multiple services (AWS, Snowflake, PostgreSQL, Airflow) each requiring
configuration loaded from environment variables. As the number of config values grew past 30,
scattered `os.environ.get()` calls made it hard to audit what was needed, what had defaults,
and which values were secret. We needed a single, type-safe source of truth for all config.

## Decision
Built a typed configuration system in `ingestion/config_manager.py` using Python dataclasses:

- Four dataclasses: `AWSConfig`, `SnowflakeConfig`, `PostgresConfig`, `PipelineConfig`
- Four typed loader functions with explicit fail-fast on required keys
- `validate_all_configs()` returning `Dict[str, bool]` per service
- `get_config_summary()` that never exposes passwords or API keys
- Companion CLI `scripts/validate_secrets.py` for pre-flight checks with required/optional tiers

## Reasons
- **Type hints + defaults**: Dataclasses provide IDE completion and document expected types
- **Fail-fast on missing config**: `ValueError` raised immediately if critical key absent
- **Secrets hygiene**: `get_config_summary()` returns only non-sensitive values — safe to log
- **Single source of truth**: One file enumerates every config key used across the pipeline
- **No external dependencies**: Standard library only (`dataclasses`, `os`, `typing`)
- **Two-tier secrets check**: Required secrets block the pipeline; optional ones warn only

## Consequences
- Must update the dataclasses when a new config value is added
- No hot-reload of config — pipeline restart required for env var changes
- `validate_all_configs()` makes one loader call per service on startup (negligible cost)
- Future: migrate to Pydantic v2 `BaseSettings` for automatic env parsing and validation
