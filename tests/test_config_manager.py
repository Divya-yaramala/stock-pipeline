import os
from unittest.mock import patch

import pytest

from ingestion.config_manager import (
    AWSConfig,
    get_config_summary,
    load_aws_config,
    load_pipeline_config,
    validate_all_configs,
)

AWS_VARS = {
    "AWS_ACCESS_KEY_ID": "test-key",
    "AWS_SECRET_ACCESS_KEY": "test-secret",
    "AWS_BUCKET_NAME": "test-bucket",
    "AWS_REGION": "us-east-1",
}


def test_load_aws_config_success():
    with patch.dict(os.environ, AWS_VARS, clear=False):
        cfg = load_aws_config()
    assert isinstance(cfg, AWSConfig)
    assert cfg.bucket_name == "test-bucket"
    assert cfg.region == "us-east-1"


def test_load_aws_config_missing():
    with patch.dict(os.environ, {}, clear=True):
        with pytest.raises(ValueError):
            load_aws_config()


def test_load_pipeline_config_defaults():
    with patch.dict(os.environ, {}, clear=True):
        cfg = load_pipeline_config()
    assert "AAPL" in cfg.tickers
    assert cfg.airflow_host == "localhost"
    assert cfg.airflow_port == 8080
    assert cfg.chaos_enabled is False


def test_validate_all_configs_returns_dict():
    with patch("ingestion.config_manager.load_aws_config"), patch(
        "ingestion.config_manager.load_snowflake_config"
    ), patch("ingestion.config_manager.load_postgres_config"), patch(
        "ingestion.config_manager.load_pipeline_config"
    ):
        result = validate_all_configs()
    assert isinstance(result, dict)
    assert "aws" in result
    assert "snowflake" in result
    assert "postgres" in result
    assert "pipeline" in result


def test_get_config_summary_no_secrets():
    with patch.dict(os.environ, {}, clear=True):
        summary = get_config_summary()
    for key in summary:
        assert "password" not in key.lower()
        assert "api_key" not in key.lower()
    assert "tickers" in summary
    assert "region" in summary
