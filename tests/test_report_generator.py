import json
from io import BytesIO
from unittest.mock import MagicMock, patch

from ingestion.report_generator import (
    generate_html_report,
    load_daily_metrics,
    save_report_to_s3,
)


def _sample_metrics():
    return {
        "quality": {
            "quality_score_pct": 95.0,
            "passed_tickers": 5,
            "total_tickers": 5,
            "failed_checks": [],
        },
        "sla": {
            "slas": {
                "fetch": {"met": True, "actual": 2.5, "threshold": 30},
            }
        },
        "monitoring": {
            "total_runs": 5,
            "success_rate_pct": 100.0,
            "slowest_step": "fetch",
            "fastest_step": "validate",
            "avg_duration_seconds": 3.2,
        },
    }


def test_generate_html_report_structure():
    html = generate_html_report(_sample_metrics(), "2026-06-08")
    assert "Daily Pipeline Report" in html
    assert "2026-06-08" in html


def test_generate_html_report_has_quality_score():
    html = generate_html_report(_sample_metrics(), "2026-06-08")
    assert "95.0" in html


def test_save_report_to_s3_success():
    with patch("ingestion.report_generator.boto3.client") as mock_client:
        mock_s3 = MagicMock()
        mock_client.return_value = mock_s3
        result = save_report_to_s3("<html></html>", "test-bucket", "2026-06-08")
    assert isinstance(result, str)
    assert "reports/daily/" in result


def test_load_daily_metrics_structure():
    quality = {"quality_score_pct": 95.0, "passed_tickers": 5, "total_tickers": 5}
    sla = {"slas": {"fetch": {"met": True, "actual": 2.5, "threshold": 30}}}
    monitoring = {"total_runs": 5, "success_rate_pct": 100.0}

    with patch("ingestion.report_generator.boto3.client") as mock_client:
        mock_s3 = MagicMock()
        mock_client.return_value = mock_s3
        mock_s3.get_object.side_effect = [
            {"Body": BytesIO(json.dumps(quality).encode("utf-8"))},
            {"Body": BytesIO(json.dumps(sla).encode("utf-8"))},
            {"Body": BytesIO(json.dumps(monitoring).encode("utf-8"))},
        ]
        result = load_daily_metrics("test-bucket", "2026-06-08")

    assert isinstance(result, dict)
    assert "quality" in result


def test_load_daily_metrics_missing_file():
    quality = {"quality_score_pct": 80.0, "passed_tickers": 4, "total_tickers": 5}

    with patch("ingestion.report_generator.boto3.client") as mock_client:
        mock_s3 = MagicMock()
        mock_client.return_value = mock_s3
        mock_s3.get_object.side_effect = [
            {"Body": BytesIO(json.dumps(quality).encode("utf-8"))},
            Exception("NoSuchKey"),
            Exception("NoSuchKey"),
        ]
        result = load_daily_metrics("test-bucket", "2026-06-08")

    assert isinstance(result, dict)
    assert "quality" in result
