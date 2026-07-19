import json
import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

import boto3
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import GridSearchCV, cross_val_score

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

PARAM_GRIDS: Dict[str, Any] = {
    "random_forest": {
        "n_estimators": [50, 100, 200],
        "max_depth": [5, 10, None],
        "min_samples_split": [2, 5, 10],
    },
    "gradient_boosting": {
        "n_estimators": [50, 100, 200],
        "learning_rate": [0.05, 0.1, 0.2],
        "max_depth": [3, 5, 7],
    },
}


def tune_random_forest(
    X_train: Any,
    y_train: Any,
    cv_folds: int = 3,
) -> Dict[str, Any]:
    base_model = RandomForestRegressor(random_state=42)
    grid_search = GridSearchCV(
        estimator=base_model,
        param_grid=PARAM_GRIDS["random_forest"],
        cv=cv_folds,
        scoring="neg_mean_squared_error",
        n_jobs=-1,
    )
    grid_search.fit(X_train, y_train)

    best_params = dict(grid_search.best_params_)
    best_score = float(grid_search.best_score_)

    cv_results: Dict[str, Any] = {
        k: v.tolist() if hasattr(v, "tolist") else v
        for k, v in grid_search.cv_results_.items()
    }

    logger.info("Best RF params: %s  score=%.4f", best_params, best_score)
    return {
        "best_params": best_params,
        "best_score": best_score,
        "cv_results": cv_results,
    }


def cross_validate_model(
    model: Any,
    X: Any,
    y: Any,
    cv_folds: int = 5,
) -> Dict[str, float]:
    scores = cross_val_score(
        model,
        X,
        y,
        cv=cv_folds,
        scoring="neg_mean_squared_error",
    )
    scores_list = scores.tolist()
    mean_score = float(np.mean(scores))
    std_score = float(np.std(scores))

    logger.info("CV results — mean=%.4f  std=%.4f", mean_score, std_score)
    return {
        "mean_score": mean_score,
        "std_score": std_score,
        "scores": scores_list,
    }


def save_tuning_results(
    ticker: str,
    results: Dict[str, Any],
    bucket: str,
    date: str,
) -> bool:
    try:
        s3 = boto3.client("s3")
        date_path = datetime.strptime(date, "%Y-%m-%d").strftime("%Y/%m/%d")
        key = f"models/tuning/{date_path}/{ticker}.json"
        payload = {
            "ticker": ticker,
            "date": date,
            **results,
        }
        s3.put_object(
            Bucket=bucket,
            Key=key,
            Body=json.dumps(payload, indent=2, default=str).encode("utf-8"),
            ContentType="application/json",
        )
        logger.info("Saved tuning results to s3://%s/%s", bucket, key)
        return True
    except Exception as exc:
        logger.error("Failed to save tuning results: %s", exc)
        return False


def run_hyperparameter_tuning(
    ticker: str,
    bucket: str,
) -> Dict[str, Any]:
    import pandas as pd

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

    split_idx = int(len(X) * 0.8)
    X_train = X[:split_idx]
    y_train = y[:split_idx]

    tuning_results = tune_random_forest(X_train, y_train)

    today = datetime.utcnow().strftime("%Y-%m-%d")
    save_tuning_results(ticker, tuning_results, bucket, today)

    logger.info("Hyperparameter Tuning Complete for %s", ticker)
    return tuning_results


if __name__ == "__main__":
    pass
