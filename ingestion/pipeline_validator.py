import datetime
import json
import logging
from typing import Any, Dict, List

import boto3

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

VALIDATION_RULES: List[Dict[str, Any]] = [
    {
        "rule_id": "V001",
        "name": "schema_validation",
        "category": "structural",
        "description": "All required fields present and correct types",
    },
    {
        "rule_id": "V002",
        "name": "range_validation",
        "category": "statistical",
        "description": "Values within expected statistical ranges",
    },
    {
        "rule_id": "V003",
        "name": "referential_integrity",
        "category": "relational",
        "description": "Ticker references valid and consistent",
    },
    {
        "rule_id": "V004",
        "name": "temporal_consistency",
        "category": "temporal",
        "description": "Dates sequential and no future dates",
    },
    {
        "rule_id": "V005",
        "name": "business_rules",
        "category": "business",
        "description": "High > Low, Close between High and Low",
    },
    {
        "rule_id": "V006",
        "name": "completeness_check",
        "category": "completeness",
        "description": "No null values in required fields",
    },
    {
        "rule_id": "V007",
        "name": "uniqueness_check",
        "category": "uniqueness",
        "description": "No duplicate ticker+date combinations",
    },
    {
        "rule_id": "V008",
        "name": "statistical_outliers",
        "category": "statistical",
        "description": "No extreme outliers beyond 5 standard deviations",
    },
]

REQUIRED_FIELDS: List[str] = [
    "ticker",
    "trade_date",
    "open_price",
    "high_price",
    "low_price",
    "close_price",
    "volume",
]

VALID_TICKERS: List[str] = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"]


def validate_schema(data: Dict[str, Any], required_fields: List[str]) -> Dict[str, Any]:
    missing_fields = [f for f in required_fields if f not in data]
    passed = len(missing_fields) == 0
    result: Dict[str, Any] = {
        "passed": passed,
        "missing_fields": missing_fields,
        "rule_id": "V001",
    }
    logger.info(
        "Schema validation %s: missing=%s", "passed" if passed else "failed", missing_fields
    )
    return result


def validate_ranges(
    data: Dict[str, Any], field_ranges: Dict[str, Dict[str, float]]
) -> Dict[str, Any]:
    violations: List[str] = []
    for field, bounds in field_ranges.items():
        if field in data and data[field] is not None:
            val = float(str(data[field]))
            min_val = float(str(bounds.get("min", float("-inf"))))
            max_val = float(str(bounds.get("max", float("inf"))))
            if val < min_val or val > max_val:
                violations.append(f"{field}={val} outside [{min_val}, {max_val}]")
    passed = len(violations) == 0
    result: Dict[str, Any] = {"passed": passed, "violations": violations, "rule_id": "V002"}
    logger.info(
        "Range validation %s: violations=%d", "passed" if passed else "failed", len(violations)
    )
    return result


def validate_business_rules(data: Dict[str, Any]) -> Dict[str, Any]:
    violations: List[str] = []
    high = float(str(data.get("high_price", 0)))
    low = float(str(data.get("low_price", 0)))
    close = float(str(data.get("close_price", 0)))
    open_price = float(str(data.get("open_price", 0)))
    volume = float(str(data.get("volume", 0)))

    if high < low:
        violations.append(f"high_price ({high}) < low_price ({low})")
    if close > high or close < low:
        violations.append(f"close_price ({close}) not between low ({low}) and high ({high})")
    if volume <= 0:
        violations.append(f"volume ({volume}) must be > 0")
    if open_price <= 0:
        violations.append(f"open_price ({open_price}) must be > 0")

    passed = len(violations) == 0
    result: Dict[str, Any] = {"passed": passed, "violations": violations, "rule_id": "V005"}
    logger.info(
        "Business rules %s: violations=%d", "passed" if passed else "failed", len(violations)
    )
    return result


def validate_temporal_consistency(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    issues: List[str] = []
    today = datetime.date.today()
    dates: List[datetime.date] = []

    for r in records:
        try:
            d = datetime.date.fromisoformat(str(r.get("trade_date", "")))
            dates.append(d)
            if d > today:
                issues.append(f"Future date detected: {d}")
        except ValueError:
            issues.append(f"Invalid date format: {r.get('trade_date')}")

    for i in range(1, len(dates)):
        if dates[i] < dates[i - 1]:
            issues.append(f"Out-of-order dates: {dates[i - 1]} -> {dates[i]}")

    passed = len(issues) == 0
    result: Dict[str, Any] = {"passed": passed, "issues": issues, "rule_id": "V004"}
    logger.info("Temporal consistency %s: issues=%d", "passed" if passed else "failed", len(issues))
    return result


def run_validation_suite(records: List[Dict[str, Any]], ticker: str) -> Dict[str, Any]:
    results: List[Dict[str, Any]] = []
    passed_count = 0

    # V001 schema validation
    r1 = validate_schema(records[0] if records else {}, REQUIRED_FIELDS)
    results.append(r1)
    if r1["passed"]:
        passed_count += 1

    # V002 range validation
    price_ranges: Dict[str, Dict[str, float]] = {
        "open_price": {"min": 0.01, "max": 100000.0},
        "high_price": {"min": 0.01, "max": 100000.0},
        "low_price": {"min": 0.01, "max": 100000.0},
        "close_price": {"min": 0.01, "max": 100000.0},
        "volume": {"min": 1.0, "max": 1e12},
    }
    r2 = validate_ranges(records[0] if records else {}, price_ranges)
    results.append(r2)
    if r2["passed"]:
        passed_count += 1

    # V003 referential integrity
    invalid_tickers = [
        str(r.get("ticker", "")) for r in records if str(r.get("ticker", "")) not in VALID_TICKERS
    ]
    r3: Dict[str, Any] = {
        "passed": len(invalid_tickers) == 0,
        "violations": [f"Invalid ticker: {t}" for t in invalid_tickers],
        "rule_id": "V003",
    }
    results.append(r3)
    if r3["passed"]:
        passed_count += 1

    # V004 temporal consistency
    r4 = validate_temporal_consistency(records)
    results.append(r4)
    if r4["passed"]:
        passed_count += 1

    # V005 business rules
    biz_violations: List[str] = []
    for rec in records:
        br = validate_business_rules(rec)
        if not br["passed"]:
            biz_violations.extend(br["violations"])
    r5: Dict[str, Any] = {
        "passed": len(biz_violations) == 0,
        "violations": biz_violations,
        "rule_id": "V005",
    }
    results.append(r5)
    if r5["passed"]:
        passed_count += 1

    # V006 completeness check
    null_issues: List[str] = []
    for rec in records:
        for field in REQUIRED_FIELDS:
            if rec.get(field) is None:
                null_issues.append(f"Null value in {field}")
    r6: Dict[str, Any] = {
        "passed": len(null_issues) == 0,
        "violations": null_issues,
        "rule_id": "V006",
    }
    results.append(r6)
    if r6["passed"]:
        passed_count += 1

    # V007 uniqueness check
    seen: set = set()
    duplicates: List[str] = []
    for rec in records:
        key = f"{rec.get('ticker')}_{rec.get('trade_date')}"
        if key in seen:
            duplicates.append(f"Duplicate: {key}")
        seen.add(key)
    r7: Dict[str, Any] = {
        "passed": len(duplicates) == 0,
        "violations": duplicates,
        "rule_id": "V007",
    }
    results.append(r7)
    if r7["passed"]:
        passed_count += 1

    # V008 statistical outliers (5 standard deviations)
    outlier_issues: List[str] = []
    for price_field in ["open_price", "high_price", "low_price", "close_price"]:
        values = [float(str(r.get(price_field, 0))) for r in records if r.get(price_field)]
        if len(values) > 2:
            mean = sum(values) / len(values)
            variance = sum((v - mean) ** 2 for v in values) / len(values)
            std = variance**0.5
            if std > 0:
                for v in values:
                    if abs(v - mean) > 5 * std:
                        outlier_issues.append(f"{price_field}={v} is >5std from mean")
    r8: Dict[str, Any] = {
        "passed": len(outlier_issues) == 0,
        "violations": outlier_issues,
        "rule_id": "V008",
    }
    results.append(r8)
    if r8["passed"]:
        passed_count += 1

    total_rules = 8
    failed_count = total_rules - passed_count
    pass_rate = round((passed_count / total_rules) * 100, 1)

    summary: Dict[str, Any] = {
        "ticker": ticker,
        "total_rules": total_rules,
        "passed": passed_count,
        "failed": failed_count,
        "pass_rate_pct": pass_rate,
        "results": results,
    }
    logger.info(
        "Validation suite for %s: %d/%d passed (%.1f%%)",
        ticker,
        passed_count,
        total_rules,
        pass_rate,
    )
    return summary


def save_validation_report(report: Dict[str, Any], ticker: str, bucket: str, date: str) -> bool:
    try:
        s3 = boto3.client("s3")
        parts = date.split("-")
        year, month, day = parts[0], parts[1], parts[2]
        key = f"validation/{year}/{month}/{day}/{ticker}.json"
        s3.put_object(Bucket=bucket, Key=key, Body=json.dumps(report).encode())
        logger.info("Saved validation report: s3://%s/%s", bucket, key)
        return True
    except Exception as e:
        logger.error("Failed to save validation report: %s", e)
        return False


if __name__ == "__main__":
    pass
