import json
from unittest.mock import MagicMock, patch

from ingestion.data_product_manager import (
    DATA_PRODUCTS,
    get_data_product,
    get_domain_summary,
    list_data_products,
    register_data_product,
)


def _make_s3_body(data: dict) -> MagicMock:
    body = MagicMock()
    body.read.return_value = json.dumps(data).encode("utf-8")
    return body


def test_register_data_product_success():
    product = DATA_PRODUCTS[0]
    mock_client = MagicMock()
    mock_client.put_object.return_value = {}
    with patch("ingestion.data_product_manager.boto3.client", return_value=mock_client):
        result = register_data_product(product, "test-bucket")
    assert result is True
    mock_client.put_object.assert_called_once()


def test_get_data_product_success():
    product = {"product_id": "DP001", "name": "stock_prices", "domain": "market_data"}
    mock_client = MagicMock()
    mock_client.get_object.return_value = {"Body": _make_s3_body(product)}
    with patch("ingestion.data_product_manager.boto3.client", return_value=mock_client):
        result = get_data_product("DP001", "test-bucket")
    assert result is not None
    assert "product_id" in result
    assert result["product_id"] == "DP001"


def test_get_data_product_not_found():
    mock_client = MagicMock()
    mock_client.get_object.side_effect = Exception("NoSuchKey")
    with patch("ingestion.data_product_manager.boto3.client", return_value=mock_client):
        result = get_data_product("DP999", "test-bucket")
    assert result is None


def test_list_data_products_returns_list():
    product = {"product_id": "DP001", "name": "stock_prices", "domain": "market_data"}
    mock_client = MagicMock()
    mock_client.list_objects_v2.return_value = {
        "Contents": [{"Key": "data_mesh/products/DP001.json"}]
    }
    mock_client.get_object.return_value = {"Body": _make_s3_body(product)}
    with patch("ingestion.data_product_manager.boto3.client", return_value=mock_client):
        result = list_data_products("test-bucket")
    assert isinstance(result, list)
    assert len(result) == 1


def test_get_domain_summary_structure():
    products = [
        {"product_id": "DP001", "name": "stock_prices", "domain": "market_data"},
        {"product_id": "DP002", "name": "anomaly_signals", "domain": "ml_insights"},
    ]
    mock_client = MagicMock()
    mock_client.list_objects_v2.return_value = {
        "Contents": [
            {"Key": "data_mesh/products/DP001.json"},
            {"Key": "data_mesh/products/DP002.json"},
        ]
    }
    mock_client.get_object.side_effect = [
        {"Body": _make_s3_body(products[0])},
        {"Body": _make_s3_body(products[1])},
    ]
    with patch("ingestion.data_product_manager.boto3.client", return_value=mock_client):
        result = get_domain_summary("test-bucket")
    assert isinstance(result, dict)
    assert "market_data" in result
    assert "ml_insights" in result
    assert "nlp_insights" in result
    assert "analytics" in result
