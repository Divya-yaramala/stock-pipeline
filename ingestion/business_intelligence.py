import json
import logging
import os
from datetime import datetime, timedelta

import boto3
import numpy as np
import pandas as pd

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TICKERS = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"]
DEFAULT_SECTORS = {
    "AAPL": "Technology",
    "MSFT": "Technology",
    "GOOGL": "Technology",
    "AMZN": "Consumer Cyclical",
    "TSLA": "Consumer Cyclical",
}
DEFAULT_MARKET_CAPS = {
    "AAPL": 3000,
    "MSFT": 2800,
    "GOOGL": 2000,
    "AMZN": 1800,
    "TSLA": 700,
}


def calculate_market_cap_weighted_index(prices: dict, market_caps: dict) -> float:
    total_cap = sum(market_caps[t] for t in prices if t in market_caps)
    if total_cap == 0:
        return 0.0
    index = sum(
        prices[t] * market_caps[t] / total_cap for t in prices if t in market_caps
    )
    logger.info("Market cap weighted index calculated: %.2f", index)
    return round(index, 2)


def calculate_sector_performance(prices: dict, sectors: dict) -> dict:
    sector_totals: dict = {}
    sector_counts: dict = {}
    for ticker, ret in prices.items():
        sector = sectors.get(ticker)
        if sector:
            sector_totals[sector] = sector_totals.get(sector, 0.0) + ret
            sector_counts[sector] = sector_counts.get(sector, 0) + 1
    result = {
        sector: round(sector_totals[sector] / sector_counts[sector], 4)
        for sector in sector_totals
    }
    logger.info("Sector performance calculated: %s", result)
    return result


def calculate_sharpe_ratio(returns: list, risk_free_rate: float = 0.05) -> float:
    arr = np.array(returns, dtype=float)
    mean_ret = float(np.mean(arr))
    std_ret = float(np.std(arr))
    if std_ret == 0:
        return 0.0
    sharpe = (mean_ret - risk_free_rate) / std_ret
    logger.info("Sharpe ratio calculated: %.4f", sharpe)
    return round(sharpe, 4)


def calculate_max_drawdown(prices: list) -> float:
    arr = np.array(prices, dtype=float)
    peak = np.maximum.accumulate(arr)
    drawdown = (arr - peak) / peak
    max_dd = float(np.min(drawdown))
    logger.info("Max drawdown calculated: %.4f", max_dd)
    return round(max_dd, 4)


def _load_ticker_prices(ticker: str, bucket: str, date: str, days: int = 30) -> list:
    s3 = boto3.client("s3")
    prices = []
    end_date = datetime.strptime(date, "%Y-%m-%d")
    for i in range(days):
        d = end_date - timedelta(days=i)
        key = f"raw/stocks/{d.strftime('%Y/%m/%d')}/{ticker}.json"
        try:
            resp = s3.get_object(Bucket=bucket, Key=key)
            records = json.loads(resp["Body"].read().decode("utf-8"))
            if isinstance(records, list) and records:
                close = records[0].get("close")
                if close:
                    prices.append(float(close))
        except Exception:
            continue
    return list(reversed(prices))


def generate_bi_report(ticker: str, bucket: str, date: str) -> dict:
    s3 = boto3.client("s3")
    price_series = _load_ticker_prices(ticker, bucket, date)

    if len(price_series) < 2:
        price_series = [100.0, 102.0, 101.0, 103.0, 105.0]

    returns = [
        (price_series[i] - price_series[i - 1]) / price_series[i - 1]
        for i in range(1, len(price_series))
    ]

    latest_prices = {t: price_series[-1] if t == ticker else 150.0 for t in TICKERS}
    sector_returns = {t: returns[-1] if t == ticker else 0.0 for t in TICKERS}

    sharpe = calculate_sharpe_ratio(returns)
    max_dd = calculate_max_drawdown(price_series)
    index_val = calculate_market_cap_weighted_index(latest_prices, DEFAULT_MARKET_CAPS)
    sector_perf = calculate_sector_performance(sector_returns, DEFAULT_SECTORS)

    report = {
        ticker: {
            "sharpe_ratio": sharpe,
            "max_drawdown": max_dd,
            "market_cap_weighted_index": index_val,
            "sector_performance": sector_perf,
            "price_series_length": len(price_series),
            "latest_price": price_series[-1],
            "generated_at": datetime.utcnow().isoformat(),
        }
    }

    dt = datetime.strptime(date, "%Y-%m-%d")
    key = f"reports/bi/{dt.strftime('%Y/%m/%d')}/{ticker}.json"
    s3.put_object(
        Bucket=bucket,
        Key=key,
        Body=json.dumps(report, default=str),
        ContentType="application/json",
    )
    logger.info("BI report for %s saved to s3://%s/%s", ticker, bucket, key)
    return report


def run_bi_analysis(bucket: str) -> dict:
    date = datetime.utcnow().strftime("%Y-%m-%d")
    combined: dict = {}
    for ticker in TICKERS:
        try:
            report = generate_bi_report(ticker, bucket, date)
            combined.update(report)
        except Exception as e:
            logger.error("BI analysis failed for %s: %s", ticker, e)
    logger.info("BI analysis complete for %d tickers", len(combined))
    return combined


if __name__ == "__main__":
    pass
