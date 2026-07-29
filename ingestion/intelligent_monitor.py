import hashlib
import json
import logging
from typing import Any, Dict, List

import boto3

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def correlate_metrics(
    metrics: Dict[str, List[float]],
) -> Dict[str, float]:
    correlations: Dict[str, float] = {}
    keys = list(metrics.keys())

    for i in range(len(keys)):
        for j in range(i + 1, len(keys)):
            a_key = keys[i]
            b_key = keys[j]
            a_vals = metrics[a_key]
            b_vals = metrics[b_key]
            n = min(len(a_vals), len(b_vals))
            if n < 2:
                continue
            a = a_vals[:n]
            b = b_vals[:n]
            a_mean = sum(a) / n
            b_mean = sum(b) / n
            num = sum((a[k] - a_mean) * (b[k] - b_mean) for k in range(n))
            a_std = sum((a[k] - a_mean) ** 2 for k in range(n)) ** 0.5
            b_std = sum((b[k] - b_mean) ** 2 for k in range(n)) ** 0.5
            if a_std == 0 or b_std == 0:
                corr = 0.0
            else:
                corr = num / (a_std * b_std)
            pair = f"{a_key}_vs_{b_key}"
            correlations[pair] = float(corr)
            if abs(corr) > 0.7:
                logger.info(f"Significant correlation {pair}: {corr:.4f}")

    return correlations


def detect_metric_anomaly(
    metric_name: str,
    values: List[float],
    z_threshold: float = 2.5,
) -> Dict[str, Any]:
    if len(values) < 2:
        return {"anomaly_detected": False, "z_score": 0.0, "direction": "none"}

    baseline = values[:-1]
    mean = sum(baseline) / len(baseline)
    variance = sum((v - mean) ** 2 for v in baseline) / len(baseline)
    std = variance**0.5 if variance > 0 else 1e-9
    latest = values[-1]
    z_score = (latest - mean) / std
    anomaly_detected = abs(z_score) > z_threshold
    direction = "up" if z_score > 0 else "down" if z_score < 0 else "none"

    result: Dict[str, Any] = {
        "anomaly_detected": anomaly_detected,
        "z_score": float(z_score),
        "direction": direction,
    }
    logger.info(f"Metric anomaly detection for {metric_name}: {result}")
    return result


def generate_root_cause_hypothesis(
    failed_metric: str,
    correlated_metrics: Dict[str, float],
) -> List[str]:
    hypotheses: List[str] = []
    hypotheses.append(
        f"Direct degradation in {failed_metric} detected — check upstream data source."
    )

    for pair, corr in correlated_metrics.items():
        if abs(float(str(corr))) > 0.6:
            other = pair.replace(failed_metric, "").replace("_vs_", "").strip("_")
            if other and other != failed_metric:
                direction = "positively" if float(str(corr)) > 0 else "negatively"
                hypotheses.append(
                    f"{other} is {direction} correlated with {failed_metric} "
                    f"(r={float(str(corr)):.2f}) — degradation may be caused by {other} changes."
                )

    if not correlated_metrics:
        hypotheses.append(
            f"No correlated metrics found — {failed_metric} degradation may be isolated."
        )

    logger.info(f"Generated {len(hypotheses)} hypotheses for {failed_metric}")
    return hypotheses


def calculate_health_fingerprint(
    metrics: Dict[str, float],
) -> str:
    sorted_items = sorted(metrics.items())
    payload = json.dumps(sorted_items, sort_keys=True)
    fingerprint = hashlib.md5(payload.encode()).hexdigest()
    logger.info(f"Health fingerprint calculated: {fingerprint}")
    return fingerprint


def compare_health_fingerprints(
    current: str,
    previous: str,
) -> bool:
    changed = current != previous
    if changed:
        logger.info(f"Health state change detected: {previous} -> {current}")
    return changed


def run_intelligent_monitoring(
    bucket: str,
) -> Dict[str, Any]:
    tickers = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"]
    all_anomalies: List[Dict[str, Any]] = []
    all_hypotheses: List[str] = []
    fingerprints: Dict[str, str] = {}

    sample_metrics: Dict[str, List[float]] = {
        "quality_score": [],
        "anomaly_rate": [],
        "pipeline_duration": [],
    }

    for ticker in tickers:
        ticker_metrics: Dict[str, Any] = {}
        if bucket:
            try:
                s3 = boto3.client("s3")
                key = f"monitoring/metrics/{ticker}_latest.json"
                obj = s3.get_object(Bucket=bucket, Key=key)
                ticker_metrics = json.loads(obj["Body"].read().decode("utf-8"))
            except Exception:
                ticker_metrics = {}

        for metric in ["quality_score", "anomaly_rate", "pipeline_duration"]:
            vals = ticker_metrics.get(metric)
            if vals and isinstance(vals, list):
                sample_metrics[metric].extend([float(str(v)) for v in vals])

        scalar_metrics: Dict[str, float] = {
            k: float(str(v)) for k, v in ticker_metrics.items() if isinstance(v, (int, float))
        }
        if scalar_metrics:
            fp = calculate_health_fingerprint(scalar_metrics)
            fingerprints[ticker] = fp

    correlations = correlate_metrics(sample_metrics)

    for metric_name, vals in sample_metrics.items():
        if len(vals) >= 2:
            anomaly = detect_metric_anomaly(metric_name, vals)
            if anomaly["anomaly_detected"]:
                all_anomalies.append({"metric": metric_name, **anomaly})
                hypotheses = generate_root_cause_hypothesis(metric_name, correlations)
                all_hypotheses.extend(hypotheses)

    combined_fp_input: Dict[str, float] = {
        k: float(str(sum(v) / len(v))) for k, v in sample_metrics.items() if v
    }
    overall_fingerprint = (
        calculate_health_fingerprint(combined_fp_input) if combined_fp_input else "no_data"
    )

    result: Dict[str, Any] = {
        "fingerprint": overall_fingerprint,
        "anomalies_found": len(all_anomalies),
        "anomalies": all_anomalies,
        "correlations": correlations,
        "hypotheses": all_hypotheses,
        "ticker_fingerprints": fingerprints,
    }
    logger.info("Intelligent Monitoring Complete")
    return result


if __name__ == "__main__":
    pass
