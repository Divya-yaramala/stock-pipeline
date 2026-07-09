import os
from unittest.mock import patch

from scripts.validate_secrets import check_secrets

REQUIRED_VARS = {
    "AWS_ACCESS_KEY_ID": "key",
    "AWS_SECRET_ACCESS_KEY": "secret",
    "AWS_BUCKET_NAME": "bucket",
    "POSTGRES_HOST": "localhost",
    "POSTGRES_USER": "user",
    "POSTGRES_PASSWORD": "pass",
    "POSTGRES_DB": "stocks",
    "SNOWFLAKE_ACCOUNT": "acct",
    "SNOWFLAKE_USER": "user",
    "SNOWFLAKE_PASSWORD": "pass",
}


def test_check_secrets_all_present():
    with patch.dict(os.environ, REQUIRED_VARS, clear=True):
        report = check_secrets()
    assert report["all_required_present"] is True


def test_check_secrets_missing_required():
    missing_pass = {k: v for k, v in REQUIRED_VARS.items() if k != "POSTGRES_PASSWORD"}
    with patch.dict(os.environ, missing_pass, clear=True):
        report = check_secrets()
    assert report["all_required_present"] is False


def test_check_secrets_optional_missing():
    with patch.dict(os.environ, REQUIRED_VARS, clear=True):
        report = check_secrets()
    assert report["all_required_present"] is True
    assert report["optional"]["Slack"]["status"] == "missing"


def test_check_secrets_structure():
    with patch.dict(os.environ, {}, clear=True):
        report = check_secrets()
    assert "required" in report
    assert "optional" in report
    assert "all_required_present" in report


def test_check_secrets_aws_status():
    aws_vars = {
        "AWS_ACCESS_KEY_ID": "key",
        "AWS_SECRET_ACCESS_KEY": "secret",
        "AWS_BUCKET_NAME": "bucket",
    }
    with patch.dict(os.environ, aws_vars, clear=True):
        report = check_secrets()
    assert report["required"]["AWS"]["status"] == "ok"
