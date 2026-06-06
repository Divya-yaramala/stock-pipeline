import json
from io import BytesIO
from unittest.mock import MagicMock, patch

from ingestion.data_versioner import (
    generate_version_id,
    list_versions,
    rollback_to_version,
    save_versioned_snapshot,
)


def test_generate_version_id_consistent():
    data = {"close": 190.5, "volume": 1000000}
    id1 = generate_version_id("AAPL", "2026-06-05", data)
    id2 = generate_version_id("AAPL", "2026-06-05", data)
    assert id1 == id2
    assert len(id1) == 8


def test_generate_version_id_different():
    data_a = {"close": 190.5}
    data_b = {"close": 191.0}
    id_a = generate_version_id("AAPL", "2026-06-05", data_a)
    id_b = generate_version_id("AAPL", "2026-06-05", data_b)
    assert id_a != id_b


def test_save_versioned_snapshot_success():
    data = {"close": 190.5, "volume": 1000000}
    with patch("ingestion.data_versioner.boto3.client") as mock_client:
        mock_s3 = MagicMock()
        mock_client.return_value = mock_s3
        version_id = save_versioned_snapshot(data, "AAPL", "fetch", "test-bucket", "2026-06-05")
    assert isinstance(version_id, str)
    assert len(version_id) == 8
    mock_s3.put_object.assert_called_once()


def test_save_versioned_snapshot_correct_path():
    data = {"close": 190.5}
    with patch("ingestion.data_versioner.boto3.client") as mock_client:
        mock_s3 = MagicMock()
        mock_client.return_value = mock_s3
        save_versioned_snapshot(data, "AAPL", "fetch", "test-bucket", "2026-06-05")

    call_kwargs = mock_s3.put_object.call_args.kwargs
    key = call_kwargs["Key"]
    assert key.startswith("versions/2026/06/05/fetch/")
    assert "AAPL_" in key
    assert key.endswith(".json")


def test_list_versions_success():
    with patch("ingestion.data_versioner.boto3.client") as mock_client:
        mock_s3 = MagicMock()
        mock_client.return_value = mock_s3
        mock_s3.list_objects_v2.return_value = {
            "Contents": [
                {"Key": "versions/2026/06/05/fetch/AAPL_abc12345.json", "LastModified": ""},
                {"Key": "versions/2026/06/05/fetch/AAPL_def67890.json", "LastModified": ""},
            ]
        }
        versions = list_versions("AAPL", "fetch", "test-bucket", "2026-06-05")

    assert isinstance(versions, list)
    assert len(versions) == 2
    assert all("version_id" in v for v in versions)


def test_rollback_to_version_success():
    payload = {"data": {"close": 190.5}, "version_id": "abc12345", "ticker": "AAPL"}
    with patch("ingestion.data_versioner.boto3.client") as mock_client:
        mock_s3 = MagicMock()
        mock_client.return_value = mock_s3
        mock_s3.get_object.return_value = {"Body": BytesIO(json.dumps(payload).encode("utf-8"))}
        result = rollback_to_version("AAPL", "fetch", "abc12345", "test-bucket", "2026-06-05")

    assert isinstance(result, dict)
    assert "data" in result
    assert result["version_id"] == "abc12345"
