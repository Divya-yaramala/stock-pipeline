from unittest.mock import MagicMock, patch

from ingestion.model_monitor import (
    calculate_model_metrics,
    detect_performance_degradation,
    save_monitoring_report,
)


def test_calculate_model_metrics_structure():
    predictions = [100.0, 200.0, 300.0]
    actuals = [110.0, 190.0, 310.0]
    result = calculate_model_metrics(predictions, actuals)
    assert "MAE" in result
    assert "RMSE" in result
    assert "MAPE" in result
    assert "R2" in result


def test_calculate_model_metrics_perfect():
    values = [100.0, 200.0, 300.0]
    result = calculate_model_metrics(values, values)
    assert result["MAE"] == 0.0
    assert result["R2"] == 1.0


def test_detect_performance_degradation_critical():
    current = {"MAE": 5.0, "RMSE": 12.0, "MAPE": 4.0, "R2": 0.7}
    baseline = {"MAE": 5.0, "RMSE": 8.0, "MAPE": 3.0, "R2": 0.85}
    result = detect_performance_degradation(current, baseline)
    assert result["degraded"] is True
    assert result["severity"] == "critical"


def test_detect_performance_degradation_none():
    metrics = {"MAE": 5.0, "RMSE": 8.0, "MAPE": 3.0, "R2": 0.85}
    result = detect_performance_degradation(metrics, metrics)
    assert result["degraded"] is False


def test_save_monitoring_report_success():
    mock_s3 = MagicMock()
    with patch("ingestion.model_monitor.boto3.client", return_value=mock_s3):
        result = save_monitoring_report(
            "AAPL",
            {"MAE": 5.0, "RMSE": 8.0, "MAPE": 3.0, "R2": 0.85},
            {"degraded": False, "severity": "none", "metrics_comparison": {}},
            "test-bucket",
            "2024/01/15",
        )
    assert result is True
