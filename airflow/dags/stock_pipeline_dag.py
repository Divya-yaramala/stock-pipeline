"""
Stock Price Data Pipeline DAG
==============================
Schedule  : Weekdays at 18:00 UTC (after US market close)
Flow      : yfinance → S3 raw layer → PostgreSQL raw → dbt transforms
"""
import logging
import os
from datetime import date, datetime, timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator, ShortCircuitOperator

log = logging.getLogger(__name__)

# ── Helpers imported from /opt/ingestion (mounted via docker-compose) ─────────

def _is_trading_day(**context) -> bool:
    """Skip the pipeline on weekends (simple guard; does not account for holidays)."""
    execution_date: datetime = context["logical_date"]
    if execution_date.weekday() >= 5:
        log.info("Execution date %s is a weekend — skipping run", execution_date.date())
        return False
    return True


def _ingest_and_upload(**context) -> str:
    """Fetch stock data for the execution date and upload to S3."""
    from fetch_stocks import fetch_stock_data
    from s3_utils import upload_dataframe_to_s3

    execution_date: datetime = context["logical_date"]
    target_date = execution_date.date()

    symbols = os.environ["STOCK_SYMBOLS"].split(",")
    df = fetch_stock_data(symbols, target_date=target_date)

    if df.empty:
        log.warning("No data returned for %s — DAG will continue but load will no-op", target_date)
        return ""

    s3_key = upload_dataframe_to_s3(
        df,
        bucket=os.environ["S3_BUCKET"],
        prefix=os.environ.get("S3_PREFIX", "raw/stocks"),
        target_date=target_date,
    )
    # Push S3 key for downstream task
    context["ti"].xcom_push(key="s3_key", value=s3_key)
    log.info("Ingestion complete. S3 key: %s", s3_key)
    return s3_key


def _load_raw_to_postgres(**context) -> int:
    """Download today's Parquet from S3 and upsert into raw.stock_prices."""
    from postgres_utils import load_from_s3_to_postgres

    s3_key: str = context["ti"].xcom_pull(task_ids="ingest_and_upload_s3", key="s3_key") or ""
    if not s3_key:
        log.warning("No S3 key received — skipping Postgres load")
        return 0

    execution_date: datetime = context["logical_date"]
    rows = load_from_s3_to_postgres(
        bucket=os.environ["S3_BUCKET"],
        prefix=os.environ.get("S3_PREFIX", "raw/stocks"),
        target_date=execution_date.date(),
    )
    log.info("Loaded %d row(s) into raw.stock_prices", rows)
    return rows


# ── DAG definition ─────────────────────────────────────────────────────────────

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
    description="Daily stock price ingestion → S3 → PostgreSQL → dbt transforms",
    schedule="0 18 * * 1-5",  # 18:00 UTC, Mon–Fri
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

    ingest_and_upload_s3 = PythonOperator(
        task_id="ingest_and_upload_s3",
        python_callable=_ingest_and_upload,
        doc_md="Fetch OHLCV data via yfinance and upload Parquet to S3.",
    )

    load_raw_to_postgres = PythonOperator(
        task_id="load_raw_to_postgres",
        python_callable=_load_raw_to_postgres,
        doc_md="Download Parquet from S3 and upsert into raw.stock_prices.",
    )

    dbt_run_staging = BashOperator(
        task_id="dbt_run_staging",
        bash_command=DBT_CMD.format("run --select staging"),
        doc_md="Build staging models (stg_stock_prices).",
    )

    dbt_run_intermediate = BashOperator(
        task_id="dbt_run_intermediate",
        bash_command=DBT_CMD.format("run --select intermediate"),
        doc_md="Build intermediate models (int_stock_daily_metrics).",
    )

    dbt_run_mart = BashOperator(
        task_id="dbt_run_mart",
        bash_command=DBT_CMD.format("run --select mart"),
        doc_md="Build mart models (mart_stock_summary).",
    )

    dbt_test = BashOperator(
        task_id="dbt_test",
        bash_command=DBT_CMD.format("test"),
        doc_md="Run all dbt data-quality tests.",
    )

    # ── Task dependency chain ─────────────────────────────────────────────────
    (
        check_trading_day
        >> ingest_and_upload_s3
        >> load_raw_to_postgres
        >> dbt_run_staging
        >> dbt_run_intermediate
        >> dbt_run_mart
        >> dbt_test
    )
