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


if __name__ == "__main__":
    run_all_steps()
