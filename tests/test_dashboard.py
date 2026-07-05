from unittest.mock import MagicMock, patch

import pandas as pd

from dashboard.app import fetch_live_price, load_anomalies, load_predictions, load_stock_prices


def test_load_stock_prices_empty_on_no_db():
    result = load_stock_prices(None, "AAPL", 30)
    assert isinstance(result, pd.DataFrame)
    assert result.empty


def test_fetch_live_price_structure():
    mock_hist = pd.DataFrame(
        {"Close": [180.0, 182.5], "Volume": [1000000, 1100000]},
    )
    mock_ticker = MagicMock()
    mock_ticker.history.return_value = mock_hist
    with patch("dashboard.app.yf.Ticker", return_value=mock_ticker):
        result = fetch_live_price("AAPL")
    assert result is not None
    assert "price" in result
    assert result["price"] == 182.5


def test_fetch_live_price_failure():
    mock_ticker = MagicMock()
    mock_ticker.history.side_effect = Exception("network error")
    with patch("dashboard.app.yf.Ticker", return_value=mock_ticker):
        result = fetch_live_price("AAPL")
    assert result is None


def test_load_anomalies_columns():
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.fetchall.return_value = [
        ("2024-01-15", 185.0, True, -0.42),
    ]
    mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
    mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
    result = load_anomalies(mock_conn, "AAPL", 30)
    assert isinstance(result, pd.DataFrame)
    assert "is_anomaly" in result.columns


def test_load_predictions_structure():
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.fetchall.return_value = [
        ("2024-01-16", 186.0, 182.0, 190.0),
        ("2024-01-17", 187.5, 183.0, 192.0),
    ]
    mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
    mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
    result = load_predictions(mock_conn, "AAPL")
    assert isinstance(result, pd.DataFrame)
    assert "predicted_price" in result.columns
