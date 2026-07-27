import json
from unittest.mock import MagicMock, patch

from ingestion.data_mesh_api import (
    approve_access_request,
    get_data_product_sample,
    get_data_product_schema,
    publish_data_product_update,
    request_data_access,
)


def _make_s3_body(data: dict) -> MagicMock:
    body = MagicMock()
    body.read.return_value = json.dumps(data).encode("utf-8")
    return body


def test_request_data_access_returns_id():
    mock_client = MagicMock()
    mock_client.put_object.return_value = {}
    with patch("ingestion.data_mesh_api.boto3.client", return_value=mock_client):
        result = request_data_access(
            product_id="DP001",
            requester="analytics_team",
            purpose="Quarterly analysis",
            bucket="test-bucket",
        )
    assert isinstance(result, str)
    assert len(result) > 0
    mock_client.put_object.assert_called_once()


def test_approve_access_request_success():
    mock_client = MagicMock()
    mock_client.put_object.return_value = {}
    with patch("ingestion.data_mesh_api.boto3.client", return_value=mock_client):
        result = approve_access_request(
            request_id="req-abc-123",
            approver="data_owner",
            bucket="test-bucket",
        )
    assert result is True
    mock_client.put_object.assert_called_once()


def test_get_data_product_sample_returns_list():
    sample = {"ticker": "AAPL", "close_price": 185.0}
    mock_client = MagicMock()
    mock_client.list_objects_v2.return_value = {
        "Contents": [{"Key": "data_mesh/samples/DP001/sample_001.json"}]
    }
    mock_client.get_object.return_value = {"Body": _make_s3_body(sample)}
    with patch("ingestion.data_mesh_api.boto3.client", return_value=mock_client):
        result = get_data_product_sample(
            product_id="DP001",
            num_records=5,
            bucket="test-bucket",
        )
    assert isinstance(result, list)


def test_publish_data_product_update_success():
    mock_client = MagicMock()
    mock_client.put_object.return_value = {}
    with patch("ingestion.data_mesh_api.boto3.client", return_value=mock_client):
        result = publish_data_product_update(
            product_id="DP001",
            version="1.1.0",
            changelog="Added adj_close field",
            bucket="test-bucket",
        )
    assert result is True
    mock_client.put_object.assert_called_once()


def test_get_data_product_schema_not_found():
    mock_client = MagicMock()
    mock_client.get_object.side_effect = Exception("NoSuchKey")
    with patch("ingestion.data_mesh_api.boto3.client", return_value=mock_client):
        result = get_data_product_schema(
            product_id="DP999",
            bucket="test-bucket",
        )
    assert result is None
