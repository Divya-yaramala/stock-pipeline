import json
import logging
import os
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

import boto3

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")


def profile_pipeline_step(
    step_name: str,
    func: Any,
    *args: Any,
    **kwargs: Any,
) -> Dict[str, Any]:
    start = time.time()
    success = True
    try:
        func(*args, **kwargs)
    except Exception as e:
        success = False
        logger.error(f"Step {step_name} failed: {e}")
    duration = round(time.time() - start, 4)
    result: Dict[str, Any] = {
        "step": step_name,
        "duration_seconds": duration,
        "success": success,
    }
    logger.info(f"Step profile: {step_name} took {duration}s, success={success}")
    return result


def identify_bottlenecks(
    step_profiles: List[Dict[str, Any]],
    threshold_seconds: float = 10.0,
) -> List[Dict[str, Any]]:
    bottlenecks = [
        p for p in step_profiles if float(str(p["duration_seconds"])) > threshold_seconds
    ]
    logger.info(
        f"Bottleneck detection: {len(bottlenecks)} steps exceed {threshold_seconds}s threshold"
    )
    return bottlenecks


def calculate_pipeline_efficiency(
    step_profiles: List[Dict[str, Any]],
) -> Dict[str, Any]:
    if not step_profiles:
        return {
            "total_seconds": 0.0,
            "slowest_step": "",
            "fastest_step": "",
            "efficiency_score": 0.0,
        }

    durations = [float(str(p["duration_seconds"])) for p in step_profiles]
    total_seconds = sum(durations)
    slowest = step_profiles[durations.index(max(durations))]
    fastest = step_profiles[durations.index(min(durations))]
    efficiency_score = min(durations) / total_seconds * 100 if total_seconds > 0 else 0.0

    result: Dict[str, Any] = {
        "total_seconds": round(total_seconds, 4),
        "slowest_step": str(slowest["step"]),
        "fastest_step": str(fastest["step"]),
        "efficiency_score": round(efficiency_score, 2),
    }
    logger.info(f"Pipeline efficiency: total={total_seconds:.2f}s, score={efficiency_score:.2f}%")
    return result


def generate_optimization_recommendations(
    bottlenecks: List[Dict[str, Any]],
) -> List[str]:
    recommendations: List[str] = []
    for b in bottlenecks:
        step = str(b["step"])
        duration = float(str(b["duration_seconds"]))
        recommendations.append(f"Consider parallelizing {step} — takes {duration:.1f}s")
    logger.info(f"Generated {len(recommendations)} optimization recommendations")
    return recommendations


def run_pipeline_profiling(
    bucket: Optional[str] = None,
) -> Dict[str, Any]:
    dummy_steps = [
        ("fetch_stocks", lambda: time.sleep(0.01)),
        ("validate_data", lambda: time.sleep(0.01)),
        ("detect_anomalies", lambda: time.sleep(0.01)),
        ("predict_prices", lambda: time.sleep(0.01)),
        ("generate_insights", lambda: time.sleep(0.01)),
    ]

    profiles: List[Dict[str, Any]] = []
    for step_name, func in dummy_steps:
        profile = profile_pipeline_step(step_name, func)
        profiles.append(profile)

    bottlenecks = identify_bottlenecks(profiles)
    efficiency = calculate_pipeline_efficiency(profiles)
    recommendations = generate_optimization_recommendations(bottlenecks)

    report: Dict[str, Any] = {
        "timestamp": datetime.utcnow().isoformat(),
        "step_profiles": profiles,
        "bottlenecks": bottlenecks,
        "efficiency": efficiency,
        "recommendations": recommendations,
    }

    if bucket:
        try:
            s3_client = boto3.client("s3", region_name=AWS_REGION)
            now = datetime.utcnow()
            key = f"reports/profiling/{now.year}/{now.month:02d}/{now.day:02d}/report.json"
            s3_client.put_object(Bucket=bucket, Key=key, Body=json.dumps(report, default=str))
            logger.info(f"Profiling report saved to s3://{bucket}/{key}")
        except Exception as e:
            logger.error(f"Failed to save profiling report: {e}")

    logger.info("Pipeline Profiling Complete")
    return report


if __name__ == "__main__":
    pass
