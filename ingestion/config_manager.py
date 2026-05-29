import logging
import os
from dataclasses import dataclass, field
from typing import List

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


@dataclass
class AWSConfig:
    access_key_id: str
    secret_access_key: str
    bucket_name: str
    region: str = "us-east-1"


@dataclass
class PostgresConfig:
    host: str
    port: int
    user: str
    password: str
    database: str


@dataclass
class SnowflakeConfig:
    account: str
    user: str
    password: str
    warehouse: str
    database: str
    schema: str
    role: str


@dataclass
class OpenAIConfig:
    api_key: str
    model: str = "gpt-3.5-turbo"
    max_tokens: int = 200


@dataclass
class PipelineConfig:
    tickers: List[str] = field(
        default_factory=lambda: ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"]
    )
    s3_raw_prefix: str = "raw/stocks"
    s3_processed_prefix: str = "processed"
    forecast_days: int = 5
    anomaly_contamination: float = 0.05
    quality_sla_threshold: float = 80.0


def load_aws_config() -> AWSConfig:
    """Load AWS configuration from environment variables."""
    required = {
        "AWS_ACCESS_KEY_ID": os.environ.get("AWS_ACCESS_KEY_ID", ""),
        "AWS_SECRET_ACCESS_KEY": os.environ.get("AWS_SECRET_ACCESS_KEY", ""),
        "AWS_BUCKET_NAME": os.environ.get("AWS_BUCKET_NAME", ""),
    }
    missing = [k for k, v in required.items() if not v]
    if missing:
        raise ValueError(f"Missing required AWS env vars: {', '.join(missing)}")
    return AWSConfig(
        access_key_id=required["AWS_ACCESS_KEY_ID"],
        secret_access_key=required["AWS_SECRET_ACCESS_KEY"],
        bucket_name=required["AWS_BUCKET_NAME"],
        region=os.environ.get("AWS_REGION", "us-east-1"),
    )


def load_postgres_config() -> PostgresConfig:
    """Load Postgres configuration from environment variables."""
    required = {
        "POSTGRES_HOST": os.environ.get("POSTGRES_HOST", ""),
        "POSTGRES_PORT": os.environ.get("POSTGRES_PORT", ""),
        "POSTGRES_USER": os.environ.get("POSTGRES_USER", ""),
        "POSTGRES_PASSWORD": os.environ.get("POSTGRES_PASSWORD", ""),
        "POSTGRES_DB": os.environ.get("POSTGRES_DB", ""),
    }
    missing = [k for k, v in required.items() if not v]
    if missing:
        raise ValueError(f"Missing required Postgres env vars: {', '.join(missing)}")
    return PostgresConfig(
        host=required["POSTGRES_HOST"],
        port=int(required["POSTGRES_PORT"]),
        user=required["POSTGRES_USER"],
        password=required["POSTGRES_PASSWORD"],
        database=required["POSTGRES_DB"],
    )


def load_snowflake_config() -> SnowflakeConfig:
    """Load Snowflake configuration from environment variables."""
    required = {
        "SNOWFLAKE_ACCOUNT": os.environ.get("SNOWFLAKE_ACCOUNT", ""),
        "SNOWFLAKE_USER": os.environ.get("SNOWFLAKE_USER", ""),
        "SNOWFLAKE_PASSWORD": os.environ.get("SNOWFLAKE_PASSWORD", ""),
        "SNOWFLAKE_WAREHOUSE": os.environ.get("SNOWFLAKE_WAREHOUSE", ""),
        "SNOWFLAKE_DATABASE": os.environ.get("SNOWFLAKE_DATABASE", ""),
        "SNOWFLAKE_SCHEMA": os.environ.get("SNOWFLAKE_SCHEMA", ""),
        "SNOWFLAKE_ROLE": os.environ.get("SNOWFLAKE_ROLE", ""),
    }
    missing = [k for k, v in required.items() if not v]
    if missing:
        raise ValueError(f"Missing required Snowflake env vars: {', '.join(missing)}")
    return SnowflakeConfig(
        account=required["SNOWFLAKE_ACCOUNT"],
        user=required["SNOWFLAKE_USER"],
        password=required["SNOWFLAKE_PASSWORD"],
        warehouse=required["SNOWFLAKE_WAREHOUSE"],
        database=required["SNOWFLAKE_DATABASE"],
        schema=required["SNOWFLAKE_SCHEMA"],
        role=required["SNOWFLAKE_ROLE"],
    )


def load_pipeline_config() -> PipelineConfig:
    """Load pipeline settings from environment variables, using defaults where unset."""
    raw_tickers = os.environ.get("PIPELINE_TICKERS", "")
    tickers = raw_tickers.split(",") if raw_tickers else ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"]
    return PipelineConfig(
        tickers=tickers,
        s3_raw_prefix=os.environ.get("S3_RAW_PREFIX", "raw/stocks"),
        s3_processed_prefix=os.environ.get("S3_PROCESSED_PREFIX", "processed"),
        forecast_days=int(os.environ.get("FORECAST_DAYS", "5")),
        anomaly_contamination=float(os.environ.get("ANOMALY_CONTAMINATION", "0.05")),
        quality_sla_threshold=float(os.environ.get("QUALITY_SLA_THRESHOLD", "80.0")),
    )


def validate_all_configs() -> bool:
    """Load all configs and return True if all succeed, False if any fail."""
    loaders = {
        "AWS": load_aws_config,
        "Postgres": load_postgres_config,
        "Snowflake": load_snowflake_config,
    }
    failed = []
    for name, loader in loaders.items():
        try:
            loader()
            logger.info("%s config loaded successfully", name)
        except ValueError as e:
            logger.error("%s config failed: %s", name, e)
            failed.append(name)

    if failed:
        logger.error("Config validation failed for: %s", ", ".join(failed))
        return False

    logger.info("All configs validated successfully")
    return True
