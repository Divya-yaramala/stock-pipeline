import os
from unittest.mock import patch

from scripts.validate_secrets import check_required_secrets, print_secrets_report

ALL_VARS = {
    "AWS_ACCESS_KEY_ID": "key",
    "AWS_SECRET_ACCESS_KEY": "secret",
    "AWS_BUCKET_NAME": "bucket",
    "AWS_REGION": "us-east-1",
    "POSTGRES_HOST": "localhost",
    "POSTGRES_PORT": "5432",
    "POSTGRES_USER": "user",
    "POSTGRES_PASSWORD": "pass",
    "POSTGRES_DB": "stocks",
    "SNOWFLAKE_ACCOUNT": "acct",
    "SNOWFLAKE_USER": "user",
    "SNOWFLAKE_PASSWORD": "pass",
    "SNOWFLAKE_WAREHOUSE": "wh",
    "SNOWFLAKE_DATABASE": "db",
    "SNOWFLAKE_SCHEMA": "public",
    "SNOWFLAKE_ROLE": "sysadmin",
    "OPENAI_API_KEY": "sk-test",
    "SLACK_WEBHOOK_URL": "https://hooks.slack.com/test",
}


def test_check_required_secrets_all_present():
    with patch.dict(os.environ, ALL_VARS, clear=True):
        report = check_required_secrets()
    assert report["AWS"]["status"] == "ok"
    assert report["Postgres"]["status"] == "ok"
    assert report["Snowflake"]["status"] == "ok"
    assert report["OpenAI"]["status"] == "ok"


def test_check_required_secrets_missing_aws():
    no_aws = {k: v for k, v in ALL_VARS.items() if not k.startswith("AWS_")}
    with patch.dict(os.environ, no_aws, clear=True):
        report = check_required_secrets()
    assert report["AWS"]["status"] == "missing"
    assert len(report["AWS"]["missing_vars"]) > 0


def test_check_required_secrets_slack_optional():
    no_slack = {k: v for k, v in ALL_VARS.items() if k != "SLACK_WEBHOOK_URL"}
    with patch.dict(os.environ, no_slack, clear=True):
        report = check_required_secrets()
    assert report["Slack"]["status"] == "missing"
    assert report["Slack"]["optional"] is True
    # Required services should still be ok
    assert report["AWS"]["status"] == "ok"


def test_print_secrets_report_ok():
    all_ok_report = {
        "AWS": {"status": "ok", "missing_vars": [], "optional": False},
        "Postgres": {"status": "ok", "missing_vars": [], "optional": False},
        "Snowflake": {"status": "ok", "missing_vars": [], "optional": False},
        "OpenAI": {"status": "ok", "missing_vars": [], "optional": False},
        "Slack": {"status": "ok", "missing_vars": [], "optional": True},
    }
    with patch("scripts.validate_secrets.sys") as mock_sys:
        print_secrets_report(all_ok_report)
        mock_sys.exit.assert_not_called()
