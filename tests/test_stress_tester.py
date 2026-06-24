from unittest.mock import MagicMock, patch

from ingestion.stress_tester import (
    run_full_stress_test,
    stress_test_api_calls,
    stress_test_data_processing,
    stress_test_s3_uploads,
)


def test_stress_test_s3_uploads_structure():
    mock_s3 = MagicMock()
    mock_s3.put_object.return_value = {}
    with patch("ingestion.stress_tester.boto3.client", return_value=mock_s3):
        result = stress_test_s3_uploads("test-bucket", num_files=5, num_workers=2)
    assert "total_time" in result
    assert "success_rate" in result
    assert result["success_rate"] == 1.0


def test_stress_test_data_processing_structure():
    result = stress_test_data_processing(num_records=50)
    assert "records_per_second" in result
    assert result["num_records"] == 50


def test_stress_test_api_calls_structure():
    mock_ticker = MagicMock()
    mock_ticker.history.return_value = {"Close": [150.0]}
    with patch("ingestion.stress_tester.yf.Ticker", return_value=mock_ticker):
        result = stress_test_api_calls(num_calls=5, num_workers=2)
    assert "calls_per_second" in result
    assert "avg_latency_ms" in result


def test_run_full_stress_test_has_all_results():
    s3_mock = {"total_time": 1.0, "files_per_second": 10.0, "success_rate": 1.0, "num_files": 10}
    api_mock = {
        "total_time": 1.0,
        "calls_per_second": 5.0,
        "success_rate": 1.0,
        "avg_latency_ms": 200.0,
        "num_calls": 5,
    }
    proc_mock = {
        "records_per_second": 5000.0,
        "validation_time": 0.01,
        "quality_score": 100.0,
        "num_records": 50,
        "valid_count": 50,
    }
    mock_s3_client = MagicMock()
    mock_s3_client.put_object.return_value = {}
    with patch("ingestion.stress_tester.stress_test_s3_uploads", return_value=s3_mock), patch(
        "ingestion.stress_tester.stress_test_api_calls", return_value=api_mock
    ), patch("ingestion.stress_tester.stress_test_data_processing", return_value=proc_mock), patch(
        "ingestion.stress_tester.boto3.client", return_value=mock_s3_client
    ):
        result = run_full_stress_test("test-bucket")
    assert "s3" in result
    assert "api" in result
    assert "processing" in result


def test_stress_test_data_processing_quality_score():
    result = stress_test_data_processing(num_records=100)
    assert 0 <= result["quality_score"] <= 100
