"""
Stock Price Data Pipeline DAG
==============================
Schedule  : Weekdays at 18:00 UTC (after US market close)
Flow      : incremental load → validation → Postgres staging → dbt → anomaly detection
            → price prediction → market insights → Snowflake → DLQ replay → monitoring report
Params    : full_refresh (bool, default False) — set True to force a full yfinance re-fetch
            instead of the default incremental gap-fill.
"""
import logging
import os
from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator, ShortCircuitOperator
from airflow.utils.trigger_rule import TriggerRule

log = logging.getLogger(__name__)


def _is_trading_day(**context) -> bool:
    """Skip the pipeline on weekends."""
    execution_date: datetime = context["logical_date"]
    if execution_date.weekday() >= 5:
        log.info("Execution date %s is a weekend — skipping run", execution_date.date())
        return False
    return True


def _check_resources(**context) -> bool:
    """Skip the pipeline if any system resource is at a critical level."""
    from resource_manager import should_run_pipeline

    ok = should_run_pipeline()
    if not ok:
        log.warning("Pipeline skipped — critical resource constraint detected")
    return ok


def _run_s3_optimization(**context) -> None:
    """Archive old raw data, purge stale monitoring files, and log cost estimate."""
    from s3_optimizer import run_s3_optimization

    run_s3_optimization()


def _fetch_and_upload_to_s3(**context) -> None:
    """Full-refresh: fetch OHLCV data for all tickers and upload JSON files to S3."""
    from fetch_stocks import run_pipeline

    run_pipeline()


def _run_incremental_load(**context) -> None:
    """Incremental load: detect data gaps and backfill missing dates from yfinance."""
    full_refresh = context["params"].get("full_refresh", False)
    if full_refresh:
        log.info("full_refresh=True — falling back to full yfinance fetch")
        from fetch_stocks import run_pipeline

        run_pipeline()
    else:
        from incremental_loader import run_incremental_load

        run_incremental_load()


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


def _run_validation(**context) -> None:
    """Validate today's stock data for all tickers before staging load."""
    from data_validator import run_validation

    run_validation()


def _run_dlq_replay(**context) -> None:
    """Replay any failed records from today's dead letter queue."""
    from dead_letter_queue import run_dlq_replay

    run_dlq_replay()


def _run_monitoring_report(**context) -> None:
    """Generate and save the daily pipeline monitoring report."""
    from pipeline_monitor import run_monitoring_report

    run_monitoring_report()


def _run_quality_reporting(**context) -> None:
    """Generate data quality report and check quality SLA."""
    from quality_reporter import run_quality_reporting

    run_quality_reporting()


def _generate_sla_report(**context) -> None:
    """Generate and save the daily SLA report for all pipeline steps."""
    import os
    from datetime import datetime as _dt

    from sla_monitor import generate_sla_report

    generate_sla_report(
        os.environ.get("AWS_BUCKET_NAME", ""),
        _dt.now().strftime("%Y/%m/%d"),
    )


def _run_report_generation(**context) -> None:
    """Generate HTML pipeline report from quality, SLA, and monitoring data."""
    from ingestion.report_generator import run_report_generation

    run_report_generation()


def _send_daily_report_email(**context) -> None:
    """Load today's metrics, render the HTML report, and email it."""
    import os
    from datetime import datetime as _dt

    from ingestion.email_notifier import send_daily_report_email
    from ingestion.report_generator import generate_html_report, load_daily_metrics

    bucket = os.environ.get("AWS_BUCKET_NAME", "")
    date = _dt.utcnow().strftime("%Y-%m-%d")
    metrics = load_daily_metrics(bucket, date)
    html = generate_html_report(metrics, date)
    send_daily_report_email(html, date)


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
    params={"full_refresh": False},
) as dag:

    # Task 1 — Gate: skip the entire DAG on weekends (no market data available)
    check_trading_day = ShortCircuitOperator(
        task_id="check_trading_day",
        python_callable=_is_trading_day,
        doc_md="Short-circuit on weekends so downstream tasks are skipped cleanly.",
    )

    # Task 1b — Resource gate: skip if CPU/memory/disk are at critical levels
    check_resources = ShortCircuitOperator(
        task_id="check_resources",
        python_callable=_check_resources,
        doc_md="Short-circuit if any system resource is critical to protect pipeline stability.",
    )

    # Task 2 — Incremental ingestion: fill data gaps or full-refresh when full_refresh=True
    run_incremental_load = PythonOperator(
        task_id="run_incremental_load",
        python_callable=_run_incremental_load,
        doc_md="Detect missing dates and backfill from yfinance (incremental by default).",
    )

    # Task 2b — Full-refresh fallback (not wired into main chain; trigger manually if needed)
    fetch_and_upload_to_s3 = PythonOperator(
        task_id="fetch_and_upload_to_s3",
        python_callable=_fetch_and_upload_to_s3,
        doc_md="Full-refresh: fetch OHLCV data via yfinance for all tickers.",
    )

    # Task 3 — Validation: check data quality before staging load; send failures to DLQ
    run_validation = PythonOperator(
        task_id="run_validation",
        python_callable=_run_validation,
        doc_md="Run 7 data-quality checks per ticker and save validation reports to S3.",
    )

    # Task 4 — Quality gate: score validation results and alert if quality SLA is missed
    run_quality_reporting = PythonOperator(
        task_id="run_quality_reporting",
        python_callable=_run_quality_reporting,
        trigger_rule=TriggerRule.ALL_DONE,
        doc_md="Calculate data quality score and check against 80% SLA threshold.",
    )

    # Task 5 — Staging: read today's JSON files from S3 and upsert into staging.stock_prices_raw
    load_to_postgres_staging = PythonOperator(
        task_id="load_to_postgres_staging",
        python_callable=_load_to_postgres_staging,
        doc_md="Load today's stock data from S3 into raw.stock_prices in Postgres.",
    )

    # Task 6 — Transformation: run dbt models (staging → intermediate → mart) and data-quality tests
    run_dbt_models = BashOperator(
        task_id="run_dbt_models",
        bash_command=(
            DBT_CMD.format("run --select staging intermediate mart")
            + " && "
            + DBT_CMD.format("test")
        ),
        doc_md="Build all dbt models (staging → intermediate → mart) and run data-quality tests.",
    )

    # Task 7 — ML: run Isolation Forest to flag unusual price/volume movements; results saved to S3
    run_anomaly_detection = PythonOperator(
        task_id="run_anomaly_detection",
        python_callable=_run_anomaly_detection,
        doc_md="Run Isolation Forest on today's OHLCV data and write anomaly results to S3.",
    )

    # Task 8 — ML: train Prophet on 30 days of history and forecast next 5 closing prices per ticker
    run_price_prediction = PythonOperator(
        task_id="run_price_prediction",
        python_callable=_run_price_prediction,
        doc_md="Run Prophet model to predict next 5 days of closing prices and write forecasts to S3.",
    )

    # Task 9 — LLM: combine prices + anomalies + predictions into a GPT prompt; save insight to S3
    run_market_insights = PythonOperator(
        task_id="run_market_insights",
        python_callable=_run_market_insights,
        doc_md="Generate GPT-powered 3-sentence market insight summaries and write to S3.",
    )

    # Task 10 — Warehouse: sync all processed S3 data into Snowflake raw layer tables
    run_snowflake_sync = PythonOperator(
        task_id="run_snowflake_sync",
        python_callable=_run_snowflake_sync,
        doc_md="Sync stock prices, anomalies, predictions, and insights from S3 into Snowflake.",
    )

    # Task 11 — Reliability: replay any DLQ records from failed upstream tasks
    run_dlq_replay = PythonOperator(
        task_id="run_dlq_replay",
        python_callable=_run_dlq_replay,
        trigger_rule=TriggerRule.ALL_DONE,
        doc_md="Replay failed pipeline records from the dead letter queue. Runs even if upstream tasks fail.",
    )

    # Task 12 — Observability: generate and persist the daily pipeline monitoring report
    run_monitoring_report = PythonOperator(
        task_id="run_monitoring_report",
        python_callable=_run_monitoring_report,
        trigger_rule=TriggerRule.ALL_DONE,
        doc_md="Generate daily pipeline metrics report and save to S3.",
    )

    # Task 13 — SLA: compare each step's actual duration against its threshold
    generate_sla_report = PythonOperator(
        task_id="generate_sla_report",
        python_callable=_generate_sla_report,
        trigger_rule=TriggerRule.ALL_DONE,
        doc_md="Generate SLA report and alert via Slack if any step exceeded its threshold.",
    )

    # Task 14 — Cost: archive old raw data, purge stale monitoring files, log cost estimate
    run_s3_optimization = PythonOperator(
        task_id="run_s3_optimization",
        python_callable=_run_s3_optimization,
        trigger_rule=TriggerRule.ALL_DONE,
        doc_md="Archive raw data older than 30 days and report estimated S3 monthly cost.",
    )

    # Task 15 — Reporting: generate HTML report combining quality, SLA, and monitoring metrics
    run_report_generation = PythonOperator(
        task_id="run_report_generation",
        python_callable=_run_report_generation,
        trigger_rule=TriggerRule.ALL_DONE,
        doc_md="Generate daily HTML pipeline report and save to S3.",
    )

    # Task 16 — Notification: email the daily report to the configured recipient
    send_daily_report_email = PythonOperator(
        task_id="send_daily_report_email",
        python_callable=_send_daily_report_email,
        trigger_rule=TriggerRule.ALL_DONE,
        doc_md="Send daily HTML pipeline report via email.",
    )

    (
        check_trading_day
        >> check_resources
        >> run_incremental_load
        >> run_validation
        >> run_quality_reporting
        >> load_to_postgres_staging
        >> run_dbt_models
        >> run_anomaly_detection
        >> run_price_prediction
        >> run_market_insights
        >> run_snowflake_sync
        >> run_dlq_replay
        >> run_monitoring_report
        >> generate_sla_report
        >> run_s3_optimization
        >> run_report_generation
        >> send_daily_report_email
    )
