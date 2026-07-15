import json
from unittest.mock import MagicMock, patch

from ingestion.schema_registry import (
    get_schema,
    register_schema,
    validate_schema_evolution,
)


def _make_s3_body(data: dict) -> MagicMock:
    body = MagicMock()
    body.read.return_value = json.dumps(data).encode("utf-8")
    return body


def test_register_schema_success():
    mock_client = MagicMock()
    mock_client.put_object.return_value = {}
    schema_def = {"ticker": {"type": "string"}, "close_price": {"type": "float"}}
    with patch("ingestion.schema_registry.boto3.client", return_value=mock_client):
        result = register_schema("stock_prices_raw", schema_def, "1.0.0", "test-bucket")
    assert isinstance(result, str)
    assert len(result) > 0
    mock_client.put_object.assert_called_once()


def test_get_schema_success():
    record = {
        "schema_id": "abc123",
        "schema_name": "stock_prices_raw",
        "schema_def": {"ticker": {"type": "string"}},
        "version": "1.0.0",
        "registered_at": "2026-07-14T00:00:00",
    }
    mock_client = MagicMock()
    mock_client.get_object.return_value = {"Body": _make_s3_body(record)}
    with patch("ingestion.schema_registry.boto3.client", return_value=mock_client):
        result = get_schema("stock_prices_raw", "1.0.0", "test-bucket")
    assert result is not None
    assert "schema_name" in result
    assert result["schema_name"] == "stock_prices_raw"


def test_get_schema_not_found():
    mock_client = MagicMock()
    mock_client.get_object.side_effect = Exception("NoSuchKey")
    with patch("ingestion.schema_registry.boto3.client", return_value=mock_client):
        result = get_schema("nonexistent", "1.0.0", "test-bucket")
    assert result is None


def test_validate_schema_evolution_safe():
    old_schema = {
        "ticker": {"type": "string"},
        "close_price": {"type": "float"},
    }
    new_schema = {
        "ticker": {"type": "string"},
        "close_price": {"type": "float"},
        "volume": {"type": "integer"},
    }
    result = validate_schema_evolution(old_schema, new_schema)
    assert result["safe"] is True
    assert result["breaking"] == []


def test_validate_schema_evolution_breaking():
    old_schema = {
        "ticker": {"type": "string"},
        "close_price": {"type": "float"},
    }
    new_schema = {
        "ticker": {"type": "string"},
    }
    result = validate_schema_evolution(old_schema, new_schema)
    assert result["safe"] is False
    assert len(result["breaking"]) > 0
