import argparse
import logging
import os

from ingestion.adaptive_model import run_adaptive_modeling

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def run_adaptive_cli(args: argparse.Namespace) -> None:
    bucket = os.getenv("AWS_BUCKET_NAME", "")
    ticker = args.ticker
    days = args.days

    try:
        import yfinance as yf

        data = yf.download(ticker, period=f"{days}d", progress=False)
        prices = [float(str(p)) for p in data["Close"].values]
        volumes = [float(str(v)) for v in data["Volume"].values]
    except Exception as exc:
        logger.warning("yfinance unavailable (%s), using synthetic data", exc)
        prices = [float(150 + i * 0.5) for i in range(days)]
        volumes = [float(1000000 + i * 10000) for i in range(days)]

    print(f"\nAdaptive Modeling — {ticker}")
    print("=" * 50)

    result = run_adaptive_modeling(ticker, prices, volumes, bucket if args.save else "")
    print(f"  Regime:     {result.get('regime', 'unknown')}")
    prediction_block = result.get("prediction", {})
    if isinstance(prediction_block, dict):
        print(f"  Model used: {prediction_block.get('model_used', 'unknown')}")
        pred_val = prediction_block.get("prediction", 0.0)
        print(f"  Prediction: {float(str(pred_val)):.4f}")
    print(f"  Features:   {result.get('feature_count', 0)} computed")
    print("=" * 50)

    logger.info("Adaptive pipeline complete for %s", ticker)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Adaptive pipeline CLI")
    parser.add_argument("--ticker", required=True, help="Ticker to process (e.g. AAPL)")
    parser.add_argument("--days", type=int, default=30, help="Days of price history (default: 30)")
    parser.add_argument(
        "--save",
        action="store_true",
        default=True,
        help="Save results to S3 (default: True)",
    )
    parsed_args = parser.parse_args()
    run_adaptive_cli(parsed_args)
