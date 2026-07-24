from unittest.mock import MagicMock, patch

import pytest  # noqa: F401

from ingestion.sector_analyzer import (
    calculate_sector_returns,
    calculate_sector_rotation,
    compare_to_benchmark,
    identify_sector_leaders,
    run_sector_analysis,
)


def test_calculate_sector_returns_tech():
    ticker_returns = {"AAPL": 0.05, "MSFT": 0.03}
    result = calculate_sector_returns(ticker_returns)
    assert "Technology" in result
    assert abs(result["Technology"] - 0.04) < 0.001


def test_identify_sector_leaders_structure():
    ticker_returns = {"AAPL": 0.05, "MSFT": 0.03, "GOOGL": 0.04, "AMZN": 0.02, "TSLA": 0.06}
    result = identify_sector_leaders(ticker_returns)
    assert isinstance(result, dict)
    assert "Technology" in result
    assert "Consumer Discretionary" in result


def test_calculate_sector_rotation_structure():
    current = {"AAPL": 0.05, "MSFT": 0.03, "GOOGL": 0.04, "AMZN": 0.02, "TSLA": 0.01}
    previous = {"AAPL": 0.02, "MSFT": 0.02, "GOOGL": 0.06, "AMZN": 0.03, "TSLA": 0.04}
    result = calculate_sector_rotation(current, previous)
    assert "gaining" in result
    assert "losing" in result
    assert "stable" in result


def test_compare_to_benchmark_alpha():
    sector_returns = {"Technology": 0.20}
    result = compare_to_benchmark(sector_returns)
    assert "Technology" in result
    assert abs(result["Technology"]["alpha"] - 0.05) < 0.001


def test_run_sector_analysis_structure():
    ticker_prices = {
        "AAPL": [185.0 + i * 0.1 for i in range(10)],
        "MSFT": [415.0 + i * 0.2 for i in range(10)],
        "GOOGL": [175.0 + i * 0.15 for i in range(10)],
        "AMZN": [195.0 + i * 0.05 for i in range(10)],
        "TSLA": [250.0 + i * 0.3 for i in range(10)],
    }
    with patch("ingestion.sector_analyzer.boto3.client") as mock_client:
        mock_s3 = MagicMock()
        mock_client.return_value = mock_s3
        result = run_sector_analysis(ticker_prices, "test-bucket")

    assert "sector_returns" in result
    assert "sector_leaders" in result
    assert "benchmark_comparison" in result
