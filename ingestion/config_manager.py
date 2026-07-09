import logging
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


@dataclass
class AWSConfig:
    access_key_id: str = ""
    secret_access_key: str = ""
    bucket_name: str = ""
    region: str = "us-east-1"


@dataclass
class SnowflakeConfig:
    account: str = ""
    user: str = ""
    password: str = ""
    warehouse: str = "STOCK_PIPELINE_WH"
    database: str = "STOCK_PIPELINE_DB"
    schema: str = "MARTS"
    role: str = "SYSADMIN"


@dataclass
class PostgresConfig:
    host: str = "localhost"
    port: int = 5432
    user: str = ""
    password: str = ""
    database: str = "stock_pipeline"


@dataclass
class PipelineConfig:
    tickers: List[str] = field(default_factory=lambda: ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"])
    s3_raw_prefix: str = "raw/stocks"
    anomaly_contamination: float = 0.1
    airflow_host: str = "localhost"
    airflow_port: int = 8080
    news_api_key: str = ""
    openai_api_key: str = ""
    slack_webhook_url: str = ""
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    report_email_to: str = ""
    chaos_enabled: bool = False


def load_aws_config() -> AWSConfig:
    bucket = str(os.environ.get("AWS_BUCKET_NAME", ""))
    if not bucket:
        raise ValueError("Missing required env var: AWS_BUCKET_NAME")
    return AWSConfig(
        access_key_id=str(os.environ.get("AWS_ACCESS_KEY_ID", "")),
        secret_access_key=str(os.environ.get("AWS_SECRET_ACCESS_KEY", "")),
        bucket_name=bucket,
        region=str(os.environ.get("AWS_REGION", "us-east-1")),
    )


def load_snowflake_config() -> SnowflakeConfig:
    account = str(os.environ.get("SNOWFLAKE_ACCOUNT", ""))
    if not account:
        raise ValueError("Missing required env var: SNOWFLAKE_ACCOUNT")
    return SnowflakeConfig(
        account=account,
        user=str(os.environ.get("SNOWFLAKE_USER", "")),
        password=str(os.environ.get("SNOWFLAKE_PASSWORD", "")),
        warehouse=str(os.environ.get("SNOWFLAKE_WAREHOUSE", "STOCK_PIPELINE_WH")),
        database=str(os.environ.get("SNOWFLAKE_DATABASE", "STOCK_PIPELINE_DB")),
        schema=str(os.environ.get("SNOWFLAKE_SCHEMA", "MARTS")),
        role=str(os.environ.get("SNOWFLAKE_ROLE", "SYSADMIN")),
    )


def load_postgres_config() -> PostgresConfig:
    host = str(os.environ.get("POSTGRES_HOST", ""))
    if not host:
        raise ValueError("Missing required env var: POSTGRES_HOST")
    return PostgresConfig(
        host=host,
        port=int(str(os.environ.get("POSTGRES_PORT", "5432"))),
        user=str(os.environ.get("POSTGRES_USER", "")),
        password=str(os.environ.get("POSTGRES_PASSWORD", "")),
        database=str(os.environ.get("POSTGRES_DB", "stock_pipeline")),
    )


def load_pipeline_config() -> PipelineConfig:
    raw_tickers = str(os.environ.get("PIPELINE_TICKERS", ""))
    tickers: List[str] = (
        raw_tickers.split(",") if raw_tickers else ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"]
    )
    return PipelineConfig(
        tickers=tickers,
        airflow_host=str(os.environ.get("AIRFLOW_HOST", "localhost")),
        airflow_port=int(str(os.environ.get("AIRFLOW_PORT", "8080"))),
        news_api_key=str(os.environ.get("NEWS_API_KEY", "")),
        openai_api_key=str(os.environ.get("OPENAI_API_KEY", "")),
        slack_webhook_url=str(os.environ.get("SLACK_WEBHOOK_URL", "")),
        smtp_host=str(os.environ.get("SMTP_HOST", "")),
        smtp_port=int(str(os.environ.get("SMTP_PORT", "587"))),
        smtp_user=str(os.environ.get("SMTP_USER", "")),
        smtp_password=str(os.environ.get("SMTP_PASSWORD", "")),
        report_email_to=str(os.environ.get("REPORT_EMAIL_TO", "")),
        chaos_enabled=str(os.environ.get("CHAOS_ENABLED", "false")).lower() == "true",
    )


def validate_all_configs() -> Dict[str, bool]:
    results: Dict[str, bool] = {}
    loaders: List[Any] = [
        ("aws", load_aws_config),
        ("snowflake", load_snowflake_config),
        ("postgres", load_postgres_config),
        ("pipeline", load_pipeline_config),
    ]
    for name, loader in loaders:
        try:
            loader()
            results[str(name)] = True
            logger.info("%s config loaded successfully", name)
        except Exception as e:
            results[str(name)] = False
            logger.error("%s config failed: %s", name, e)

    passed = [k for k, v in results.items() if v]
    failed = [k for k, v in results.items() if not v]
    if passed:
        logger.info("Configs passed: %s", ", ".join(passed))
    if failed:
        logger.error("Configs failed: %s", ", ".join(failed))
    return results


def get_config_summary() -> Dict[str, Any]:
    raw_tickers = str(os.environ.get("PIPELINE_TICKERS", ""))
    tickers: List[str] = (
        raw_tickers.split(",") if raw_tickers else ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"]
    )
    summary: Dict[str, Any] = {
        "tickers": tickers,
        "region": str(os.environ.get("AWS_REGION", "us-east-1")),
        "warehouse": str(os.environ.get("SNOWFLAKE_WAREHOUSE", "STOCK_PIPELINE_WH")),
        "chaos_enabled": str(os.environ.get("CHAOS_ENABLED", "false")).lower() == "true",
    }
    logger.info("Config summary: %s", summary)
    return summary


if __name__ == "__main__":
    print(get_config_summary())
