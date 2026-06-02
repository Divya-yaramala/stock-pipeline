import logging
import os
import sys

import boto3
import psycopg2

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def check_s3_connectivity() -> dict:
    """
    Try to list the configured S3 bucket and return a health status dict.

    Returns:
        Dict with keys 'service', 'status' ('healthy'/'unhealthy'), and 'message'.
    """
    bucket = os.environ.get("AWS_BUCKET_NAME", "")
    region = os.environ.get("AWS_REGION", "us-east-1")
    try:
        s3 = boto3.client("s3", region_name=region)
        s3.list_objects_v2(Bucket=bucket, MaxKeys=1)
        return {"service": "S3", "status": "healthy", "message": f"Connected to bucket {bucket}"}
    except Exception as e:
        return {"service": "S3", "status": "unhealthy", "message": str(e)}


def check_postgres_connectivity() -> dict:
    """
    Try to connect to Postgres and return a health status dict.

    Returns:
        Dict with keys 'service', 'status' ('healthy'/'unhealthy'), and 'message'.
    """
    try:
        conn = psycopg2.connect(
            host=os.environ.get("POSTGRES_HOST", "localhost"),
            port=os.environ.get("POSTGRES_PORT", "5432"),
            user=os.environ.get("POSTGRES_USER", ""),
            password=os.environ.get("POSTGRES_PASSWORD", ""),
            dbname=os.environ.get("POSTGRES_DB", ""),
        )
        conn.close()
        return {"service": "Postgres", "status": "healthy", "message": "Connected to DB"}
    except Exception as e:
        return {"service": "Postgres", "status": "unhealthy", "message": str(e)}


def check_snowflake_connectivity() -> dict:
    """
    Try to connect to Snowflake and return a health status dict.

    Returns:
        Dict with keys 'service', 'status' ('healthy'/'unhealthy'), and 'message'.
    """
    try:
        import snowflake.connector

        conn = snowflake.connector.connect(
            account=os.environ.get("SNOWFLAKE_ACCOUNT", ""),
            user=os.environ.get("SNOWFLAKE_USER", ""),
            password=os.environ.get("SNOWFLAKE_PASSWORD", ""),
        )
        conn.close()
        return {"service": "Snowflake", "status": "healthy", "message": "Connected"}
    except Exception as e:
        return {"service": "Snowflake", "status": "unhealthy", "message": str(e)}


def check_openai_connectivity() -> dict:
    """
    Try a minimal OpenAI API call and return a health status dict.

    Returns:
        Dict with keys 'service', 'status' ('healthy'/'unhealthy'), and 'message'.
    """
    try:
        import openai

        client = openai.OpenAI(api_key=os.environ.get("OPENAI_API_KEY", ""))
        client.models.list()
        return {"service": "OpenAI", "status": "healthy", "message": "API responding"}
    except Exception as e:
        return {"service": "OpenAI", "status": "unhealthy", "message": str(e)}


def run_health_check() -> None:
    """
    Run all connectivity checks, log a report table, and exit 1 if any fail.

    Calls check_s3_connectivity, check_postgres_connectivity,
    check_snowflake_connectivity, and check_openai_connectivity, then logs
    results and sends a Slack failure alert if any service is unhealthy.
    """
    checks = [
        check_s3_connectivity(),
        check_postgres_connectivity(),
        check_snowflake_connectivity(),
        check_openai_connectivity(),
    ]

    logger.info("%-12s| %-12s| Message", "Service", "Status")
    logger.info("-" * 60)
    any_unhealthy = False
    for result in checks:
        service = result["service"]
        status = result["status"]
        message = result["message"]
        icon = "✅" if status == "healthy" else "❌"
        logger.info("%-12s| %s %-10s| %s", service, icon, status, message)
        if status != "healthy":
            any_unhealthy = True

    if any_unhealthy:
        from ingestion import slack_alerter

        unhealthy = [r["service"] for r in checks if r["status"] != "healthy"]
        slack_alerter.alert_pipeline_failure(
            "health_check", "pipeline", f"Unhealthy services: {', '.join(unhealthy)}"
        )
        logger.error("Health check FAILED — unhealthy services: %s", unhealthy)
        sys.exit(1)

    logger.info("Health check PASSED — all services healthy")
    sys.exit(0)


if __name__ == "__main__":
    run_health_check()
