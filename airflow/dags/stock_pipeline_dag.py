"""
Stock Price Data Pipeline DAG
==============================
Schedule  : Weekdays at 18:00 UTC (after US market close)
Flow      : yfinance → S3 (JSON per ticker) → Postgres staging → dbt → anomaly detection → price prediction → market insights
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
    """Load today's stock JSON files from S3 into staging.stock_prices_raw."""
    import json
    import os
    import boto3 as _boto3
    from datetime import datetime as _dt
    from scripts.setup_postgres import load_to_postgres

    date = _dt.now().strftime("%Y/%m/%d")
    trade_date = _dt.now().strftime("%Y-%m-%d")
    bucket = os.environ.get("AWS_BUCKET_NAME", "")
    region = os.environ.get("AWS_REGION", "us-east-1")
    tickers = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"]

    insert_sql = """
        INSERT INTO staging.stock_prices_raw
            (ticker, trade_date, open_price, high_price, low_price, close_price, volume)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (ticker, trade_date) DO NOTHING
    """

    s3 = _boto3.client("s3", region_name=region)

    for ticker in tickers:
        key = f"raw/stocks/{date}/{ticker}.json"
        try:
            response = s3.get_object(Bucket=bucket, Key=key)
            data = json.loads(response["Body"].read().decode("utf-8"))

            opens   = data.get("Open")   or data.get("open")   or {}
            highs   = data.get("High")   or data.get("high")   or {}
            lows    = data.get("Low")    or data.get("low")    or {}
            closes  = data.get("Close")  or data.get("close")  or {}
            volumes = data.get("Volume") or data.get("volume") or {}

            rows = [(
                ticker,
                trade_date,
                next(iter(opens.values()),   None),
                next(iter(highs.values()),   None),
                next(iter(lows.values()),    None),
                next(iter(closes.values()),  None),
                next(iter(volumes.values()), None),
            )]

            if load_to_postgres(rows, insert_sql):
                log.info("Inserted %d row(s) for %s into staging.stock_prices_raw", len(rows), ticker)
            else:
                log.warning("Failed to insert %s into staging.stock_prices_raw", ticker)
        except Exception as e:
            log.error("Error loading %s from S3: %s", ticker, e)


def _run_anomaly_detection(**context) -> None:
    """Run Isolation Forest anomaly detection on today's stock data."""
    from anomaly_detector import run_anomaly_detection
    run_anomaly_detection()


def _run_price_prediction(**context) -> None:
    """Run Prophet price prediction and save forecasts to S3."""
    from price_predictor import run_price_prediction
    run_price_prediction()


def _run_market_insights(**context) -> None:
    """Generate GPT-powered market insight summaries and save to S3."""
    from market_insights import run_market_insights
    run_market_insights()


def _run_snowflake_sync(**context) -> None:
    """Sync all processed data from S3 into Snowflake raw layer."""
    from snowflake_sync import run_snowflake_sync
    run_snowflake_sync()


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

    # Task 1 — Gate: skip the entire DAG on weekends (no market data available)
    check_trading_day = ShortCircuitOperator(
        task_id="check_trading_day",
        python_callable=_is_trading_day,
        doc_md="Short-circuit on weekends so downstream tasks are skipped cleanly.",
    )

    # Task 2 — Ingestion: pull OHLCV prices from Yahoo Finance and persist raw JSON to S3
    fetch_and_upload_to_s3 = PythonOperator(
        task_id="fetch_and_upload_to_s3",
        python_callable=_fetch_and_upload_to_s3,
        doc_md="Fetch OHLCV data via yfinance and upload one JSON file per ticker to S3.",
    )

    # Task 3 — Staging: read today's JSON files from S3 and upsert into staging.stock_prices_raw
    load_to_postgres_staging = PythonOperator(
        task_id="load_to_postgres_staging",
        python_callable=_load_to_postgres_staging,
        doc_md="Load today's stock data from S3 into raw.stock_prices in Postgres.",
    )

    # Task 4 — Transformation: run dbt models (staging → intermediate → mart) and data-quality tests
    run_dbt_models = BashOperator(
        task_id="run_dbt_models",
        bash_command=(
            DBT_CMD.format("run --select staging intermediate mart")
            + " && "
            + DBT_CMD.format("test")
        ),
        doc_md="Build all dbt models (staging → intermediate → mart) and run data-quality tests.",
    )

    # Task 5 — ML: run Isolation Forest to flag unusual price/volume movements; results saved to S3
    run_anomaly_detection = PythonOperator(
        task_id="run_anomaly_detection",
        python_callable=_run_anomaly_detection,
        doc_md="Run Isolation Forest on today's OHLCV data and write anomaly results to S3.",
    )

    # Task 6 — ML: train Prophet on 30 days of history and forecast next 5 closing prices per ticker
    run_price_prediction = PythonOperator(
        task_id="run_price_prediction",
        python_callable=_run_price_prediction,
        doc_md="Run Prophet model to predict next 5 days of closing prices and write forecasts to S3.",
    )

    # Task 7 — LLM: combine prices + anomalies + predictions into a GPT prompt; save insight to S3
    run_market_insights = PythonOperator(
        task_id="run_market_insights",
        python_callable=_run_market_insights,
        doc_md="Generate GPT-powered 3-sentence market insight summaries and write to S3.",
    )

    # Task 8 — Warehouse: sync all processed S3 data into Snowflake raw layer tables
    run_snowflake_sync = PythonOperator(
        task_id="run_snowflake_sync",
        python_callable=_run_snowflake_sync,
        doc_md="Sync stock prices, anomalies, predictions, and insights from S3 into Snowflake.",
    )

    (
        check_trading_day
        >> fetch_and_upload_to_s3
        >> load_to_postgres_staging
        >> run_dbt_models
        >> run_anomaly_detection
        >> run_price_prediction
        >> run_market_insights
        >> run_snowflake_sync
    )
