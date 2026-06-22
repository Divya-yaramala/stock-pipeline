import json
import logging
import os
from datetime import datetime, timezone

import boto3

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")
TICKERS = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"]

QUALITY_DIMENSIONS = [
    {"dimension": "completeness", "weight": 0.25, "description": "All required data present"},
    {"dimension": "accuracy", "weight": 0.25, "description": "Data values are correct"},
    {
        "dimension": "consistency",
        "weight": 0.20,
        "description": "Data is consistent across sources",
    },
    {"dimension": "timeliness", "weight": 0.15, "description": "Data is up to date"},
    {"dimension": "validity", "weight": 0.15, "description": "Data conforms to rules"},
]

_DATA_PATHS = [
    "raw/stocks/{date}/{ticker}.json",
    "processed/anomalies/{date}/{ticker}.json",
    "processed/predictions/{date}/{ticker}.json",
    "processed/insights/{date}/{ticker}.json",
    "processed/validation/{date}/{ticker}.json",
]


def score_completeness(bucket: str, ticker: str, date: str) -> float:
    dt = datetime.strptime(date, "%Y-%m-%d")
    date_path = dt.strftime("%Y/%m/%d")
    s3 = boto3.client("s3", region_name=AWS_REGION)
    found = 0
    for path_template in _DATA_PATHS:
        key = path_template.format(date=date_path, ticker=ticker)
        try:
            s3.head_object(Bucket=bucket, Key=key)
            found += 1
        except Exception:
            pass
    score = round((found / len(_DATA_PATHS)) * 100, 1)
    logger.info("Completeness score for %s: %.1f", ticker, score)
    return score


def score_accuracy(bucket: str, ticker: str, date: str) -> float:
    dt = datetime.strptime(date, "%Y-%m-%d")
    key = f"raw/stocks/{dt.strftime('%Y/%m/%d')}/{ticker}.json"
    try:
        s3 = boto3.client("s3", region_name=AWS_REGION)
        response = s3.get_object(Bucket=bucket, Key=key)
        data = json.loads(response["Body"].read().decode("utf-8"))
        records = data if isinstance(data, list) else [data]
        if not records:
            return 0.0
        checks_passed = 0
        total_checks = 0
        for record in records:
            price = record.get("close", 0)
            volume = record.get("volume", 0)
            high = record.get("high", 0)
            low = record.get("low", 0)
            total_checks += 3
            if price > 0:
                checks_passed += 1
            if volume > 0:
                checks_passed += 1
            if high >= low:
                checks_passed += 1
        score = round((checks_passed / total_checks) * 100, 1) if total_checks else 0.0
        logger.info("Accuracy score for %s: %.1f", ticker, score)
        return score
    except Exception as exc:
        logger.warning("Could not score accuracy for %s: %s", ticker, exc)
        return 0.0


def score_consistency(bucket: str, ticker: str, date: str) -> float:
    dt = datetime.strptime(date, "%Y-%m-%d")
    date_path = dt.strftime("%Y/%m/%d")
    s3 = boto3.client("s3", region_name=AWS_REGION)
    consistent = 0
    checked = 0
    for path_template in _DATA_PATHS:
        key = path_template.format(date=date_path, ticker=ticker)
        try:
            response = s3.get_object(Bucket=bucket, Key=key)
            data = json.loads(response["Body"].read().decode("utf-8"))
            record = data[0] if isinstance(data, list) and data else data
            checked += 1
            if str(record.get("ticker", "")).upper() == ticker.upper():
                consistent += 1
        except Exception:
            pass
    score = round((consistent / checked) * 100, 1) if checked else 100.0
    logger.info("Consistency score for %s: %.1f", ticker, score)
    return score


def score_timeliness(bucket: str, ticker: str) -> float:
    date_str = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    key = f"raw/stocks/{dt.strftime('%Y/%m/%d')}/{ticker}.json"
    try:
        s3 = boto3.client("s3", region_name=AWS_REGION)
        response = s3.head_object(Bucket=bucket, Key=key)
        last_modified = response["LastModified"]
        age_hours = (datetime.now(tz=timezone.utc) - last_modified).total_seconds() / 3600
        if age_hours < 25:
            score = 100.0
        else:
            score = max(0.0, round(100.0 - (age_hours - 25) * 2, 1))
        logger.info("Timeliness score for %s: %.1f (age %.1fh)", ticker, score, age_hours)
        return score
    except Exception as exc:
        logger.warning("Could not score timeliness for %s: %s", ticker, exc)
        return 0.0


def score_validity(bucket: str, ticker: str, date: str) -> float:
    dt = datetime.strptime(date, "%Y-%m-%d")
    key = f"processed/validation/{dt.strftime('%Y/%m/%d')}/{ticker}.json"
    try:
        s3 = boto3.client("s3", region_name=AWS_REGION)
        response = s3.get_object(Bucket=bucket, Key=key)
        report = json.loads(response["Body"].read().decode("utf-8"))
        passed = report.get("checks_passed", 0)
        total = report.get("checks_total", 1)
        score = round((passed / total) * 100, 1) if total else 0.0
        logger.info("Validity score for %s: %.1f", ticker, score)
        return score
    except Exception as exc:
        logger.warning("Could not score validity for %s: %s", ticker, exc)
        return 0.0


def _assign_grade(score: float) -> str:
    if score >= 90:
        return "A"
    elif score >= 80:
        return "B"
    elif score >= 70:
        return "C"
    elif score >= 60:
        return "D"
    return "F"


def calculate_dq_score(ticker: str, bucket: str, date: str) -> dict:
    scores = {
        "completeness": score_completeness(bucket, ticker, date),
        "accuracy": score_accuracy(bucket, ticker, date),
        "consistency": score_consistency(bucket, ticker, date),
        "timeliness": score_timeliness(bucket, ticker),
        "validity": score_validity(bucket, ticker, date),
    }
    total_score: float = 0.0
    for dimension in QUALITY_DIMENSIONS:
        dim_name: str = str(dimension["dimension"])
        weight: float = float(str(dimension["weight"]))
        dim_score: float = float(scores.get(dim_name, 0.0))
        total_score += dim_score * weight
    overall = round(total_score, 1)
    grade = _assign_grade(overall)
    logger.info("DQ score for %s: %.1f (%s)", ticker, overall, grade)
    return {
        "ticker": ticker,
        "overall_score": overall,
        "grade": grade,
        "dimensions": scores,
    }


def run_quality_scoring(bucket: str, date: str) -> dict:
    ticker_scores = [calculate_dq_score(t, bucket, date) for t in TICKERS]
    portfolio_avg = round(sum(t["overall_score"] for t in ticker_scores) / len(ticker_scores), 1)
    portfolio_grade = _assign_grade(portfolio_avg)
    for ts in ticker_scores:
        logger.info("  %s: %.1f (%s)", ts["ticker"], ts["overall_score"], ts["grade"])
    logger.info("Portfolio quality score: %.1f (%s)", portfolio_avg, portfolio_grade)
    return {
        "date": date,
        "portfolio_score": portfolio_avg,
        "portfolio_grade": portfolio_grade,
        "tickers": ticker_scores,
    }


if __name__ == "__main__":
    pass
