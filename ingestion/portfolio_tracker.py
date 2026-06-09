import json
import logging
import os
from datetime import datetime, timedelta

import boto3
import pandas as pd

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

_DEFAULT_PORTFOLIO = {"AAPL": 10, "MSFT": 5, "GOOGL": 3, "AMZN": 2, "TSLA": 8}


def load_portfolio(bucket: str) -> dict:
    """
    Load portfolio configuration from S3.

    Args:
        bucket: S3 bucket name.

    Returns:
        Dict of ticker → shares, or the default portfolio if not found.
    """
    s3 = boto3.client("s3")
    try:
        response = s3.get_object(Bucket=bucket, Key="portfolio/config.json")
        portfolio = json.loads(response["Body"].read().decode("utf-8"))
        logger.info("Loaded portfolio with %d tickers from S3", len(portfolio))
        return portfolio
    except Exception as e:
        logger.warning("Could not load portfolio config — using default: %s", e)
        return dict(_DEFAULT_PORTFOLIO)


def calculate_portfolio_value(portfolio: dict, prices: dict) -> dict:
    """
    Calculate current portfolio value, per-ticker weights, and top holding.

    Args:
        portfolio: Dict of ticker → number of shares.
        prices: Dict of ticker → current close price.

    Returns:
        Dict with total_value, individual_values, weights, and top_holding.
    """
    individual_values = {
        ticker: shares * prices.get(ticker, 0.0) for ticker, shares in portfolio.items()
    }
    total_value = sum(individual_values.values())

    weights = {
        ticker: round((value / total_value * 100) if total_value > 0 else 0.0, 2)
        for ticker, value in individual_values.items()
    }
    top_holding = (
        max(individual_values, key=lambda t: individual_values[t]) if individual_values else None
    )

    logger.info("Portfolio value calculated: $%.2f, top holding: %s", total_value, top_holding)
    return {
        "total_value": round(total_value, 2),
        "individual_values": individual_values,
        "weights": weights,
        "top_holding": top_holding,
    }


def calculate_portfolio_returns(
    portfolio: dict,
    current_prices: dict,
    previous_prices: dict,
) -> dict:
    """
    Calculate daily return per ticker and overall portfolio daily return.

    Args:
        portfolio: Dict of ticker → number of shares.
        current_prices: Dict of ticker → today's close price.
        previous_prices: Dict of ticker → yesterday's close price.

    Returns:
        Dict with ticker_returns and daily_return_pct.
    """
    ticker_returns = {}
    weighted_return = 0.0
    total_prev_value = 0.0

    for ticker, shares in portfolio.items():
        current = current_prices.get(ticker, 0.0)
        previous = previous_prices.get(ticker, 0.0)
        if previous > 0:
            pct = (current - previous) / previous * 100
            ticker_returns[ticker] = round(pct, 4)
            prev_value = shares * previous
            total_prev_value += prev_value
            weighted_return += pct * prev_value
        else:
            ticker_returns[ticker] = 0.0

    daily_return_pct = round(weighted_return / total_prev_value, 4) if total_prev_value > 0 else 0.0
    return {"ticker_returns": ticker_returns, "daily_return_pct": daily_return_pct}


def save_portfolio_snapshot(metrics: dict, bucket: str, date: str) -> bool:
    """
    Save a portfolio metrics snapshot to S3.

    Args:
        metrics: Portfolio metrics dict from calculate_portfolio_value.
        bucket: S3 bucket name.
        date: Date string in YYYY-MM-DD format.

    Returns:
        True on success, False on failure.
    """
    date_path = date.replace("-", "/")
    key = f"portfolio/snapshots/{date_path}/snapshot.json"
    try:
        s3 = boto3.client("s3")
        s3.put_object(
            Bucket=bucket,
            Key=key,
            Body=json.dumps(metrics),
            ContentType="application/json",
        )
        logger.info("Portfolio snapshot saved to s3://%s/%s", bucket, key)
        return True
    except Exception as e:
        logger.error("Failed to save portfolio snapshot: %s", e)
        return False


def run_portfolio_tracking() -> None:
    """Load portfolio, fetch prices, calculate value and returns, save snapshot."""
    bucket = os.getenv("AWS_BUCKET_NAME", "")
    today = datetime.utcnow()
    yesterday = today - timedelta(days=1)
    today_path = today.strftime("%Y/%m/%d")
    yesterday_path = yesterday.strftime("%Y/%m/%d")

    portfolio = load_portfolio(bucket)
    s3 = boto3.client("s3")
    current_prices: dict = {}
    previous_prices: dict = {}

    for ticker in portfolio:
        for date_path, price_store in [
            (today_path, current_prices),
            (yesterday_path, previous_prices),
        ]:
            try:
                key = f"raw/stocks/{date_path}/{ticker}.json"
                response = s3.get_object(Bucket=bucket, Key=key)
                data = json.loads(response["Body"].read().decode("utf-8"))
                df = pd.DataFrame(data)
                df.columns = [col.lower() for col in df.columns]
                price_store[ticker] = float(df["close"].iloc[0])
            except Exception as e:
                logger.warning("Could not load price for %s on %s: %s", ticker, date_path, e)

    metrics = calculate_portfolio_value(portfolio, current_prices)
    returns = calculate_portfolio_returns(portfolio, current_prices, previous_prices)
    metrics.update(returns)

    date = today.strftime("%Y-%m-%d")
    save_portfolio_snapshot(metrics, bucket, date)
    logger.info(
        "Portfolio tracking complete: total=$%.2f, daily_return=%.2f%%",
        metrics.get("total_value", 0),
        returns.get("daily_return_pct", 0),
    )


if __name__ == "__main__":
    run_portfolio_tracking()
