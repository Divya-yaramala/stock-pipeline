from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

from ingestion.data_governance import (
    apply_data_masking,
    check_retention_policy,
    classify_data,
    create_audit_log,
)


def test_classify_data_public():
    result = classify_data("geo_data", {"country": "US", "continent": "NA"})
    assert result["classification"] == "PUBLIC"


def test_classify_data_with_pii():
    result = classify_data("user_data", {"email": "user@example.com", "ticker": "AAPL"})
    assert result["pii_detected"] is True


def test_apply_data_masking():
    data = {"email": "user@example.com", "ticker": "AAPL"}
    masked = apply_data_masking(data, ["email"])
    assert masked["email"] != "user@example.com"
    assert masked["ticker"] == "AAPL"


def test_create_audit_log_success():
    mock_s3 = MagicMock()
    with patch("ingestion.data_governance.boto3.client", return_value=mock_s3):
        result = create_audit_log("READ", "stock_prices_raw", "pipeline", {}, "test-bucket")
    assert result is True
    mock_s3.put_object.assert_called_once()


def test_check_retention_policy_expired():
    old_date = (datetime.now() - timedelta(days=100)).strftime("%Y-%m-%d")
    result = check_retention_policy("stock_prices_raw", old_date, 30)
    assert result["should_delete"] is True
