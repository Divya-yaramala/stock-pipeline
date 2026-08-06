import argparse
import datetime
import logging
import os

from ingestion.distributed_tracer import run_pipeline_with_tracing
from ingestion.observability_dashboard import (
    get_service_level_objectives,
    run_observability_check,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def run_observability_cli(args: argparse.Namespace) -> None:
    bucket = os.getenv("AWS_BUCKET_NAME", "")
    date = args.date or datetime.date.today().strftime("%Y-%m-%d")

    if args.slo:
        print("\nService Level Objectives")
        print("=" * 50)
        slos = get_service_level_objectives()
        for slo in slos:
            print(f"  {slo['name']:<30} target={slo['target']} {slo['unit']}")
        print("=" * 50)
        logger.info("SLO definitions displayed")
        return

    print(f"\nObservability Report — {date}")
    print("=" * 60)

    result = run_observability_check(bucket)
    signals = result.get("golden_signals", {})
    slo = result.get("slo_compliance", {})

    print("\n Golden Signals:")
    print(f"  {'Latency':<20} {float(str(signals.get('latency', 0))):.1f} min")
    print(f"  {'Traffic':<20} {float(str(signals.get('traffic', 0))):.1f} records/hr")
    print(f"  {'Errors':<20} {float(str(signals.get('errors', 0))):.2f}%")
    print(f"  {'Saturation':<20} {float(str(signals.get('saturation', 0))):.1f}%")

    print(f"\n SLO Compliance: {slo.get('compliant')}/{slo.get('total')}")
    for violation in slo.get("violations", []):
        print(f"  FAIL: {violation}")

    if args.trace:
        print("\n Running distributed trace...")
        tickers = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"]
        for ticker in tickers:
            trace_id = run_pipeline_with_tracing(ticker, bucket)
            print(f"  {ticker}: trace_id={trace_id}")

    print("=" * 60)
    logger.info("Observability check complete for %s", date)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Observability CLI")
    parser.add_argument("--date", help="Date to check in YYYY-MM-DD format (default: today)")
    parser.add_argument(
        "--trace",
        action="store_true",
        help="Also run distributed trace for all tickers",
    )
    parser.add_argument(
        "--slo",
        action="store_true",
        help="Show SLO definitions only",
    )
    parsed_args = parser.parse_args()
    run_observability_cli(parsed_args)
