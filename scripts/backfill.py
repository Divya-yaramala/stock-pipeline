import argparse
import logging
import os
from datetime import datetime

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

TICKERS = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"]


def validate_dates(start_date: str, end_date: str) -> bool:
    """Return True if start_date < end_date and start_date is not in the future."""
    try:
        start = datetime.strptime(start_date, "%Y-%m-%d").date()
        end = datetime.strptime(end_date, "%Y-%m-%d").date()
    except ValueError as e:
        logger.error("Invalid date format: %s", e)
        return False

    today = datetime.now().date()
    if start >= end:
        logger.error("start_date %s must be before end_date %s", start_date, end_date)
        return False
    if start > today:
        logger.error("start_date %s is in the future", start_date)
        return False
    return True


def run_backfill(ticker: str, start_date: str, end_date: str, dry_run: bool) -> None:
    """Backfill one ticker for the given date range, or log intent if dry_run=True."""
    if dry_run:
        logger.info("[DRY RUN] Would backfill %s from %s to %s", ticker, start_date, end_date)
        return

    from ingestion import incremental_loader
    from scripts.setup_postgres import get_connection

    bucket = os.environ.get("AWS_BUCKET_NAME", "")
    conn = get_connection()
    try:
        rows = incremental_loader.backfill_ticker(ticker, conn, bucket, start_date, end_date)
        logger.info("Backfill complete for %s: %d rows loaded", ticker, rows)
    finally:
        conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Backfill historical stock data into the pipeline")
    parser.add_argument("--ticker", help="Specific ticker to backfill (default: all 5)")
    parser.add_argument("--start-date", required=True, help="Start date YYYY-MM-DD")
    parser.add_argument(
        "--end-date",
        default=datetime.now().strftime("%Y-%m-%d"),
        help="End date YYYY-MM-DD (default: today)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview what would be loaded without making changes",
    )
    args = parser.parse_args()

    if not validate_dates(args.start_date, args.end_date):
        raise SystemExit(1)

    tickers = [args.ticker] if args.ticker else TICKERS

    for ticker in tickers:
        run_backfill(ticker, args.start_date, args.end_date, dry_run=args.dry_run)

    logger.info(
        "Backfill %s for %d ticker(s) from %s to %s",
        "preview complete" if args.dry_run else "complete",
        len(tickers),
        args.start_date,
        args.end_date,
    )


if __name__ == "__main__":
    main()
