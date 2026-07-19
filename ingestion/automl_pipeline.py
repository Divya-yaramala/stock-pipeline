import json
import logging
import os
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

import boto3
import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.linear_model import Lasso, LinearRegression, Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

FEATURE_COLS = [
    "daily_return",
    "high_low_range",
    "price_position",
    "body_size",
    "volume_ratio",
    "roc_5",
    "roc_10",
]

CANDIDATE_MODELS: List[Dict[str, Any]] = [
    {"name": "random_forest", "params": {"n_estimators": 100, "max_depth": 10}},
    {"name": "gradient_boosting", "params": {"n_estimators": 100, "learning_rate": 0.1}},
    {"name": "linear_regression", "params": {}},
    {"name": "ridge", "params": {"alpha": 1.0}},
    {"name": "lasso", "params": {"alpha": 1.0}},
]


def train_candidate(
    model_config: Dict[str, Any],
    X_train: Any,
    y_train: Any,
) -> Dict[str, Any]:
    name = str(model_config["name"])
    params = dict(model_config["params"])

    model_map = {
        "random_forest": RandomForestRegressor,
        "gradient_boosting": GradientBoostingRegressor,
        "linear_regression": LinearRegression,
        "ridge": Ridge,
        "lasso": Lasso,
    }

    cls = model_map[name]
    model = cls(**params)

    start = time.time()
    model.fit(X_train, y_train)
    train_time = float(time.time() - start)

    logger.info("Trained %s in %.2f seconds", name, train_time)
    return {"name": name, "model": model, "train_time_seconds": train_time}


def evaluate_candidate(
    candidate: Dict[str, Any],
    X_test: Any,
    y_test: Any,
) -> Dict[str, Any]:
    name = str(candidate["name"])
    model = candidate["model"]

    y_pred = model.predict(X_test)
    mae = float(mean_absolute_error(y_test, y_pred))
    rmse = float(np.sqrt(mean_squared_error(y_test, y_pred)))
    r2 = float(r2_score(y_test, y_pred))

    logger.info("%s — MAE: %.4f  RMSE: %.4f  R2: %.4f", name, mae, rmse, r2)
    return {"name": name, "mae": mae, "rmse": rmse, "r2": r2}


def run_automl(
    X_train: Any,
    y_train: Any,
    X_test: Any,
    y_test: Any,
) -> Dict[str, Any]:
    candidates = [train_candidate(cfg, X_train, y_train) for cfg in CANDIDATE_MODELS]
    results = [evaluate_candidate(c, X_test, y_test) for c in candidates]

    winner_result = min(results, key=lambda r: float(r["rmse"]))
    winner_name = str(winner_result["name"])

    logger.info(
        "AutoML winner: %s  RMSE=%.4f",
        winner_name,
        float(winner_result["rmse"]),
    )
    return {
        "winner": winner_name,
        "results": results,
        "best_metrics": winner_result,
    }


def save_automl_results(
    ticker: str,
    results: Dict[str, Any],
    bucket: str,
    date: str,
) -> bool:
    try:
        s3 = boto3.client("s3")
        date_path = datetime.strptime(date, "%Y-%m-%d").strftime("%Y/%m/%d")
        key = f"models/automl/{date_path}/{ticker}.json"
        payload = {
            "ticker": ticker,
            "date": date,
            **results,
        }
        s3.put_object(
            Bucket=bucket,
            Key=key,
            Body=json.dumps(payload, indent=2).encode("utf-8"),
            ContentType="application/json",
        )
        logger.info("Saved AutoML results to s3://%s/%s", bucket, key)
        return True
    except Exception as exc:
        logger.error("Failed to save AutoML results: %s", exc)
        return False


def run_automl_pipeline(
    ticker: str,
    bucket: str,
) -> Dict[str, Any]:
    s3 = boto3.client("s3")
    date_str = datetime.utcnow().strftime("%Y/%m/%d")
    key = f"processed/features/{date_str}/{ticker}.json"

    response = s3.get_object(Bucket=bucket, Key=key)
    records = json.loads(response["Body"].read().decode("utf-8"))
    df = pd.DataFrame(records)

    available = [c for c in FEATURE_COLS if c in df.columns]
    for col in available:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna(subset=available)

    target_col = "daily_return"
    feature_cols = [c for c in available if c != target_col]
    X = df[feature_cols].values
    y = df[target_col].values

    split_idx = int(len(df) * 0.8)
    X_train, X_test = X[:split_idx], X[split_idx:]
    y_train, y_test = y[:split_idx], y[split_idx:]

    results = run_automl(X_train, y_train, X_test, y_test)

    today = datetime.utcnow().strftime("%Y-%m-%d")
    save_automl_results(ticker, results, bucket, today)

    winner = str(results["winner"])
    rmse = float(results["best_metrics"]["rmse"])
    logger.info("AutoML Complete: winner=%s RMSE=%.4f", winner, rmse)
    return results


if __name__ == "__main__":
    pass
