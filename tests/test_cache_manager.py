import json
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

from ingestion.cache_manager import (
    generate_cache_key,
    get_from_cache,
    save_to_cache,
)


def test_generate_cache_key_consistent():
    key1 = generate_cache_key("my_func", {"ticker": "AAPL"})
    key2 = generate_cache_key("my_func", {"ticker": "AAPL"})
    assert key1 == key2
    assert len(key1) == 16


def test_generate_cache_key_different():
    key1 = generate_cache_key("my_func", {"ticker": "AAPL"})
    key2 = generate_cache_key("my_func", {"ticker": "MSFT"})
    assert key1 != key2


def test_save_to_cache_success():
    mock_s3 = MagicMock()
    with patch("ingestion.cache_manager.boto3.client", return_value=mock_s3):
        result = save_to_cache("abc123", {"price": 150.0}, "test-bucket", ttl_seconds=3600)
    assert result is True
    mock_s3.put_object.assert_called_once()


def test_get_from_cache_hit():
    now = datetime.now(timezone.utc)
    expires_at = (now + timedelta(hours=1)).isoformat()
    entry = {
        "data": {"price": 150.0},
        "cached_at": now.isoformat(),
        "ttl_seconds": 3600,
        "expires_at": expires_at,
    }
    mock_s3 = MagicMock()
    mock_body = MagicMock()
    mock_body.read.return_value = json.dumps(entry).encode()
    mock_s3.get_object.return_value = {"Body": mock_body}

    with patch("ingestion.cache_manager.boto3.client", return_value=mock_s3):
        result = get_from_cache("abc123", "test-bucket")

    assert result is not None
    assert result["price"] == 150.0


def test_get_from_cache_expired():
    now = datetime.now(timezone.utc)
    expires_at = (now - timedelta(hours=1)).isoformat()
    entry = {
        "data": {"price": 150.0},
        "cached_at": (now - timedelta(hours=2)).isoformat(),
        "ttl_seconds": 3600,
        "expires_at": expires_at,
    }
    mock_s3 = MagicMock()
    mock_body = MagicMock()
    mock_body.read.return_value = json.dumps(entry).encode()
    mock_s3.get_object.return_value = {"Body": mock_body}

    with patch("ingestion.cache_manager.boto3.client", return_value=mock_s3):
        result = get_from_cache("abc123", "test-bucket")

    assert result is None
