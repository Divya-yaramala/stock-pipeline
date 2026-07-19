"""Tests for ingestion/test_coverage_reporter.py."""

import json
from typing import Any, Dict
from unittest.mock import MagicMock, patch

from ingestion.test_coverage_reporter import (
    compare_coverage_trend,
    generate_coverage_report_html,
    get_low_coverage_files,
    save_coverage_report,
)

_SAMPLE_COVERAGE: Dict[str, Any] = {
    "total_coverage_pct": 82.0,
    "files": {
        "ingestion/fetch_stocks.py": {"coverage_pct": 60.0, "missing_lines": 10},
        "ingestion/anomaly_detector.py": {"coverage_pct": 90.0, "missing_lines": 2},
        "ingestion/predictor.py": {"coverage_pct": 85.0, "missing_lines": 3},
    },
    "missing_lines": 15,
}


def test_get_low_coverage_files_finds_low() -> None:
    low = get_low_coverage_files(_SAMPLE_COVERAGE, threshold_pct=80.0)
    assert len(low) == 1
    assert low[0]["file"] == "ingestion/fetch_stocks.py"
    assert low[0]["coverage_pct"] == 60.0


def test_get_low_coverage_files_none() -> None:
    all_high: Dict[str, Any] = {
        "total_coverage_pct": 95.0,
        "files": {
            "ingestion/a.py": {"coverage_pct": 90.0, "missing_lines": 1},
            "ingestion/b.py": {"coverage_pct": 85.0, "missing_lines": 2},
        },
        "missing_lines": 3,
    }
    low = get_low_coverage_files(all_high, threshold_pct=80.0)
    assert low == []


def test_generate_coverage_report_html_structure() -> None:
    html = generate_coverage_report_html(_SAMPLE_COVERAGE)
    assert "coverage" in html.lower()
    assert "82.0%" in html
    assert "fetch_stocks.py" in html


def test_save_coverage_report_success() -> None:
    mock_client = MagicMock()
    with patch("ingestion.test_coverage_reporter.boto3.client", return_value=mock_client):
        result = save_coverage_report(_SAMPLE_COVERAGE, "bucket", "2026/01/01")
    assert result is True
    mock_client.put_object.assert_called_once()


def test_compare_coverage_trend_structure() -> None:
    mock_client = MagicMock()
    day_report = json.dumps({"total_coverage_pct": 85.0}).encode("utf-8")

    body_mock = MagicMock()
    body_mock.read.return_value = day_report
    mock_client.get_object.return_value = {"Body": body_mock}

    with patch("ingestion.test_coverage_reporter.boto3.client", return_value=mock_client):
        trend = compare_coverage_trend("bucket", days=7)

    assert "trend" in trend
    assert "avg_coverage" in trend
    assert "daily" in trend
    assert isinstance(trend["daily"], list)
