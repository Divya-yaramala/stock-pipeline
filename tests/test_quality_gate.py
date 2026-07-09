from typing import Any, Dict
from unittest.mock import MagicMock, patch

from ingestion.quality_gate import evaluate_gate, run_quality_gates, save_gate_results

GOOD_METRICS: Dict[str, Any] = {
    "hours_since_update": 10.0,
    "completeness_pct": 95.0,
    "quality_score": 88.0,
    "anomaly_rate_pct": 5.0,
    "prediction_accuracy_pct": 75.0,
}


def test_evaluate_gate_passes():
    gate: Dict[str, Any] = {
        "gate_id": "T001",
        "name": "test_gate",
        "threshold": 80.0,
        "metric": "completeness_pct",
        "operator": ">",
        "action": "block",
    }
    result = evaluate_gate(gate, {"completeness_pct": 90.0})
    assert result["passed"] is True


def test_evaluate_gate_fails():
    gate: Dict[str, Any] = {
        "gate_id": "T002",
        "name": "test_gate",
        "threshold": 80.0,
        "metric": "completeness_pct",
        "operator": ">",
        "action": "block",
    }
    result = evaluate_gate(gate, {"completeness_pct": 70.0})
    assert result["passed"] is False


def test_run_quality_gates_all_pass():
    summary = run_quality_gates(GOOD_METRICS, "AAPL")
    assert summary["blocked"] is False
    assert summary["passed"] == 5


def test_run_quality_gates_blocked():
    bad_metrics: Dict[str, Any] = {
        **GOOD_METRICS,
        "hours_since_update": 30.0,  # fails G001 (block gate)
    }
    summary = run_quality_gates(bad_metrics, "AAPL")
    assert summary["blocked"] is True


def test_save_gate_results_success():
    mock_s3 = MagicMock()
    with patch("ingestion.quality_gate.boto3.client", return_value=mock_s3):
        result = save_gate_results({"ticker": "AAPL"}, "AAPL", "test-bucket", "2026-07-09")
    assert result is True
    mock_s3.put_object.assert_called_once()
