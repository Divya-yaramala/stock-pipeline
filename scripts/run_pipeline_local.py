"""
Run the full stock-price pipeline locally without Airflow.
Usage: python scripts/run_pipeline_local.py
"""

import logging
import os
import sys
import time

# Ensure project root and ingestion/ are on the path
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)
sys.path.insert(0, os.path.join(_ROOT, "ingestion"))

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def _import_steps():
    from ingestion.anomaly_detector import run_anomaly_detection as detect
    from ingestion.fetch_stocks import run_pipeline as fetch
    from ingestion.market_insights import run_market_insights as insights
    from ingestion.price_predictor import run_price_prediction as predict
    from scripts.setup_postgres import setup_database as pg_setup

    return [
        ("fetch_stocks", fetch),
        ("anomaly_detection", detect),
        ("price_prediction", predict),
        ("market_insights", insights),
        ("postgres_setup", pg_setup),
    ]


def run_all_steps() -> None:
    """
    Execute every pipeline step in sequence.

    Steps run independently — a failure in one step does not abort the rest.
    Prints a formatted summary table with per-step status and wall-clock duration.
    """
    from ingestion.config_manager import validate_all_configs
    from ingestion.resource_manager import get_system_resources, should_run_pipeline
    from ingestion.s3_optimizer import generate_cost_report

    # Config validation — abort if required env vars are missing
    if not validate_all_configs():
        logger.error("Aborting — one or more required configs are invalid")
        sys.exit(1)

    # Resource check — abort if any resource is critical
    resources = get_system_resources()
    print()
    print(
        f"  Resource snapshot — CPU: {resources['cpu_percent']:.1f}%  "
        f"Memory: {resources['memory_percent']:.1f}%  "
        f"Disk: {resources['disk_usage_percent']:.1f}%"
    )
    if not should_run_pipeline():
        logger.error("Aborting — system resources are at a critical level")
        sys.exit(1)

    steps = _import_steps()
    results = []

    for name, fn in steps:
        logger.info("Starting step: %s", name)
        start = time.time()
        status = "SUCCESS"
        try:
            fn()
        except Exception as exc:
            status = "FAILED"
            logger.error("[%s] %s", name, exc)
        duration = round(time.time() - start, 2)
        results.append((name, status, duration))
        logger.info("Finished step: %s — %s (%.2fs)", name, status, duration)

    # Summary table
    col_w = (22, 10, 10)
    divider = "-" * (sum(col_w) + 6)
    print()
    print("=" * (sum(col_w) + 6))
    print(f"  {'Step':<{col_w[0]}} {'Status':<{col_w[1]}} {'Duration':>{col_w[2]}}")
    print(divider)
    for name, status, duration in results:
        print(f"  {name:<{col_w[0]}} {status:<{col_w[1]}} {duration:>{col_w[2] - 1}.2f}s")
    print("=" * (sum(col_w) + 6))

    failed = [r for r in results if r[1] == "FAILED"]
    if failed:
        logger.warning("%d step(s) failed: %s", len(failed), [r[0] for r in failed])
    else:
        logger.info("All steps completed successfully.")

    # Cost report at end
    bucket = os.environ.get("AWS_BUCKET_NAME", "")
    if bucket:
        try:
            cost_report = generate_cost_report(bucket)
            print()
            print(
                f"  S3 cost estimate — {cost_report['storage_gb']:.4f} GB  "
                f"≈ ${cost_report['estimated_monthly_cost_usd']:.4f}/month"
            )
        except Exception as exc:
            logger.warning("Could not generate cost report: %s", exc)


if __name__ == "__main__":
    run_all_steps()
