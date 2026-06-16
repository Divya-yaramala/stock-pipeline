from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from api.websocket_server import app, get_live_price

client = TestClient(app)


def test_ws_status_endpoint():
    response = client.get("/ws/status")
    assert response.status_code == 200
    data = response.json()
    assert "websocket_url" in data
    assert "status" in data
    assert data["status"] == "running"


@pytest.mark.anyio
async def test_get_live_price_success():
    mock_info = MagicMock()
    mock_info.last_price = 173.50
    mock_info.previous_close = 170.00
    mock_ticker = MagicMock()
    mock_ticker.fast_info = mock_info

    with patch("api.websocket_server.yf.Ticker", return_value=mock_ticker):
        result = await get_live_price("AAPL")

    assert result is not None
    assert result["ticker"] == "AAPL"
    assert "price" in result
    assert "timestamp" in result
    assert result["price"] == 173.50


@pytest.mark.anyio
async def test_get_live_price_failure():
    with patch("api.websocket_server.yf.Ticker", side_effect=Exception("API error")):
        result = await get_live_price("AAPL")

    assert result is None


def test_websocket_prices_connects():
    with client.websocket_connect("/ws/prices") as ws:
        data = ws.receive_text()
        import json

        payload = json.loads(data)
        assert payload["type"] == "PRICES"
        assert "data" in payload


def test_websocket_alerts_connects():
    with client.websocket_connect("/ws/alerts") as ws:
        data = ws.receive_text()
        import json

        payload = json.loads(data)
        assert payload["type"] == "ALERT"
        assert "ticker" in payload
        assert "message" in payload
