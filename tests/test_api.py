from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from api.main import app, get_db_connection


def make_mock_conn(fetchall_return=None, fetchone_return=None):
    """Build a mock psycopg2 connection with a cursor."""
    cursor = MagicMock()
    cursor.fetchall.return_value = fetchall_return or []
    cursor.fetchone.return_value = fetchone_return
    cursor.__enter__ = lambda s: s
    cursor.__exit__ = MagicMock(return_value=False)
    conn = MagicMock()
    conn.cursor.return_value = cursor
    return conn, cursor


def override_db(conn):
    def _override():
        yield conn

    return _override


def test_health_endpoint():
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert data["status"] == "healthy"


def test_get_tickers():
    conn, _ = make_mock_conn(fetchall_return=[("AAPL",), ("MSFT",), ("TSLA",)])
    app.dependency_overrides[get_db_connection] = override_db(conn)
    client = TestClient(app)
    response = client.get("/tickers")
    assert response.status_code == 200
    result = response.json()
    assert isinstance(result, list)
    assert "AAPL" in result
    app.dependency_overrides.clear()


def test_get_prices_valid_ticker():
    rows = [("AAPL", "2026-06-04", 189.0, 191.0, 188.0, 190.5, 1000000)]
    conn, _ = make_mock_conn(fetchall_return=rows)
    app.dependency_overrides[get_db_connection] = override_db(conn)
    client = TestClient(app)
    response = client.get("/prices/AAPL")
    assert response.status_code == 200
    result = response.json()
    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0]["ticker"] == "AAPL"
    assert result[0]["close_price"] == 190.5
    app.dependency_overrides.clear()


def test_get_prices_invalid_ticker():
    conn, _ = make_mock_conn(fetchall_return=[])
    app.dependency_overrides[get_db_connection] = override_db(conn)
    client = TestClient(app)
    response = client.get("/prices/FAKE")
    assert response.status_code == 200
    assert response.json() == []
    app.dependency_overrides.clear()


def test_get_anomalies():
    rows = [("AAPL", "2026-06-04", True, -0.42, "anomaly")]
    conn, _ = make_mock_conn(fetchall_return=rows)
    app.dependency_overrides[get_db_connection] = override_db(conn)
    client = TestClient(app)
    response = client.get("/anomalies/AAPL")
    assert response.status_code == 200
    result = response.json()
    assert isinstance(result, list)
    assert result[0]["is_anomaly"] is True
    app.dependency_overrides.clear()


def test_get_summary():
    conn = MagicMock()
    cursor = MagicMock()
    cursor.__enter__ = lambda s: s
    cursor.__exit__ = MagicMock(return_value=False)
    cursor.fetchone.side_effect = [
        (190.5, "2026-06-04"),
        (False,),
        (192.0,),
        ("Markets steady today.",),
    ]
    conn.cursor.return_value = cursor
    app.dependency_overrides[get_db_connection] = override_db(conn)
    client = TestClient(app)
    response = client.get("/summary/AAPL")
    assert response.status_code == 200
    data = response.json()
    assert "latest_price" in data
    assert "is_anomaly" in data
    assert "predicted_close" in data
    app.dependency_overrides.clear()
