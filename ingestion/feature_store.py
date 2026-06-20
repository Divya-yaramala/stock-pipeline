import json
import logging
from datetime import datetime

import boto3
import pandas as pd

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TICKERS = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"]


def save_features(
    ticker: str,
    features: dict,
    feature_group: str,
    bucket: str,
) -> bool:
    date_path = datetime.now().strftime("%Y/%m/%d")
    key = f"features/{feature_group}/{date_path}/{ticker}.json"

    entry = {
        "ticker": ticker,
        "feature_group": feature_group,
        "features": features,
        "saved_at": datetime.now().isoformat(),
    }

    try:
        s3 = boto3.client("s3")
        s3.put_object(
            Bucket=bucket,
            Key=key,
            Body=json.dumps(entry, indent=2).encode("utf-8"),
            ContentType="application/json",
        )
        logger.info("Features saved: ticker=%s group=%s key=%s", ticker, feature_group, key)
        return True
    except Exception as e:
        logger.error("Failed to save features for %s/%s: %s", ticker, feature_group, e)
        return False


def get_features(
    ticker: str,
    feature_group: str,
    bucket: str,
    date: str,
) -> dict:
    date_path = date.replace("-", "/")
    key = f"features/{feature_group}/{date_path}/{ticker}.json"

    try:
        s3 = boto3.client("s3")
        response = s3.get_object(Bucket=bucket, Key=key)
        entry = json.loads(response["Body"].read().decode("utf-8"))
        logger.info("Features loaded: ticker=%s group=%s date=%s", ticker, feature_group, date)
        return entry.get("features", {})
    except Exception:
        return {}


def list_feature_groups(bucket: str) -> list:
    s3 = boto3.client("s3")
    try:
        response = s3.list_objects_v2(Bucket=bucket, Prefix="features/", Delimiter="/")
        groups = [
            p["Prefix"].rstrip("/").split("/")[-1]
            for p in response.get("CommonPrefixes", [])
        ]
        logger.info("list_feature_groups: %d groups found", len(groups))
        return groups
    except Exception as e:
        logger.error("Failed to list feature groups: %s", e)
        return []


def get_latest_features(ticker: str, bucket: str) -> dict:
    today = datetime.now().strftime("%Y-%m-%d")
    groups = list_feature_groups(bucket)

    all_features: dict = {}
    for group in groups:
        feats = get_features(ticker, group, bucket, today)
        all_features.update(feats)

    feature_series = pd.Series(all_features)
    logger.info("get_latest_features: ticker=%s features=%d", ticker, len(feature_series))
    return feature_series.to_dict()


def run_feature_store_check(bucket: str) -> dict:
    today = datetime.now().strftime("%Y-%m-%d")
    groups = list_feature_groups(bucket)
    tickers_with_features = 0
    missing = []

    for ticker in TICKERS:
        has_features = False
        for group in groups:
            if get_features(ticker, group, bucket, today):
                has_features = True
                break
        if has_features:
            tickers_with_features += 1
        else:
            missing.append(ticker)

    logger.info(
        "Feature store check: %d/%d tickers have features", tickers_with_features, len(TICKERS)
    )
    return {"tickers_with_features": tickers_with_features, "missing": missing}


if __name__ == "__main__":
    pass
