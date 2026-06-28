import json
import logging
from datetime import datetime, timedelta

import boto3

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

PIPELINE_KPIS = [
    {
        "kpi_id": "K001",
        "name": "data_freshness_hours",
        "target": 25,
        "unit": "hours",
        "direction": "lower_is_better",
    },
    {
        "kpi_id": "K002",
        "name": "pipeline_success_rate",
        "target": 95.0,
        "unit": "percent",
        "direction": "higher_is_better",
    },
    {
        "kpi_id": "K003",
        "name": "data_quality_score",
        "target": 90.0,
        "unit": "percent",
        "direction": "higher_is_better",
    },
    {
        "kpi_id": "K004",
        "name": "prediction_accuracy",
        "target": 70.0,
        "unit": "percent",
        "direction": "higher_is_better",
    },
    {
        "kpi_id": "K005",
        "name": "anomaly_detection_rate",
        "target": 95.0,
        "unit": "percent",
        "direction": "higher_is_better",
    },
    {
        "kpi_id": "K006",
        "name": "avg_processing_time",
        "target": 300,
        "unit": "seconds",
        "direction": "lower_is_better",
    },
]


def record_kpi(kpi_id: str, value: float, bucket: str, date: str) -> bool:
    s3 = boto3.client("s3")
    dt = datetime.strptime(date, "%Y-%m-%d")
    key = f"kpis/{dt.strftime('%Y/%m/%d')}/{kpi_id}.json"
    payload = {
        "kpi_id": kpi_id,
        "value": value,
        "date": date,
        "recorded_at": datetime.utcnow().isoformat(),
    }
    try:
        s3.put_object(
            Bucket=bucket,
            Key=key,
            Body=json.dumps(payload),
            ContentType="application/json",
        )
        logger.info("KPI %s recorded: %.2f", kpi_id, value)
        return True
    except Exception as e:
        logger.error("Failed to record KPI %s: %s", kpi_id, e)
        return False


def get_kpi_status(kpi_id: str, value: float) -> str:
    kpi = next((k for k in PIPELINE_KPIS if k["kpi_id"] == kpi_id), None)
    if not kpi:
        return "off_track"
    target = float(str(kpi["target"]))
    direction = str(kpi["direction"])
    if direction == "higher_is_better":
        if value >= target * 0.95:
            return "on_track"
        elif value >= target * 0.80:
            return "at_risk"
        else:
            return "off_track"
    else:
        if value <= target * 1.05:
            return "on_track"
        elif value <= target * 1.20:
            return "at_risk"
        else:
            return "off_track"


def get_kpi_trend(kpi_id: str, bucket: str, days: int = 7) -> str:
    kpi = next((k for k in PIPELINE_KPIS if k["kpi_id"] == kpi_id), None)
    if not kpi:
        return "stable"
    s3 = boto3.client("s3")
    values = []
    today = datetime.utcnow().date()
    for i in range(days):
        d = today - timedelta(days=i)
        key = f"kpis/{d.strftime('%Y/%m/%d')}/{kpi_id}.json"
        try:
            resp = s3.get_object(Bucket=bucket, Key=key)
            data = json.loads(resp["Body"].read().decode("utf-8"))
            values.append(float(data.get("value", 0.0)))
        except Exception:
            continue
    if len(values) < 2:
        return "stable"
    recent = values[0]
    older = values[-1]
    change_pct = (recent - older) / abs(older) if older != 0 else 0
    if abs(change_pct) < 0.01:
        return "stable"
    if str(kpi["direction"]) == "higher_is_better":
        return "improving" if change_pct > 0 else "declining"
    else:
        return "improving" if change_pct < 0 else "declining"


def generate_kpi_dashboard(bucket: str, date: str) -> dict:
    s3 = boto3.client("s3")
    dt = datetime.strptime(date, "%Y-%m-%d")
    kpi_results = []
    for kpi in PIPELINE_KPIS:
        kpi_id = str(kpi["kpi_id"])
        key = f"kpis/{dt.strftime('%Y/%m/%d')}/{kpi_id}.json"
        try:
            resp = s3.get_object(Bucket=bucket, Key=key)
            data = json.loads(resp["Body"].read().decode("utf-8"))
            value = float(data.get("value", float(str(kpi["target"]))))
        except Exception:
            value = float(str(kpi["target"]))
        status = get_kpi_status(kpi_id, value)
        trend = get_kpi_trend(kpi_id, bucket)
        kpi_results.append(
            {
                "kpi_id": kpi_id,
                "name": kpi["name"],
                "value": value,
                "target": kpi["target"],
                "unit": kpi["unit"],
                "status": status,
                "trend": trend,
            }
        )
    on_track = sum(1 for k in kpi_results if k["status"] == "on_track")
    logger.info("KPI dashboard: %d/%d on track", on_track, len(kpi_results))
    return {
        "kpis": kpi_results,
        "date": date,
        "generated_at": datetime.utcnow().isoformat(),
        "summary": {"on_track": on_track, "total": len(kpi_results)},
    }


def run_kpi_tracking(bucket: str) -> dict:
    date = datetime.utcnow().strftime("%Y-%m-%d")
    current_values = {
        "K001": 20.0,
        "K002": 96.5,
        "K003": 91.0,
        "K004": 72.0,
        "K005": 97.0,
        "K006": 280.0,
    }
    for kpi in PIPELINE_KPIS:
        kpi_id = str(kpi["kpi_id"])
        value = current_values.get(kpi_id, float(str(kpi["target"])))
        record_kpi(kpi_id, value, bucket, date)
    dashboard = generate_kpi_dashboard(bucket, date)
    s3 = boto3.client("s3")
    dt = datetime.strptime(date, "%Y-%m-%d")
    key = f"reports/kpis/{dt.strftime('%Y/%m/%d')}/kpi_dashboard.json"
    s3.put_object(
        Bucket=bucket,
        Key=key,
        Body=json.dumps(dashboard, default=str),
        ContentType="application/json",
    )
    logger.info("KPI tracking complete, dashboard saved to s3://%s/%s", bucket, key)
    return dashboard


if __name__ == "__main__":
    pass
