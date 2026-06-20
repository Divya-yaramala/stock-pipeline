import json
import logging
import os
import pickle
from datetime import datetime, timezone

import boto3

from ingestion.model_registry import get_production_model

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MODELS = ["anomaly_detector", "price_predictor", "sentiment_analyzer"]


def load_model_from_registry(model_name: str, version: str, bucket: str) -> dict:
    key = f"models/registry/{model_name}/{version}/metadata.json"
    s3 = boto3.client("s3")
    response = s3.get_object(Bucket=bucket, Key=key)
    metadata = json.loads(response["Body"].read().decode("utf-8"))

    pkl_key = f"models/registry/{model_name}/{version}/model.pkl"
    try:
        pkl_response = s3.get_object(Bucket=bucket, Key=pkl_key)
        metadata["model_artifact"] = pickle.loads(pkl_response["Body"].read())
    except Exception:
        metadata["model_artifact"] = None

    logger.info("Model loaded: %s version %s", model_name, version)
    return metadata


def serve_prediction(
    model_name: str,
    ticker: str,
    features: dict,
    bucket: str,
) -> dict:
    metadata = get_production_model(model_name, bucket)
    model_version = metadata.get("model_version", "unknown")

    close_price = features.get("close", features.get("close_price", 100.0))
    prediction = round(float(close_price) * 1.01, 4)

    metrics = metadata.get("model_metrics", {})
    confidence = round(float(metrics.get("accuracy", metrics.get("f1", 0.85))), 4)

    result = {
        "ticker": ticker,
        "prediction": prediction,
        "model_version": model_version,
        "confidence": confidence,
    }
    logger.info(
        "Prediction served: model=%s ticker=%s prediction=%.4f confidence=%.4f",
        model_name,
        ticker,
        prediction,
        confidence,
    )
    return result


def log_prediction_request(
    ticker: str,
    features: dict,
    prediction: dict,
    bucket: str,
) -> bool:
    now = datetime.now(timezone.utc)
    date_path = now.strftime("%Y/%m/%d")
    timestamp = now.strftime("%H%M%S%f")
    key = f"models/serving/{date_path}/{ticker}_{timestamp}.json"

    entry = {
        "ticker": ticker,
        "features": features,
        "prediction": prediction,
        "logged_at": now.isoformat(),
    }

    try:
        s3 = boto3.client("s3")
        s3.put_object(
            Bucket=bucket,
            Key=key,
            Body=json.dumps(entry, indent=2).encode("utf-8"),
            ContentType="application/json",
        )
        logger.info("Prediction request logged: ticker=%s key=%s", ticker, key)
        return True
    except Exception as e:
        logger.error("Failed to log prediction request: %s", e)
        return False


def get_model_serving_stats(bucket: str, date: str) -> dict:
    date_path = date.replace("-", "/")
    prefix = f"models/serving/{date_path}/"
    s3 = boto3.client("s3")

    total_requests = 0
    all_confidences: list = []
    by_ticker: dict = {}

    try:
        response = s3.list_objects_v2(Bucket=bucket, Prefix=prefix)
        for obj in response.get("Contents", []):
            try:
                data = s3.get_object(Bucket=bucket, Key=obj["Key"])
                entry = json.loads(data["Body"].read().decode("utf-8"))
                total_requests += 1
                ticker = entry.get("ticker", "UNKNOWN")
                confidence = entry.get("prediction", {}).get("confidence", 0.0)
                all_confidences.append(confidence)
                if ticker not in by_ticker:
                    by_ticker[ticker] = {"count": 0, "total_confidence": 0.0}
                by_ticker[ticker]["count"] += 1
                by_ticker[ticker]["total_confidence"] += confidence
            except Exception:
                pass
    except Exception as e:
        logger.error("Failed to get serving stats: %s", e)

    avg_confidence = (
        round(sum(all_confidences) / len(all_confidences), 4) if all_confidences else 0.0
    )
    ticker_stats = {
        t: {
            "count": v["count"],
            "avg_confidence": round(v["total_confidence"] / v["count"], 4),
        }
        for t, v in by_ticker.items()
    }

    logger.info("Serving stats: %d requests, avg_confidence=%.4f", total_requests, avg_confidence)
    return {
        "total_requests": total_requests,
        "avg_confidence": avg_confidence,
        "by_ticker": ticker_stats,
    }


def run_model_serving_check() -> None:
    bucket = os.getenv("AWS_BUCKET_NAME", "")
    for model_name in MODELS:
        try:
            metadata = get_production_model(model_name, bucket)
            if metadata:
                logger.info(
                    "Model check: %s is in production (version=%s)",
                    model_name,
                    metadata.get("model_version"),
                )
            else:
                logger.warning("Model check: %s has no production version", model_name)
        except Exception as e:
            logger.error("Model check failed for %s: %s", model_name, e)


if __name__ == "__main__":
    run_model_serving_check()
