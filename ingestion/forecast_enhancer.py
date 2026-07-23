import datetime
import json
import logging
import os  # noqa: F401
from typing import Any, Dict, List, Optional

import boto3
import numpy as np
import pandas as pd  # noqa: F401

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def add_confidence_intervals(
    predictions: List[float],
    historical_volatility: float,
    confidence_level: float = 0.95,
) -> List[Dict[str, float]]:
    z = 1.96 if confidence_level >= 0.95 else 1.645
    result: List[Dict[str, float]] = []
    for i, pred in enumerate(predictions):
        horizon = float(i + 1)
        margin = z * historical_volatility * (horizon**0.5)
        result.append(
            {
                "prediction": round(float(pred), 4),
                "lower": round(float(pred) - margin, 4),
                "upper": round(float(pred) + margin, 4),
            }
        )
    logger.info("Confidence intervals added for %d predictions", len(result))
    return result


def adjust_for_seasonality(
    predictions: List[float],
    seasonal_factors: List[float],
) -> List[float]:
    period = len(seasonal_factors)
    adjusted: List[float] = []
    for i, pred in enumerate(predictions):
        factor = float(seasonal_factors[i % period]) if period > 0 else 1.0
        adjusted.append(round(float(pred) * factor, 4))
    logger.info("Seasonality adjustment applied to %d predictions", len(adjusted))
    return adjusted


def blend_forecasts(
    prophet_predictions: List[float],
    ensemble_predictions: List[float],
    prophet_weight: float = 0.6,
) -> List[float]:
    ensemble_weight = 1.0 - prophet_weight
    blended: List[float] = []
    for p, e in zip(prophet_predictions, ensemble_predictions):
        blended.append(round(prophet_weight * float(p) + ensemble_weight * float(e), 4))
    logger.info(
        "Forecasts blended: Prophet %.0f%% + Ensemble %.0f%%",
        prophet_weight * 100,
        ensemble_weight * 100,
    )
    return blended


def calculate_forecast_accuracy(
    predictions: List[float],
    actuals: List[float],
) -> Dict[str, float]:
    n = len(predictions)
    if n == 0 or len(actuals) == 0:
        return {"MAE": 0.0, "RMSE": 0.0, "MAPE": 0.0, "directional_accuracy": 0.0}

    pairs = list(zip(predictions, actuals))
    mae = float(np.mean([abs(float(p) - float(a)) for p, a in pairs]))
    rmse = float(np.sqrt(np.mean([(float(p) - float(a)) ** 2 for p, a in pairs])))

    mape_vals = [abs(float(p) - float(a)) / abs(float(a)) for p, a in pairs if float(a) != 0]
    mape = float(np.mean(mape_vals)) * 100.0 if mape_vals else 0.0

    correct_dir = 0
    dir_total = 0
    for i in range(1, len(predictions)):
        pred_dir = float(predictions[i]) - float(predictions[i - 1])
        actual_dir = float(actuals[i]) - float(actuals[i - 1])
        if pred_dir * actual_dir > 0:
            correct_dir += 1
        dir_total += 1
    directional_accuracy = (float(correct_dir) / float(dir_total) * 100.0) if dir_total > 0 else 0.0

    result: Dict[str, float] = {
        "MAE": round(mae, 4),
        "RMSE": round(rmse, 4),
        "MAPE": round(mape, 4),
        "directional_accuracy": round(directional_accuracy, 2),
    }
    logger.info(
        "Forecast accuracy — MAE=%.4f, RMSE=%.4f, MAPE=%.4f%%, Dir=%.2f%%",
        mae,
        rmse,
        mape,
        directional_accuracy,
    )
    return result


def generate_scenario_forecasts(
    base_prediction: float,
    volatility: float,
) -> Dict[str, float]:
    base = float(base_prediction)
    vol = float(volatility)
    result: Dict[str, float] = {
        "bull": round(base + 2.0 * vol, 4),
        "base": round(base, 4),
        "bear": round(base - 2.0 * vol, 4),
    }
    logger.info(
        "Scenario forecasts — Bull=%.2f, Base=%.2f, Bear=%.2f",
        result["bull"],
        result["base"],
        result["bear"],
    )
    return result


def run_forecast_enhancement(
    ticker: str,
    predictions: List[float],
    actuals: Optional[List[float]],
    bucket: str,
) -> Dict[str, Any]:
    vol = float(np.std(predictions)) if predictions else 0.0
    intervals = add_confidence_intervals(predictions, vol)

    base = float(predictions[-1]) if predictions else 0.0
    scenarios = generate_scenario_forecasts(base, vol)

    accuracy: Optional[Dict[str, float]] = None
    if actuals and len(actuals) == len(predictions):
        accuracy = calculate_forecast_accuracy(predictions, actuals)

    result: Dict[str, Any] = {
        "ticker": ticker,
        "prediction_count": len(predictions),
        "confidence_intervals": intervals,
        "scenarios": scenarios,
        "accuracy": accuracy,
        "enhanced_at": datetime.datetime.utcnow().isoformat(),
    }

    now = datetime.datetime.utcnow()
    s3_key = "processed/forecasts_enhanced/{}/{}/{}/{}.json".format(
        now.strftime("%Y"),
        now.strftime("%m"),
        now.strftime("%d"),
        ticker,
    )

    try:
        s3 = boto3.client("s3")
        s3.put_object(
            Bucket=bucket,
            Key=s3_key,
            Body=json.dumps(result),
            ContentType="application/json",
        )
        logger.info("Saved enhanced forecast to s3://%s/%s", bucket, s3_key)
    except Exception as e:
        logger.warning("S3 upload skipped: %s", str(e))

    logger.info("Forecast Enhancement Complete for %s", ticker)
    return result


if __name__ == "__main__":
    pass
