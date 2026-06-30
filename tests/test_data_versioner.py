import json
from io import BytesIO
from typing import Any, Dict
from unittest.mock import MagicMock, patch

from ingestion.data_versioner import (
    compare_versions,
    generate_version_id,
    rollback_to_version,
    save_versioned_data,
)


def test_generate_version_id_consistent():
    data: Dict[str, Any] = {"close": 190.5, "volume": 1000000}
    id1 = generate_version_id("AAPL", "2026-06-05", data)
    id2 = generate_version_id("AAPL", "2026-06-05", data)
    assert id1 == id2


def test_generate_version_id_8_chars():
    data: Dict[str, Any] = {"close": 190.5}
    version_id = generate_version_id("AAPL", "2026-06-05", data)
    assert len(version_id) == 8


def test_save_versioned_data_success():
    data: Dict[str, Any] = {"close": 190.5, "volume": 1000000}
    with patch("ingestion.data_versioner.boto3.client") as mock_client:
        mock_s3 = MagicMock()
        mock_client.return_value = mock_s3
        version_id = save_versioned_data(data, "AAPL", "fetch", "test-bucket", "2026-06-05")
    assert isinstance(version_id, str)
    assert len(version_id) == 8
    mock_s3.put_object.assert_called_once()


def test_rollback_to_version_success():
    payload: Dict[str, Any] = {"data": {"close": 190.5}, "version_id": "abc12345", "ticker": "AAPL"}
    with patch("ingestion.data_versioner.boto3.client") as mock_client:
        mock_s3 = MagicMock()
        mock_client.return_value = mock_s3
        mock_s3.get_object.return_value = {"Body": BytesIO(json.dumps(payload).encode("utf-8"))}
        result = rollback_to_version("AAPL", "fetch", "abc12345", "test-bucket", "2026-06-05")
    assert isinstance(result, dict)
    assert "data" in result


def test_compare_versions_structure():
    payload1: Dict[str, Any] = {
        "data": {"close": 190.5, "volume": 1000000},
        "version_id": "abc12345",
    }
    payload2: Dict[str, Any] = {
        "data": {"close": 191.0, "open": 189.0},
        "version_id": "def67890",
    }
    with patch("ingestion.data_versioner.rollback_to_version") as mock_rollback:
        mock_rollback.side_effect = [payload1, payload2]
        result = compare_versions(
            "AAPL", "prices", "abc12345", "def67890", "test-bucket", "2026-06-05"
        )
    assert isinstance(result, dict)
    assert "added_keys" in result
    assert "removed_keys" in result
    assert "changed_keys" in result
