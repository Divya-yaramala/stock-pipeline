import os
from unittest.mock import patch

import pytest

from ingestion.config_manager import (
    AWSConfig,
    PostgresConfig,
    SnowflakeConfig,
    load_aws_config,
    load_pipeline_config,
    load_postgres_config,
    load_snowflake_config,
    validate_all_configs,
)

# Minimal env var sets for each service
AWS_VARS = {
    "AWS_ACCESS_KEY_ID": "test-key",
    "AWS_SECRET_ACCESS_KEY": "test-secret",
    "AWS_BUCKET_NAME": "test-bucket",
    "AWS_REGION": "us-east-1",
}

POSTGRES_VARS = {
    "POSTGRES_HOST": "localhost",
    "POSTGRES_PORT": "5432",
    "POSTGRES_USER": "user",
    "POSTGRES_PASSWORD": "pass",
    "POSTGRES_DB": "stocks",
}

SNOWFLAKE_VARS = {
    "SNOWFLAKE_ACCOUNT": "acct",
    "SNOWFLAKE_USER": "user",
    "SNOWFLAKE_PASSWORD": "pass",
    "SNOWFLAKE_WAREHOUSE": "wh",
    "SNOWFLAKE_DATABASE": "db",
    "SNOWFLAKE_SCHEMA": "public",
    "SNOWFLAKE_ROLE": "sysadmin",
}


def test_load_aws_config_success():
    with patch.dict(os.environ, AWS_VARS, clear=False):
        cfg = load_aws_config()
    assert isinstance(cfg, AWSConfig)
    assert cfg.bucket_name == "test-bucket"
    assert cfg.region == "us-east-1"


def test_load_aws_config_missing_var():
    incomplete = {k: v for k, v in AWS_VARS.items() if k != "AWS_BUCKET_NAME"}
    with patch.dict(os.environ, incomplete, clear=False):
        # Remove the key from environment if it exists
        env_copy = {**os.environ, **incomplete}
        env_copy.pop("AWS_BUCKET_NAME", None)
        with patch.dict(os.environ, env_copy, clear=True):
            with pytest.raises(ValueError, match="AWS_BUCKET_NAME"):
                load_aws_config()


def test_load_postgres_config_success():
    with patch.dict(os.environ, POSTGRES_VARS, clear=False):
        cfg = load_postgres_config()
    assert isinstance(cfg, PostgresConfig)
    assert cfg.host == "localhost"
    assert cfg.port == 5432


def test_load_snowflake_config_success():
    with patch.dict(os.environ, SNOWFLAKE_VARS, clear=False):
        cfg = load_snowflake_config()
    assert isinstance(cfg, SnowflakeConfig)
    assert cfg.warehouse == "wh"
    assert cfg.role == "sysadmin"


def test_load_pipeline_config_defaults():
    with patch.dict(os.environ, {}, clear=False):
        cfg = load_pipeline_config()
    assert cfg.forecast_days == 5
    assert cfg.anomaly_contamination == 0.05
    assert cfg.quality_sla_threshold == 80.0
    assert "AAPL" in cfg.tickers


def test_validate_all_configs_success():
    all_vars = {**AWS_VARS, **POSTGRES_VARS, **SNOWFLAKE_VARS}
    with patch.dict(os.environ, all_vars, clear=False):
        result = validate_all_configs()
    assert result is True
