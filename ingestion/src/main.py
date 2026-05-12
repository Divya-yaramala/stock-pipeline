"""CLI entry-point: fetch → S3 → Postgres."""
import logging
import sys
from datetime import date

import config
from fetch_stocks import fetch_stock_data
from postgres_utils import load_dataframe_to_postgres
from s3_utils import upload_dataframe_to_s3

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s — %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)


def run(target_date: date | None = None) -> None:
    logger.info("=== Stock Price Pipeline starting ===")

    df = fetch_stock_data(config.STOCK_SYMBOLS, target_date=target_date)
    if df.empty:
        logger.warning("No data fetched — pipeline complete (no-op)")
        return

    s3_key = ""
    if config.S3_BUCKET:
        s3_key = upload_dataframe_to_s3(
            df,
            bucket=config.S3_BUCKET,
            prefix=config.S3_PREFIX,
            target_date=target_date or df["date"].max(),
        )
    else:
        logger.warning("S3_BUCKET not set — skipping S3 upload")

    load_dataframe_to_postgres(df, s3_key=s3_key)
    logger.info("=== Pipeline complete ===")


if __name__ == "__main__":
    run()
