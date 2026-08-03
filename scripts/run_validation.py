import argparse
import datetime
import json
import logging
import os
import sys

import boto3

from ingestion.pipeline_validator import run_validation_suite, save_validation_report

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TICKERS = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"]


def _load_records_from_s3(bucket: str, ticker: str, date: str) -> list:
    try:
        s3 = boto3.client("s3")
        parts = date.split("-")
        year, month, day = parts[0], parts[1], parts[2]
        key = f"processed/{year}/{month}/{day}/{ticker}.json"
        resp = s3.get_object(Bucket=bucket, Key=key)
        data = json.loads(resp["Body"].read().decode())
        if isinstance(data, list):
            return data
        return [data]
    except Exception as e:
        logger.warning("Could not load records for %s on %s: %s", ticker, date, e)
        return []


def run_validation_cli(args: argparse.Namespace) -> None:
    bucket = os.getenv("AWS_BUCKET_NAME", "")
    date = args.date or datetime.date.today().isoformat()
    tickers = [args.ticker] if args.ticker else TICKERS

    print(f"\nValidation Report — {date}")
    print("=" * 60)

    any_failure = False
    for ticker in tickers:
        records = _load_records_from_s3(bucket, ticker, date)
        if not records:
            print(f"{ticker}: no records found for {date}")
            continue

        result = run_validation_suite(records, ticker)
        pass_rate = result["pass_rate_pct"]
        status = "PASS" if pass_rate == 100.0 else "WARN" if pass_rate >= 80.0 else "FAIL"

        print(f"\n{ticker} [{status}] — pass rate: {pass_rate:.1f}%")
        for r in result["results"]:
            icon = "✅" if r["passed"] else "❌"
            rule_id = r["rule_id"]
            violations = r.get("violations", r.get("issues", []))
            if not r["passed"]:
                print(f"  {icon} {rule_id}: {violations}")
                any_failure = True
            else:
                print(f"  {icon} {rule_id}: passed")

        if args.save and bucket:
            save_validation_report(result, ticker, bucket, date)

    print("\n" + "=" * 60)
    if args.strict and any_failure:
        print("STRICT mode: validation failures detected — exiting with code 1")
        sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run pipeline validation suite")
    parser.add_argument("--ticker", help="Specific ticker to validate (default: all 5)")
    parser.add_argument("--date", help="Date in YYYY-MM-DD format (default: today)")
    parser.add_argument(
        "--strict", action="store_true", help="Exit with code 1 if pass_rate < 100%%"
    )
    parser.add_argument(
        "--save", action="store_true", default=True, help="Save report to S3 (default: True)"
    )
    parsed_args = parser.parse_args()
    run_validation_cli(parsed_args)
