import json
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient


class TestRESTAPIE2E:
    def test_health_endpoint_returns_200(self):
        from api.main import app

        client = TestClient(app)
        response = client.get("/health")
        assert response.status_code == 200
        assert "status" in response.json()

    def test_prices_endpoint_structure(self):
        from api.main import app, get_db_connection

        def override_get_db():
            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_cursor.fetchall.return_value = []
            mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
            mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
            yield mock_conn

        app.dependency_overrides[get_db_connection] = override_get_db
        client = TestClient(app)
        response = client.get("/prices/AAPL")
        app.dependency_overrides.clear()

        assert isinstance(response.json(), list)

    def test_anomalies_endpoint_structure(self):
        from api.main import app, get_db_connection

        def override_get_db():
            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_cursor.fetchall.return_value = []
            mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
            mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
            yield mock_conn

        app.dependency_overrides[get_db_connection] = override_get_db
        client = TestClient(app)
        response = client.get("/anomalies/AAPL")
        app.dependency_overrides.clear()

        assert response.json() is not None

    def test_summary_endpoint_structure(self):
        from api.main import app, get_db_connection

        def override_get_db():
            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_cursor.fetchone.return_value = None
            mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
            mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
            yield mock_conn

        app.dependency_overrides[get_db_connection] = override_get_db
        client = TestClient(app)
        response = client.get("/summary/AAPL")
        app.dependency_overrides.clear()

        assert "ticker" in response.json()

    def test_graphql_health_endpoint(self):
        from api.graphql_api import app

        client = TestClient(app)
        response = client.get("/health")
        assert response.status_code == 200

    def test_websocket_status_endpoint(self):
        from api.websocket_server import app

        client = TestClient(app)
        response = client.get("/ws/status")
        assert "websocket_url" in response.json()
