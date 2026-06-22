from unittest.mock import MagicMock, patch

from ingestion.test_framework import (
    calculate_quality_trend,
    run_test,
    run_test_suite,
    save_test_results,
)


def test_run_test_suite_structure():
    mock_s3 = MagicMock()
    mock_s3.list_objects_v2.return_value = {
        "Contents": [{"Key": "raw/stocks/2026/06/22/AAPL.json"}]
    }
    with patch("ingestion.test_framework.boto3.client", return_value=mock_s3):
        result = run_test_suite("test-bucket", "2026-06-22")
    assert "total" in result
    assert "passed" in result
    assert "failed" in result
    assert result["total"] == 8


def test_run_test_returns_correct_keys():
    mock_s3 = MagicMock()
    mock_s3.list_objects_v2.return_value = {"Contents": [{"Key": "some/key"}]}
    with patch("ingestion.test_framework.boto3.client", return_value=mock_s3):
        result = run_test("T001", "test-bucket", "2026-06-22")
    assert "test_id" in result
    assert "status" in result
    assert "duration_ms" in result
    assert result["test_id"] == "T001"


def test_save_test_results_success():
    mock_s3 = MagicMock()
    with patch("ingestion.test_framework.boto3.client", return_value=mock_s3):
        result = save_test_results(
            {"total": 8, "passed": 8, "failed": 0, "pass_rate_pct": 100.0, "results": []},
            "test-bucket",
            "2026-06-22",
        )
    assert result is True
    mock_s3.put_object.assert_called_once()


def test_calculate_quality_trend_improving():
    history = [
        {"pass_rate_pct": 60.0},
        {"pass_rate_pct": 65.0},
        {"pass_rate_pct": 70.0},
        {"pass_rate_pct": 80.0},
        {"pass_rate_pct": 85.0},
        {"pass_rate_pct": 90.0},
    ]
    result = calculate_quality_trend(history)
    assert result["trend"] == "improving"


def test_calculate_quality_trend_declining():
    history = [
        {"pass_rate_pct": 90.0},
        {"pass_rate_pct": 85.0},
        {"pass_rate_pct": 80.0},
        {"pass_rate_pct": 70.0},
        {"pass_rate_pct": 65.0},
        {"pass_rate_pct": 60.0},
    ]
    result = calculate_quality_trend(history)
    assert result["trend"] == "declining"
