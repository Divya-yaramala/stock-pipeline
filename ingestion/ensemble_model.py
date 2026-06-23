import json
import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

import boto3
import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")

FEATURE_COLS = [
    "daily_return",
    "high_low_range",
    "price_position",
    "body_size",
    "volume_ratio",
    "roc_5",
    "roc_10",
]


def load_feature_matrix(ticker: str, bucket: str) -> pd.DataFrame:
    s3 = boto3.client("s3", region_name=AWS_REGION)
    date_str = datetime.utcnow().strftime("%Y/%m/%d")
    key = f"processed/features/{date_str}/{ticker}.json"
    try:
        response = s3.get_object(Bucket=bucket, Key=key)
        records = json.loads(response["Body"].read().decode("utf-8"))
        df = pd.DataFrame(records)
        for col in FEATURE_COLS:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
        df = df.dropna(subset=[c for c in FEATURE_COLS if c in df.columns])
        logger.info("Loaded feature matrix for %s: %d rows", ticker, len(df))
        return df
    except Exception as exc:
        logger.warning("Could not load feature matrix for %s: %s", ticker, exc)
        return pd.DataFrame()


def train_ensemble(X_train: pd.DataFrame, y_train: pd.Series) -> Dict[str, Any]:
    rf = RandomForestRegressor(n_estimators=100, random_state=42)
    rf.fit(X_train, y_train)
    logger.info("RandomForestRegressor trained on %d samples", len(X_train))

    gb = GradientBoostingRegressor(n_estimators=100, random_state=42)
    gb.fit(X_train, y_train)
    logger.info("GradientBoostingRegressor trained on %d samples", len(X_train))

    lr = LinearRegression()
    lr.fit(X_train, y_train)
    logger.info("LinearRegression trained on %d samples", len(X_train))

    return {
        "random_forest": rf,
        "gradient_boosting": gb,
        "linear_regression": lr,
    }


def ensemble_predict(
    models: Dict[str, Any],
    X_test: pd.DataFrame,
    weights: Optional[List[float]] = None,
) -> np.ndarray:
    preds = [
        models["random_forest"].predict(X_test),
        models["gradient_boosting"].predict(X_test),
        models["linear_regression"].predict(X_test),
    ]

    if weights is not None:
        total = sum(weights)
        w = [wi / total for wi in weights]
        combined = sum(p * wi for p, wi in zip(preds, w))
    else:
        combined = sum(preds) / len(preds)

    return np.array(combined)


def evaluate_ensemble(predictions: np.ndarray, y_test: pd.Series) -> dict:
    mae = float(mean_absolute_error(y_test, predictions))
    rmse = float(np.sqrt(mean_squared_error(y_test, predictions)))
    r2 = float(r2_score(y_test, predictions))
    metrics = {
        "MAE": round(mae, 4),
        "RMSE": round(rmse, 4),
        "R2": round(r2, 4),
    }
    logger.info("Ensemble — MAE: %.4f  RMSE: %.4f  R2: %.4f", mae, rmse, r2)
    return metrics


def run_ensemble_prediction(ticker: str, bucket: str) -> dict:
    df = load_feature_matrix(ticker, bucket)
    if df.empty:
        return {"ticker": ticker, "error": "No feature data available", "results": {}}

    available = [c for c in FEATURE_COLS if c in df.columns]
    target = "daily_return"
    if target not in available:
        return {"ticker": ticker, "error": "Target column missing", "results": {}}
    features = [c for c in available if c != target]

    X = df[features]
    y = df[target]
    split = int(len(df) * 0.8)
    X_train, X_test = X.iloc[:split], X.iloc[split:]
    y_train, y_test = y.iloc[:split], y.iloc[split:]

    if len(X_train) < 5 or len(X_test) < 2:
        return {"ticker": ticker, "error": "Insufficient data for training", "results": {}}

    models = train_ensemble(X_train, y_train)
    predictions = ensemble_predict(models, X_test)
    metrics = evaluate_ensemble(predictions, y_test)

    results = {
        "ticker": ticker,
        "date": datetime.utcnow().strftime("%Y-%m-%d"),
        "training_samples": len(X_train),
        "test_samples": len(X_test),
        "features_used": features,
        "results": metrics,
    }

    try:
        s3 = boto3.client("s3", region_name=AWS_REGION)
        date_str = datetime.utcnow().strftime("%Y/%m/%d")
        key = f"models/ensemble/{date_str}/{ticker}.json"
        s3.put_object(
            Bucket=bucket,
            Key=key,
            Body=json.dumps(results, indent=2).encode("utf-8"),
            ContentType="application/json",
        )
        logger.info("Saved ensemble results for %s to s3://%s/%s", ticker, bucket, key)
    except Exception as exc:
        logger.error("Failed to save ensemble results for %s: %s", ticker, exc)

    return results


if __name__ == "__main__":
    pass
