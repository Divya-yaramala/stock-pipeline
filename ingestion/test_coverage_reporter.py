"""Test coverage reporter — runs pytest-cov, tracks trends, saves reports to S3."""

import json
import logging
import os
import subprocess
from datetime import datetime, timedelta
from typing import Any, Dict, List

import boto3

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def run_coverage_report(
    test_dirs: List[str],
    source_dir: str = "ingestion",
) -> Dict[str, Any]:
    """Run pytest with coverage and return parsed coverage data."""
    cmd = [
        "python",
        "-m",
        "pytest",
        f"--cov={source_dir}",
        "--cov-report=json",
        "-q",
    ] + test_dirs

    try:
        subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    except Exception as exc:
        logger.warning("Coverage run error: %s", exc)

    coverage_path = "coverage.json"
    if not os.path.exists(coverage_path):
        logger.warning("coverage.json not found — returning empty coverage data")
        return {"total_coverage_pct": 0.0, "files": {}, "missing_lines": 0}

    with open(coverage_path, "r") as fh:
        raw: Dict[str, Any] = json.load(fh)

    totals: Dict[str, Any] = raw.get("totals", {})
    total_pct: float = float(str(totals.get("percent_covered", 0.0)))
    missing: int = int(str(totals.get("missing_lines", 0)))

    files: Dict[str, Any] = {}
    for path, data in raw.get("files", {}).items():
        summary: Dict[str, Any] = data.get("summary", {})
        files[path] = {
            "coverage_pct": float(str(summary.get("percent_covered", 0.0))),
            "missing_lines": int(str(summary.get("missing_lines", 0))),
        }

    result: Dict[str, Any] = {
        "total_coverage_pct": total_pct,
        "files": files,
        "missing_lines": missing,
    }
    logger.info("Coverage: %.1f%% total, %d missing lines", total_pct, missing)
    return result


def get_low_coverage_files(
    coverage_data: Dict[str, Any],
    threshold_pct: float = 80.0,
) -> List[Dict[str, Any]]:
    """Return files with coverage below threshold_pct."""
    low: List[Dict[str, Any]] = []
    for filepath, info in coverage_data.get("files", {}).items():
        pct: float = float(str(info.get("coverage_pct", 0.0)))
        if pct < threshold_pct:
            low.append(
                {
                    "file": str(filepath),
                    "coverage_pct": pct,
                    "missing_lines": int(str(info.get("missing_lines", 0))),
                }
            )
    low.sort(key=lambda x: float(str(x["coverage_pct"])))
    logger.info("Found %d files below %.0f%% coverage threshold", len(low), threshold_pct)
    return low


def generate_coverage_report_html(coverage_data: Dict[str, Any]) -> str:
    """Generate an HTML coverage summary string."""
    total_pct: float = float(str(coverage_data.get("total_coverage_pct", 0.0)))
    low_files = get_low_coverage_files(coverage_data, threshold_pct=80.0)
    all_files = list(coverage_data.get("files", {}).items())
    all_files.sort(key=lambda kv: float(str(kv[1].get("coverage_pct", 100.0))))
    top5_low = all_files[:5]

    rows_low = "".join(
        f"<tr><td>{f['file']}</td><td>{f['coverage_pct']:.1f}%</td>"
        f"<td>{f['missing_lines']}</td></tr>"
        for f in low_files
    )
    rows_top5 = "".join(
        f"<tr><td>{path}</td><td>{info.get('coverage_pct', 0):.1f}%</td></tr>"
        for path, info in top5_low
    )

    html = f"""<!DOCTYPE html>
<html>
<head><title>Coverage Report</title></head>
<body>
<h1>Coverage Report</h1>
<p>Total coverage: <strong>{total_pct:.1f}%</strong></p>
<h2>Files Below 80% Threshold ({len(low_files)})</h2>
<table border="1">
<tr><th>File</th><th>Coverage</th><th>Missing Lines</th></tr>
{rows_low}
</table>
<h2>Top 5 Lowest Coverage</h2>
<table border="1">
<tr><th>File</th><th>Coverage</th></tr>
{rows_top5}
</table>
</body>
</html>"""
    return html


def save_coverage_report(
    coverage_data: Dict[str, Any],
    bucket: str,
    date: str,
) -> bool:
    """Save coverage report JSON to S3."""
    s3 = boto3.client("s3")
    key = f"reports/coverage/{date}/coverage.json"
    try:
        s3.put_object(
            Bucket=bucket,
            Key=key,
            Body=json.dumps(coverage_data, indent=2),
            ContentType="application/json",
        )
        logger.info("Coverage report saved to s3://%s/%s", bucket, key)
        return True
    except Exception as exc:
        logger.error("Failed to save coverage report: %s", exc)
        return False


def compare_coverage_trend(
    bucket: str,
    days: int = 7,
) -> Dict[str, Any]:
    """Load last N days of coverage reports and return trend analysis."""
    s3 = boto3.client("s3")
    daily: List[Dict[str, Any]] = []

    for i in range(days):
        date = (datetime.utcnow() - timedelta(days=i)).strftime("%Y/%m/%d")
        key = f"reports/coverage/{date}/coverage.json"
        try:
            obj = s3.get_object(Bucket=bucket, Key=key)
            data: Dict[str, Any] = json.loads(obj["Body"].read().decode("utf-8"))
            daily.append(
                {
                    "date": date,
                    "coverage_pct": float(str(data.get("total_coverage_pct", 0.0))),
                }
            )
        except Exception:
            pass

    if len(daily) < 2:
        trend = "insufficient_data"
        avg_coverage = float(str(daily[0]["coverage_pct"])) if daily else 0.0
    else:
        first_pct: float = float(str(daily[-1]["coverage_pct"]))
        last_pct: float = float(str(daily[0]["coverage_pct"]))
        if last_pct > first_pct + 1.0:
            trend = "improving"
        elif last_pct < first_pct - 1.0:
            trend = "declining"
        else:
            trend = "stable"
        avg_coverage = sum(float(str(d["coverage_pct"])) for d in daily) / len(daily)

    result: Dict[str, Any] = {
        "trend": trend,
        "avg_coverage": round(avg_coverage, 1),
        "daily": daily,
    }
    logger.info("Coverage trend: %s (avg %.1f%%)", trend, avg_coverage)
    return result


def run_coverage_check(bucket: str) -> Dict[str, Any]:
    """Run coverage, save report, and return summary."""
    today = datetime.utcnow().strftime("%Y/%m/%d")
    coverage_data = run_coverage_report(["tests/"])
    low_files = get_low_coverage_files(coverage_data)
    save_coverage_report(coverage_data, bucket, today)

    total_pct: float = float(str(coverage_data.get("total_coverage_pct", 0.0)))
    result: Dict[str, Any] = {
        "total_coverage_pct": total_pct,
        "low_coverage_files": len(low_files),
        "missing_lines": int(str(coverage_data.get("missing_lines", 0))),
        "report_date": today,
    }
    logger.info("Coverage Check Complete: %.1f%% coverage", total_pct)
    return result


if __name__ == "__main__":
    pass
