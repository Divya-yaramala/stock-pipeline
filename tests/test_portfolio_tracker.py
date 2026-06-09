from unittest.mock import MagicMock, patch

from ingestion.portfolio_tracker import (
    calculate_portfolio_returns,
    calculate_portfolio_value,
    load_portfolio,
    save_portfolio_snapshot,
)


def test_calculate_portfolio_value_correct():
    portfolio = {"AAPL": 10}
    prices = {"AAPL": 185.0}
    result = calculate_portfolio_value(portfolio, prices)
    assert result["total_value"] == 1850.0


def test_calculate_portfolio_value_weights():
    portfolio = {"AAPL": 10, "MSFT": 5}
    prices = {"AAPL": 185.0, "MSFT": 380.0}
    result = calculate_portfolio_value(portfolio, prices)
    total_weight = sum(result["weights"].values())
    assert abs(total_weight - 100.0) < 0.01


def test_calculate_portfolio_returns_positive():
    portfolio = {"AAPL": 10}
    current = {"AAPL": 190.0}
    previous = {"AAPL": 185.0}
    result = calculate_portfolio_returns(portfolio, current, previous)
    assert result["daily_return_pct"] > 0


def test_save_portfolio_snapshot_success():
    metrics = {"total_value": 1850.0, "top_holding": "AAPL", "ticker_returns": {}}
    with patch("ingestion.portfolio_tracker.boto3.client") as mock_client:
        mock_s3 = MagicMock()
        mock_client.return_value = mock_s3
        result = save_portfolio_snapshot(metrics, "test-bucket", "2026-06-09")
    assert result is True
    mock_s3.put_object.assert_called_once()


def test_load_portfolio_default():
    with patch("ingestion.portfolio_tracker.boto3.client") as mock_client:
        mock_s3 = MagicMock()
        mock_client.return_value = mock_s3
        mock_s3.get_object.side_effect = Exception("NoSuchKey")
        result = load_portfolio("test-bucket")
    assert isinstance(result, dict)
    assert len(result) > 0
    assert "AAPL" in result
