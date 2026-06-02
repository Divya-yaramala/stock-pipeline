"""
Validate that all required environment variables are set before running the pipeline.
Usage: python scripts/validate_secrets.py
Exits with code 1 if any required service is missing vars; 0 if only optional Slack is missing.
"""

import logging
import os
import sys

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

REQUIRED_VARS = {
    "AWS": [
        "AWS_ACCESS_KEY_ID",
        "AWS_SECRET_ACCESS_KEY",
        "AWS_BUCKET_NAME",
        "AWS_REGION",
    ],
    "Postgres": [
        "POSTGRES_HOST",
        "POSTGRES_PORT",
        "POSTGRES_USER",
        "POSTGRES_PASSWORD",
        "POSTGRES_DB",
    ],
    "Snowflake": [
        "SNOWFLAKE_ACCOUNT",
        "SNOWFLAKE_USER",
        "SNOWFLAKE_PASSWORD",
        "SNOWFLAKE_WAREHOUSE",
        "SNOWFLAKE_DATABASE",
        "SNOWFLAKE_SCHEMA",
        "SNOWFLAKE_ROLE",
    ],
    "OpenAI": ["OPENAI_API_KEY"],
}

OPTIONAL_VARS = {
    "Slack": ["SLACK_WEBHOOK_URL"],
}


def check_required_secrets() -> dict:
    """Check all required env vars and return a status report grouped by service."""
    report = {}

    for service, vars_list in REQUIRED_VARS.items():
        missing = [v for v in vars_list if not os.environ.get(v, "")]
        report[service] = {
            "status": "missing" if missing else "ok",
            "missing_vars": missing,
            "optional": False,
        }

    for service, vars_list in OPTIONAL_VARS.items():
        missing = [v for v in vars_list if not os.environ.get(v, "")]
        report[service] = {
            "status": "missing" if missing else "ok",
            "missing_vars": missing,
            "optional": True,
        }

    return report


def print_secrets_report(report: dict) -> None:
    """Log a formatted table of secret validation results and exit on failure."""
    col_service = 12
    col_status = 12

    logger.info("")
    logger.info("  %-*s %-*s Missing Vars", col_service, "Service", col_status, "Status")
    logger.info("  " + "-" * 60)

    required_missing = False
    optional_missing = False

    for service, data in report.items():
        if data["status"] == "ok":
            status_str = "✅ ok"
        elif data["optional"]:
            status_str = "⚠️  missing"
            optional_missing = True
        else:
            status_str = "❌ missing"
            required_missing = True

        missing_str = ", ".join(data["missing_vars"]) if data["missing_vars"] else ""
        logger.info("  %-*s %-*s %s", col_service, service, col_status, status_str, missing_str)

    logger.info("")

    if required_missing:
        logger.error("Required secrets are missing — pipeline cannot run")
        sys.exit(1)

    if optional_missing:
        logger.warning("Optional Slack webhook is not set — Slack alerts will be disabled")


if __name__ == "__main__":
    result = check_required_secrets()
    print_secrets_report(result)
    logger.info("Secrets validation passed")
