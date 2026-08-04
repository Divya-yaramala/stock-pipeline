import argparse
import datetime
import logging
import os

from ingestion.delta_versioner import optimize_delta_table
from ingestion.lakehouse_manager import get_layer_stats

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TICKERS = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"]
LAYERS = ["bronze", "silver", "gold"]


def run_lakehouse_cli(args: argparse.Namespace) -> None:
    bucket = os.getenv("AWS_BUCKET_NAME", "")
    tickers = [args.ticker] if args.ticker else TICKERS

    if args.optimize:
        print("\nRunning delta table optimization...")
        for ticker in tickers:
            result = optimize_delta_table(ticker, bucket)
            print(
                f"  {ticker}: {result['files_compacted']} files compacted, "
                f"{result['size_reduced_mb']:.4f} MB freed"
            )
        logger.info("Delta optimization complete for %d tickers", len(tickers))
        return

    date_str = args.date or datetime.date.today().strftime("%Y-%m-%d")
    date_path = date_str.replace("-", "/")
    layers = [args.layer] if args.layer and args.layer != "all" else LAYERS

    print(f"\nLakehouse Layer Stats — {date_str}")
    print("=" * 60)
    print(f"{'Layer':<10} {'Records':>10} {'Size (MB)':>12}")
    print("-" * 60)

    for layer in layers:
        stats = get_layer_stats(layer, bucket, date_path)
        record_count = stats["record_count"]
        size_mb = stats["size_mb"]
        status = "✅" if record_count >= 5 else "⚠️"
        print(f"{layer:<10} {record_count:>10} {size_mb:>11.4f}  {status}")

    print("=" * 60)
    logger.info("Lakehouse stats displayed for %s", date_str)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Data lakehouse management CLI")
    parser.add_argument("--ticker", help="Specific ticker to process (default: all 5)")
    parser.add_argument(
        "--layer",
        choices=["bronze", "silver", "gold", "all"],
        default="all",
        help="Layer to check (default: all)",
    )
    parser.add_argument("--date", help="Date in YYYY-MM-DD format (default: today)")
    parser.add_argument(
        "--optimize", action="store_true", help="Run delta table optimization"
    )
    parsed_args = parser.parse_args()
    run_lakehouse_cli(parsed_args)
