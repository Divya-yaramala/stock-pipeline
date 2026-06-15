from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from api.graphql_api import app

client = TestClient(app)


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_graphql_tickers_query():
    query = "{ tickers }"
    response = client.post("/graphql", json={"query": query})
    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    assert "tickers" in data["data"]
    assert isinstance(data["data"]["tickers"], list)
    assert "AAPL" in data["data"]["tickers"]


def test_graphql_stock_prices_query():
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.fetchall.return_value = [
        ("AAPL", "2026-06-14", 170.0, 175.0, 168.0, 173.0, 50_000_000),
    ]
    mock_conn.cursor.return_value = mock_cursor

    with patch("api.graphql_api._get_conn", return_value=mock_conn):
        query = '{ stockPrices(ticker: "AAPL") { ticker closePrice } }'
        response = client.post("/graphql", json={"query": query})

    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    assert "stockPrices" in data["data"]


def test_graphql_anomalies_query():
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.fetchall.return_value = [
        ("AAPL", "2026-06-14", False, -0.12),
    ]
    mock_conn.cursor.return_value = mock_cursor

    with patch("api.graphql_api._get_conn", return_value=mock_conn):
        query = '{ anomalies(ticker: "AAPL") { ticker isAnomaly } }'
        response = client.post("/graphql", json={"query": query})

    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    assert "anomalies" in data["data"]


def test_graphql_portfolio_summary():
    query = "{ portfolioSummary { totalValue dailyReturnPct } }"
    response = client.post("/graphql", json={"query": query})
    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    assert "portfolioSummary" in data["data"]
    assert data["data"]["portfolioSummary"]["totalValue"] > 0


def test_graphql_invalid_query():
    response = client.post("/graphql", json={"query": "{ invalidFieldThatDoesNotExist }"})
    assert response.status_code == 200
    data = response.json()
    assert "errors" in data
