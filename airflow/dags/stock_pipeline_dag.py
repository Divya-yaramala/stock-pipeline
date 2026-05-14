"""
Stock Price Data Pipeline DAG
==============================
Schedule  : Weekdays at 18:00 UTC (after US market close)
Flow      : yfinance → S3 (JSON per ticker) → Postgres staging → dbt → anomaly detection → price prediction
"""
import logging
import os
from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator, ShortCircuitOperator

log = logging.getLogger(__name__)


def _is_trading_day(**context) -> bool:
    """Skip the pipeline on weekends."""
    execution_date: datetime = context["logical_date"]
    if execution_date.weekday() >= 5:
        log.info("Execution date %s is a weekend — skipping run", execution_date.date())
        return False
    return True


def _fetch_and_upload_to_s3(**context) -> None:
    """Fetch OHLCV data for all tickers and upload JSON files to S3."""
    from fetch_stocks import run_pipeline
    run_pipeline()


def _load_to_postgres_staging(**context) -> None:
    """Load stock JSON files from S3 into the Postgres raw staging layer."""
    log.info("Postgres staging load — to be implemented in Day 4")


def _run_anomaly_detection(**context) -> None:
    """Run Isolation Forest anomaly detection on today's stock data."""
    from anomaly_detector import run_anomaly_detection
    run_anomaly_detection()


def _run_price_prediction(**context) -> None:
    """Run Prophet price prediction and save forecasts to S3."""
    from price_predictor import run_price_prediction
    run_price_prediction()


default_args = {
    "owner": "data-engineer",
    "depends_on_past": False,
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
}

DBT_DIR = "/opt/dbt/stock_analytics"
DBT_CMD = f"cd {DBT_DIR} && dbt {{}} --profiles-dir {DBT_DIR} --target dev"

with DAG(
    dag_id="stock_price_pipeline",
    default_args=default_args,
    description="Daily stock price ingestion → S3 (JSON) → Postgres → dbt → anomaly detection",
    schedule="0 18 * * 1-5",
    start_date=datetime(2024, 1, 1),
    catchup=False,
    max_active_runs=1,
    tags=["stocks", "pipeline", "portfolio"],
) as dag:

    check_trading_day = ShortCircuitOperator(
        task_id="check_trading_day",
        python_callable=_is_trading_day,
        doc_md="Short-circuit on weekends so downstream tasks are skipped cleanly.",
    )

    fetch_and_upload_to_s3 = PythonOperator(
        task_id="fetch_and_upload_to_s3",
        python_callable=_fetch_and_upload_to_s3,
        doc_md="Fetch OHLCV data via yfinance and upload one JSON file per ticker to S3.",
    )

    load_to_postgres_staging = PythonOperator(
        task_id="load_to_postgres_staging",
        python_callable=_load_to_postgres_staging,
        doc_md="Load today's stock data from S3 into raw.stock_prices in Postgres.",
    )

    run_dbt_models = BashOperator(
        task_id="run_dbt_models",
        bash_command=(
            DBT_CMD.format("run --select staging intermediate mart")
            + " && "
            + DBT_CMD.format("test")
        ),
        doc_md="Build all dbt models (staging → intermediate → mart) and run data-quality tests.",
    )

    run_anomaly_detection = PythonOperator(
        task_id="run_anomaly_detection",
        python_callable=_run_anomaly_detection,
        doc_md="Run Isolation Forest on today's OHLCV data and write anomaly results to S3.",
    )

    run_price_prediction = PythonOperator(
        task_id="run_price_prediction",
        python_callable=_run_price_prediction,
        doc_md="Run Prophet model to predict next 5 days of closing prices and write forecasts to S3.",
    )

    (
        check_trading_day
        >> fetch_and_upload_to_s3
        >> load_to_postgres_staging
        >> run_dbt_models
        >> run_anomaly_detection
        >> run_price_prediction
    )
