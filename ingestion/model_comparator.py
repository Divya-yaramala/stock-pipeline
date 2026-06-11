import json
import logging
import os
from datetime import datetime
from typing import Any, Dict, Tuple

import boto3
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression
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


def prepare_training_data(
    df: pd.DataFrame,
    target_col: str = "daily_return",
    test_size: float = 0.2,
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.Series]:
    available_features = [c for c in FEATURE_COLS if c in df.columns and c != target_col]
    X = df[available_features]
    y = df[target_col]

    split_idx = int(len(df) * (1 - test_size))
    X_train = X.iloc[:split_idx]
    X_test = X.iloc[split_idx:]
    y_train = y.iloc[:split_idx]
    y_test = y.iloc[split_idx:]

    return X_train, X_test, y_train, y_test


def train_random_forest(X_train: pd.DataFrame, y_train: pd.Series) -> Dict[str, Any]:
    model = RandomForestRegressor(n_estimators=100, random_state=42)
    model.fit(X_train, y_train)
    importances = dict(zip(X_train.columns.tolist(), model.feature_importances_.tolist()))
    logger.info("Random Forest trained on %d samples", len(X_train))
    return {"model": model, "feature_importances": importances}


def train_linear_regression(X_train: pd.DataFrame, y_train: pd.Series) -> Dict[str, Any]:
    model = LinearRegression()
    model.fit(X_train, y_train)
    coefficients = dict(zip(X_train.columns.tolist(), model.coef_.tolist()))
    logger.info("Linear Regression trained on %d samples", len(X_train))
    return {"model": model, "coefficients": coefficients}


def evaluate_model(
    model: Any,
    X_test: pd.DataFrame,
    y_test: pd.Series,
    model_name: str,
) -> Dict[str, Any]:
    y_pred = model.predict(X_test)
    mae = float(mean_absolute_error(y_test, y_pred))
    rmse = float(np.sqrt(mean_squared_error(y_test, y_pred)))
    r2 = float(r2_score(y_test, y_pred))

    metrics = {
        "model_name": model_name,
        "MAE": round(mae, 4),
        "RMSE": round(rmse, 4),
        "R2": round(r2, 4),
    }
    logger.info("%s — MAE: %.4f  RMSE: %.4f  R2: %.4f", model_name, mae, rmse, r2)
    return metrics


def compare_models(ticker: str, bucket: str) -> Dict[str, Any]:
    s3 = boto3.client("s3")
    date_str = datetime.utcnow().strftime("%Y/%m/%d")
    key = f"processed/features/{date_str}/{ticker}.json"

    response = s3.get_object(Bucket=bucket, Key=key)
    records = json.loads(response["Body"].read().decode("utf-8"))
    df = pd.DataFrame(records)
    for col in FEATURE_COLS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna(subset=FEATURE_COLS)

    X_train, X_test, y_train, y_test = prepare_training_data(df)

    rf_result = train_random_forest(X_train, y_train)
    lr_result = train_linear_regression(X_train, y_train)

    rf_metrics = evaluate_model(rf_result["model"], X_test, y_test, "RandomForest")
    lr_metrics = evaluate_model(lr_result["model"], X_test, y_test, "LinearRegression")

    winner = "RandomForest" if rf_metrics["RMSE"] <= lr_metrics["RMSE"] else "LinearRegression"
    logger.info(
        "Winner for %s: %s (RMSE=%.4f)",
        ticker,
        winner,
        rf_metrics["RMSE"] if winner == "RandomForest" else lr_metrics["RMSE"],
    )

    results = {
        "ticker": ticker,
        "date": datetime.utcnow().strftime("%Y-%m-%d"),
        "models": {
            "RandomForest": {**rf_metrics, "feature_importances": rf_result["feature_importances"]},
            "LinearRegression": {**lr_metrics, "coefficients": lr_result["coefficients"]},
        },
        "winner": winner,
    }

    save_key = f"models/comparisons/{date_str}/{ticker}.json"
    s3.put_object(
        Bucket=bucket,
        Key=save_key,
        Body=json.dumps(results, indent=2).encode("utf-8"),
        ContentType="application/json",
    )
    logger.info("Saved comparison results for %s to s3://%s/%s", ticker, bucket, save_key)
    return results


if __name__ == "__main__":
    _bucket = os.getenv("AWS_BUCKET_NAME", "")
    pass
