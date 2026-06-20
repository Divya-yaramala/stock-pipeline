import json
from io import BytesIO
from unittest.mock import MagicMock, patch

from ingestion.feature_store import (
    get_features,
    list_feature_groups,
    run_feature_store_check,
    save_features,
)


def test_save_features_success():
    mock_s3 = MagicMock()
    with patch("ingestion.feature_store.boto3.client", return_value=mock_s3):
        result = save_features(
            "AAPL", {"close": 150.0, "sma_20": 148.5}, "price_features", "test-bucket"
        )
    assert result is True
    mock_s3.put_object.assert_called_once()


def test_get_features_success():
    payload = {
        "ticker": "AAPL",
        "feature_group": "price_features",
        "features": {"close": 150.0, "sma_20": 148.5},
        "saved_at": "2026-06-20T00:00:00",
    }
    mock_s3 = MagicMock()
    mock_s3.get_object.return_value = {"Body": BytesIO(json.dumps(payload).encode("utf-8"))}
    with patch("ingestion.feature_store.boto3.client", return_value=mock_s3):
        result = get_features("AAPL", "price_features", "test-bucket", "2026-06-20")
    assert isinstance(result, dict)
    assert "close" in result


def test_get_features_not_found():
    mock_s3 = MagicMock()
    mock_s3.get_object.side_effect = Exception("NoSuchKey")
    with patch("ingestion.feature_store.boto3.client", return_value=mock_s3):
        result = get_features("AAPL", "price_features", "test-bucket", "2026-06-20")
    assert result == {}


def test_list_feature_groups_success():
    mock_s3 = MagicMock()
    mock_s3.list_objects_v2.return_value = {
        "CommonPrefixes": [
            {"Prefix": "features/price_features/"},
            {"Prefix": "features/technical_features/"},
        ]
    }
    with patch("ingestion.feature_store.boto3.client", return_value=mock_s3):
        result = list_feature_groups("test-bucket")
    assert isinstance(result, list)
    assert len(result) == 2
    assert "price_features" in result


def test_run_feature_store_check_structure():
    mock_s3 = MagicMock()
    mock_s3.list_objects_v2.return_value = {"CommonPrefixes": []}
    with patch("ingestion.feature_store.boto3.client", return_value=mock_s3):
        result = run_feature_store_check("test-bucket")
    assert "tickers_with_features" in result
    assert "missing" in result
    assert result["tickers_with_features"] == 0
    assert len(result["missing"]) == 5
