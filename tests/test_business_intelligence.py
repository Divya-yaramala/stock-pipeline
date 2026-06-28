from unittest.mock import MagicMock, patch

from ingestion.business_intelligence import (
    calculate_market_cap_weighted_index,
    calculate_max_drawdown,
    calculate_sector_performance,
    calculate_sharpe_ratio,
    generate_bi_report,
)


def test_calculate_sharpe_ratio_positive():
    returns = [0.01, 0.02, 0.015, 0.018, 0.012, 0.022, 0.016]
    result = calculate_sharpe_ratio(returns, risk_free_rate=0.001)
    assert result > 0


def test_calculate_max_drawdown_negative():
    prices = [100, 110, 90, 95, 105]
    result = calculate_max_drawdown(prices)
    assert result < 0


def test_calculate_sector_performance_structure():
    prices = {
        "AAPL": 0.01,
        "MSFT": 0.02,
        "GOOGL": 0.015,
        "AMZN": -0.005,
        "TSLA": 0.03,
    }
    sectors = {
        "AAPL": "Technology",
        "MSFT": "Technology",
        "GOOGL": "Technology",
        "AMZN": "Consumer Cyclical",
        "TSLA": "Consumer Cyclical",
    }
    result = calculate_sector_performance(prices, sectors)
    assert isinstance(result, dict)
    assert "Technology" in result
    assert "Consumer Cyclical" in result


def test_calculate_market_cap_weighted_index():
    prices = {
        "AAPL": 180.0,
        "MSFT": 380.0,
        "GOOGL": 140.0,
        "AMZN": 185.0,
        "TSLA": 250.0,
    }
    market_caps = {"AAPL": 3000, "MSFT": 2800, "GOOGL": 2000, "AMZN": 1800, "TSLA": 700}
    result = calculate_market_cap_weighted_index(prices, market_caps)
    assert result > 0


def test_generate_bi_report_structure():
    with patch("ingestion.business_intelligence.boto3.client") as mock_client:
        mock_s3 = MagicMock()
        mock_client.return_value = mock_s3
        mock_s3.get_object.side_effect = Exception("NoSuchKey")
        result = generate_bi_report("AAPL", "test-bucket", "2026-06-27")
    assert isinstance(result, dict)
    assert "AAPL" in result
