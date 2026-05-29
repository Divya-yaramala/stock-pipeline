# ADR 007 - Typed Configuration with Python Dataclasses

## Status

Accepted

## Context

Environment variables were loaded in a scattered fashion across modules — `os.environ.get("AWS_BUCKET_NAME", "")` appeared in `fetch_stocks.py`, `anomaly_detector.py`, `s3_optimizer.py`, and others. There was no central validation, so a missing variable would only surface as a runtime error deep inside a pipeline step, often after minutes of work had already been done.

## Decision

Centralize all environment variable loading in `ingestion/config_manager.py` using Python dataclasses (`AWSConfig`, `PostgresConfig`, `SnowflakeConfig`, `OpenAIConfig`, `PipelineConfig`). Each loader raises `ValueError` immediately if a required variable is absent. `validate_all_configs()` provides a single call to fail fast at pipeline startup.

## Reasons

- **Type safety**: Dataclasses give each config field an explicit type; `port` is an `int`, not a string from `os.environ`.
- **Single source of truth**: All env var names and defaults live in one file, making it easy to audit what the pipeline requires.
- **Early error detection**: Missing credentials are caught before any S3, Postgres, or Snowflake calls are made, producing a clear error message rather than a cryptic boto3 or psycopg2 exception.
- **Testability**: Tests can patch `os.environ` once and call `load_aws_config()` rather than patching individual `os.getenv` calls scattered across modules.

## Consequences

- `config_manager.py` is an additional module to maintain; changes to required env vars must be updated there.
- All pipeline modules that previously called `os.environ.get` directly now depend on `config_manager`, adding an internal coupling. This is acceptable because the config contract changes infrequently.
- The `validate_secrets.py` CLI script provides a human-readable pre-flight check that mirrors the programmatic validation.
