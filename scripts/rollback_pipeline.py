import argparse
import logging
import os
from datetime import datetime

from ingestion.config_manager import load_pipeline_config
from ingestion.data_versioner import rollback_to_version

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

VALID_STEPS = ["fetch", "anomaly", "prediction", "insights"]


def validate_rollback_args(args: argparse.Namespace) -> bool:
    """
    Validate command-line arguments for a rollback operation.

    Args:
        args: Parsed argparse namespace.

    Returns:
        True if all arguments are valid, False otherwise.
    """
    pipeline_cfg = load_pipeline_config()
    if args.ticker.upper() not in [t.upper() for t in pipeline_cfg.tickers]:
        logger.error("Invalid ticker: %s. Must be one of %s", args.ticker, pipeline_cfg.tickers)
        return False
    if args.step not in VALID_STEPS:
        logger.error("Invalid step: %s. Must be one of %s", args.step, VALID_STEPS)
        return False
    if len(args.version_id) != 8:
        logger.error(
            "Invalid version_id: %s. Must be exactly 8 characters.", args.version_id
        )
        return False
    return True


def execute_rollback(
    ticker: str,
    step: str,
    version_id: str,
    date: str,
    dry_run: bool,
) -> None:
    """
    Execute or preview a pipeline step rollback.

    Args:
        ticker: Stock ticker symbol.
        step: Pipeline step to roll back.
        version_id: 8-character version ID to restore.
        date: Date string in YYYY-MM-DD format.
        dry_run: If True, log the rollback plan without executing.
    """
    bucket = os.getenv("AWS_S3_BUCKET", "")

    if dry_run:
        logger.info(
            "[DRY RUN] Would rollback %s/%s to version %s for date %s",
            ticker,
            step,
            version_id,
            date,
        )
        return

    payload = rollback_to_version(ticker, step, version_id, bucket, date)
    logger.info(
        "Rollback complete: %s/%s restored to version %s (created_at=%s)",
        ticker,
        step,
        version_id,
        payload.get("created_at", "unknown"),
    )


def main() -> None:
    """Parse arguments and run the pipeline rollback."""
    parser = argparse.ArgumentParser(description="Roll back a pipeline step to a previous version")
    parser.add_argument("--ticker", required=True, help="Ticker symbol to roll back")
    parser.add_argument(
        "--step",
        required=True,
        choices=VALID_STEPS,
        help="Pipeline step to roll back",
    )
    parser.add_argument("--version-id", required=True, help="8-character version ID to restore")
    parser.add_argument(
        "--date",
        default=datetime.utcnow().strftime("%Y-%m-%d"),
        help="Date in YYYY-MM-DD format (default: today)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview rollback without executing",
    )
    args = parser.parse_args()

    if not validate_rollback_args(args):
        logger.error("Rollback aborted due to invalid arguments.")
        return

    execute_rollback(
        ticker=args.ticker.upper(),
        step=args.step,
        version_id=args.version_id,
        date=args.date,
        dry_run=args.dry_run,
    )
    logger.info(
        "Summary: rollback of %s/%s to version %s — %s",
        args.ticker.upper(),
        args.step,
        args.version_id,
        "DRY RUN (no changes made)" if args.dry_run else "SUCCESS",
    )


if __name__ == "__main__":
    main()
