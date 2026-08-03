from unittest.mock import MagicMock, patch

from ingestion.contract_enforcer import (
    calculate_contract_health,
    enforce_contract,
    get_contract_violation_history,
    log_contract_violation,
)


def test_enforce_contract_no_violations():
    valid_data = {
        "ticker": "AAPL",
        "trade_date": "2026-07-29",
        "open_price": 185.0,
        "high_price": 190.0,
        "low_price": 183.0,
        "close_price": 188.0,
        "volume": 1000000,
    }
    with patch("ingestion.contract_enforcer.boto3.client") as mock_boto:
        mock_s3 = MagicMock()
        mock_boto.return_value = mock_s3
        mock_s3.get_object.side_effect = Exception("not found")
        result = enforce_contract(valid_data, "C001", "test-bucket")
    assert result["blocked"] is False
    assert result["violations"] == []


def test_log_contract_violation_success():
    with patch("ingestion.contract_enforcer.boto3.client") as mock_boto:
        mock_s3 = MagicMock()
        mock_boto.return_value = mock_s3
        result = log_contract_violation("C001", ["Missing field"], "AAPL", "test-bucket")
    assert result is True
    mock_s3.put_object.assert_called_once()


def test_get_contract_violation_history_returns_list():
    with patch("ingestion.contract_enforcer.boto3.client") as mock_boto:
        mock_s3 = MagicMock()
        mock_boto.return_value = mock_s3
        mock_s3.get_paginator.return_value.paginate.return_value = [{"Contents": []}]
        result = get_contract_violation_history("C001", "test-bucket", days=3)
    assert isinstance(result, list)


def test_calculate_contract_health_perfect():
    with patch("ingestion.contract_enforcer.get_contract_violation_history") as mock_hist:
        mock_hist.return_value = []
        health = calculate_contract_health("C001", "test-bucket", days=7)
    assert health["health_score"] == 100.0
    assert health["violation_rate_pct"] == 0.0


def test_calculate_contract_health_degraded():
    with patch("ingestion.contract_enforcer.get_contract_violation_history") as mock_hist:
        mock_hist.return_value = [{"violations": ["Missing field"]}]
        health = calculate_contract_health("C001", "test-bucket", days=2)
    assert health["health_score"] == 50.0
    assert health["violation_rate_pct"] == 50.0
