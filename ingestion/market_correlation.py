import json
import logging
import os
from datetime import datetime, timedelta

import boto3
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

TICKERS = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"]


def load_price_series(tickers: list, bucket: str, days: int = 30) -> pd.DataFrame:
    s3 = boto3.client("s3")
    today = datetime.utcnow().date()
    data: dict = {ticker: {} for ticker in tickers}

    for i in range(days):
        date = today - timedelta(days=i)
        date_str = date.strftime("%Y/%m/%d")
        for ticker in tickers:
            key = f"raw/stocks/{date_str}/{ticker}.json"
            try:
                response = s3.get_object(Bucket=bucket, Key=key)
                records = json.loads(response["Body"].read().decode("utf-8"))
                if isinstance(records, list) and records:
                    close = records[0].get("close")
                elif isinstance(records, dict):
                    close = records.get("close")
                else:
                    close = None
                if close is not None:
                    data[ticker][str(date)] = float(close)
            except Exception:
                pass

    df = pd.DataFrame(data)
    df.index = pd.to_datetime(df.index)
    df.sort_index(inplace=True)
    return df


def calculate_correlation_matrix(df: pd.DataFrame) -> pd.DataFrame:
    corr = df.corr(method="pearson")

    valid = corr.values[~np.isnan(corr.values)]
    if len(valid) > len(corr.columns):
        upper = corr.where(np.triu(np.ones(corr.shape), k=1).astype(bool))
        max_pair = upper.stack().idxmax()
        min_pair = upper.stack().idxmin()
        logger.info("Highest correlation: %s & %s = %.4f", max_pair[0], max_pair[1], upper.loc[max_pair])
        logger.info("Lowest correlation: %s & %s = %.4f", min_pair[0], min_pair[1], upper.loc[min_pair])

    return corr


def find_highly_correlated(corr_matrix: pd.DataFrame, threshold: float = 0.8) -> list:
    pairs = []
    tickers = list(corr_matrix.columns)
    for i in range(len(tickers)):
        for j in range(i + 1, len(tickers)):
            val = corr_matrix.iloc[i, j]
            if not np.isnan(val) and abs(val) >= threshold:
                pairs.append(
                    {
                        "ticker1": tickers[i],
                        "ticker2": tickers[j],
                        "correlation": round(float(val), 4),
                    }
                )
    pairs.sort(key=lambda x: abs(x["correlation"]), reverse=True)
    return pairs


def calculate_beta(ticker: str, market_ticker: str, prices: pd.DataFrame) -> float:
    if ticker not in prices.columns or market_ticker not in prices.columns:
        raise ValueError(f"Tickers {ticker} or {market_ticker} not found in price data")

    returns = prices[[ticker, market_ticker]].pct_change().dropna()
    if len(returns) < 2:
        raise ValueError("Not enough data points to calculate beta")

    cov = np.cov(returns[ticker], returns[market_ticker])
    market_var = cov[1, 1]
    if market_var == 0:
        raise ValueError("Market variance is zero — cannot compute beta")
    return float(cov[0, 1] / market_var)


def run_correlation_analysis(bucket: str = "") -> dict:
    if not bucket:
        bucket = os.getenv("AWS_BUCKET_NAME", "")

    date = datetime.utcnow().strftime("%Y-%m-%d")
    df = load_price_series(TICKERS, bucket, days=30)

    corr_matrix = calculate_correlation_matrix(df)
    highly_correlated = find_highly_correlated(corr_matrix, threshold=0.8)

    betas = {}
    market_ticker = "MSFT"
    for ticker in TICKERS:
        if ticker == market_ticker:
            continue
        try:
            betas[ticker] = round(calculate_beta(ticker, market_ticker, df), 4)
        except Exception as e:
            logger.warning("Could not compute beta for %s: %s", ticker, e)
            betas[ticker] = None

    results = {
        "date": date,
        "correlation_matrix": {
            col: {row: round(float(v), 4) if not np.isnan(v) else None for row, v in corr_matrix[col].items()}
            for col in corr_matrix.columns
        },
        "highly_correlated_pairs": highly_correlated,
        "betas_vs_msft": betas,
    }

    if bucket:
        try:
            s3 = boto3.client("s3")
            path_date = date.replace("-", "/")
            key = f"processed/correlation/{path_date}/correlation.json"
            s3.put_object(
                Bucket=bucket,
                Key=key,
                Body=json.dumps(results, indent=2).encode("utf-8"),
                ContentType="application/json",
            )
            logger.info("Saved correlation analysis to s3://%s/%s", bucket, key)
        except Exception as e:
            logger.error("Failed to save correlation analysis: %s", e)

    logger.info(
        "Correlation analysis complete: %d highly-correlated pairs found",
        len(highly_correlated),
    )
    return results


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    _bucket = os.getenv("AWS_BUCKET_NAME", "")
    pass
