import json
import logging
import os
from datetime import datetime, timezone

import boto3

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

RULES = [
    {
        "rule_id": "R001",
        "name": "High Anomaly Rate",
        "metric": "anomaly_rate_pct",
        "operator": ">",
        "threshold": 20.0,
        "severity": "HIGH",
        "action": "slack",
    },
    {
        "rule_id": "R002",
        "name": "Low Quality Score",
        "metric": "quality_score_pct",
        "operator": "<",
        "threshold": 80.0,
        "severity": "HIGH",
        "action": "slack",
    },
    {
        "rule_id": "R003",
        "name": "Pipeline SLA Breach",
        "metric": "sla_met_pct",
        "operator": "<",
        "threshold": 90.0,
        "severity": "MEDIUM",
        "action": "slack",
    },
    {
        "rule_id": "R004",
        "name": "High Error Rate",
        "metric": "error_rate_pct",
        "operator": ">",
        "threshold": 5.0,
        "severity": "HIGH",
        "action": "slack",
    },
    {
        "rule_id": "R005",
        "name": "Prediction Accuracy Low",
        "metric": "prediction_accuracy_pct",
        "operator": "<",
        "threshold": 70.0,
        "severity": "MEDIUM",
        "action": "log",
    },
]

_OPERATORS = {
    ">": lambda a, b: a > b,
    "<": lambda a, b: a < b,
    ">=": lambda a, b: a >= b,
    "<=": lambda a, b: a <= b,
    "==": lambda a, b: a == b,
}


def evaluate_rule(rule: dict, metrics: dict) -> bool:
    metric_name = rule["metric"]
    operator = rule["operator"]
    threshold = rule["threshold"]
    value = metrics.get(metric_name)
    if value is None:
        logger.info(f"Rule {rule['rule_id']} skipped: metric '{metric_name}' not in metrics")
        return False
    op_func = _OPERATORS.get(operator)
    if op_func is None:
        logger.warning(f"Rule {rule['rule_id']}: unknown operator '{operator}'")
        return False
    triggered = op_func(float(value), float(threshold))
    if triggered:
        logger.info(
            f"Rule {rule['rule_id']} TRIGGERED: {metric_name} {operator} {threshold} "
            f"(actual: {value})"
        )
    else:
        logger.info(f"Rule {rule['rule_id']} passed: {metric_name}={value}")
    return triggered


def evaluate_all_rules(metrics: dict) -> list:
    triggered = []
    rules = load_custom_rules.__wrapped__ if hasattr(load_custom_rules, "__wrapped__") else RULES
    for rule in RULES:
        if evaluate_rule(rule, metrics):
            triggered.append(rule)
    logger.info(f"{len(triggered)} rules triggered out of {len(RULES)}")
    return triggered


def save_rule_results(results: list, bucket: str, date: str) -> bool:
    s3 = boto3.client("s3")
    date_path = date.replace("-", "/")
    s3_key = f"monitoring/alerts/{date_path}/rules.json"
    payload = {
        "date": date,
        "triggered_count": len(results),
        "rules": results,
        "saved_at": datetime.now(timezone.utc).isoformat(),
    }
    try:
        s3.put_object(Bucket=bucket, Key=s3_key, Body=json.dumps(payload))
        logger.info(f"Rule results saved to s3://{bucket}/{s3_key}")
        return True
    except Exception as e:
        logger.error(f"Failed to save rule results: {e}")
        return False


def load_custom_rules(bucket: str) -> list:
    s3 = boto3.client("s3")
    s3_key = "monitoring/rules/custom_rules.json"
    try:
        response = s3.get_object(Bucket=bucket, Key=s3_key)
        custom = json.loads(response["Body"].read())
        combined = RULES + custom
        logger.info(f"Loaded {len(custom)} custom rules, total {len(combined)}")
        return combined
    except Exception:
        logger.info("No custom rules found, using defaults")
        return list(RULES)


def run_rules_engine(metrics: dict, bucket: str) -> dict:
    all_rules = load_custom_rules(bucket)
    triggered = []
    for rule in all_rules:
        if evaluate_rule(rule, metrics):
            triggered.append(rule)
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    save_rule_results(triggered, bucket, date_str)
    result = {"triggered": len(triggered), "rules": triggered}
    logger.info(f"Rules engine complete: {len(triggered)}/{len(all_rules)} rules triggered")
    return result


if __name__ == "__main__":
    pass
