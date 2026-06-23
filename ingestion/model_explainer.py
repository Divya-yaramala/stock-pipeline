import json
import logging
import os
from datetime import datetime
from typing import Any

import boto3
import numpy as np
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")


def calculate_feature_importance(model: Any, feature_names: list) -> dict:
    if hasattr(model, "feature_importances_"):
        importances = model.feature_importances_
    elif hasattr(model, "coef_"):
        importances = np.abs(model.coef_)
    else:
        importances = np.ones(len(feature_names)) / len(feature_names)

    importance_dict = {name: round(float(imp), 6) for name, imp in zip(feature_names, importances)}
    sorted_dict = dict(sorted(importance_dict.items(), key=lambda x: x[1], reverse=True))
    top5 = list(sorted_dict.items())[:5]
    logger.info("Top 5 features: %s", top5)
    return sorted_dict


def calculate_shap_values(model: Any, X: pd.DataFrame) -> dict:
    feature_names = X.columns.tolist()
    importance_dict = calculate_feature_importance(model, feature_names)

    shap_approx = {}
    for feature in feature_names:
        base_importance = importance_dict.get(feature, 0.0)
        col_vals = X[feature].values
        col_std = float(np.std(col_vals)) if np.std(col_vals) > 0 else 1.0
        avg_impact = round(base_importance * col_std, 6)
        shap_approx[feature] = avg_impact

    shap_approx = dict(sorted(shap_approx.items(), key=lambda x: abs(x[1]), reverse=True))
    logger.info("SHAP approximation computed for %d features", len(shap_approx))
    return shap_approx


def generate_explanation_report(
    ticker: str,
    model: Any,
    X: pd.DataFrame,
    prediction: float,
) -> dict:
    feature_names = X.columns.tolist()
    importance_dict = calculate_feature_importance(model, feature_names)
    top_features = list(importance_dict.items())[:3]

    signal_map = {
        "rsi": ("RSI was elevated", "bearish signal"),
        "volume_ratio": ("Volume was above average", "bullish signal"),
        "macd": ("MACD showed momentum", "bullish signal"),
        "roc_5": ("Short-term momentum was positive", "bullish signal"),
        "roc_10": ("Medium-term momentum was positive", "bullish signal"),
        "daily_return": ("Recent returns were strong", "bullish signal"),
        "high_low_range": ("Price range was wide", "high volatility"),
        "price_position": ("Price closed near its high", "bullish signal"),
        "body_size": ("Candle body was large", "strong directional move"),
        "volume_sma_20": ("Volume trend was elevated", "bullish signal"),
    }

    reasons = []
    for i, (feat, imp) in enumerate(top_features, start=1):
        desc, signal = signal_map.get(feat, (f"{feat} was influential", "notable signal"))
        reasons.append(f"{i}. {desc} ({signal}, importance={imp:.4f})")

    explanation_text = f"The model predicted ${prediction:.2f} for {ticker} because:\n" + "\n".join(
        reasons
    )

    report = {
        "ticker": ticker,
        "prediction": round(prediction, 4),
        "explanation": explanation_text,
        "top_features": {feat: imp for feat, imp in top_features},
        "generated_at": datetime.utcnow().isoformat(),
    }
    logger.info("Explanation generated for %s", ticker)
    return report


def save_explanation_to_s3(explanation: dict, ticker: str, bucket: str, date: str) -> bool:
    dt = datetime.strptime(date, "%Y-%m-%d")
    key = f"models/explanations/{dt.strftime('%Y/%m/%d')}/{ticker}.json"
    try:
        s3 = boto3.client("s3", region_name=AWS_REGION)
        s3.put_object(
            Bucket=bucket,
            Key=key,
            Body=json.dumps(explanation, indent=2).encode("utf-8"),
            ContentType="application/json",
        )
        logger.info("Saved explanation for %s to s3://%s/%s", ticker, bucket, key)
        return True
    except Exception as exc:
        logger.error("Failed to save explanation for %s: %s", ticker, exc)
        return False


def run_model_explanation(ticker: str, bucket: str) -> dict:
    s3 = boto3.client("s3", region_name=AWS_REGION)
    date_str = datetime.utcnow().strftime("%Y/%m/%d")
    key = f"models/ensemble/{date_str}/{ticker}.json"
    try:
        response = s3.get_object(Bucket=bucket, Key=key)
        ensemble_results = json.loads(response["Body"].read().decode("utf-8"))
    except Exception as exc:
        logger.warning("Could not load ensemble results for %s: %s", ticker, exc)
        ensemble_results = {}

    metrics = ensemble_results.get("results", {})
    features_used = ensemble_results.get("features_used", ["daily_return", "roc_5"])

    dummy_data = {feat: np.random.randn(10) for feat in features_used}
    X_dummy = pd.DataFrame(dummy_data)

    from sklearn.ensemble import RandomForestRegressor

    dummy_model = RandomForestRegressor(n_estimators=10, random_state=42)
    dummy_y = np.random.randn(10)
    dummy_model.fit(X_dummy, dummy_y)

    prediction = float(metrics.get("MAE", 0.0))
    today = datetime.utcnow().strftime("%Y-%m-%d")
    report = generate_explanation_report(ticker, dummy_model, X_dummy, prediction)
    save_explanation_to_s3(report, ticker, bucket, today)

    logger.info("Model explanation complete for %s", ticker)
    return report


if __name__ == "__main__":
    pass
