from unittest.mock import MagicMock, patch

import pandas as pd

from ingestion.data_validator import (
    save_validation_report,
    validate_anomaly_data,
    validate_stock_data,
)

VALID_DF = pd.DataFrame(
    {
        "open": [150.0],
        "high": [155.0],
        "low": [148.0],
        "close": [153.0],
        "volume": [1000000],
    }
)


def test_validate_stock_data_passes():
    report = validate_stock_data(VALID_DF, "AAPL")
    assert report["passed"] is True
    assert report["ticker"] == "AAPL"
    assert all(report["checks"].values())


def test_validate_stock_data_fails_null():
    df = VALID_DF.copy()
    df.loc[0, "close"] = None
    report = validate_stock_data(df, "MSFT")
    assert report["passed"] is False
    assert report["checks"]["no_nulls"] is False


def test_validate_stock_data_fails_negative_price():
    df = VALID_DF.copy()
    df.loc[0, "close"] = -1.0
    report = validate_stock_data(df, "GOOGL")
    assert report["passed"] is False
    assert report["checks"]["price_positive"] is False


def test_validate_stock_data_fails_high_lt_low():
    df = VALID_DF.copy()
    df.loc[0, "high"] = 140.0  # below low of 148
    report = validate_stock_data(df, "AMZN")
    assert report["passed"] is False
    assert report["checks"]["high_gte_low"] is False


def test_validate_anomaly_data_passes():
    data = {"is_anomaly": False, "anomaly_score": -0.12}
    report = validate_anomaly_data(data, "TSLA")
    assert report["passed"] is True
    assert all(report["checks"].values())


def test_save_validation_report_success():
    report = {"ticker": "AAPL", "passed": True, "checks": {}}
    with patch("ingestion.data_validator.boto3") as mock_boto3:
        mock_s3 = MagicMock()
        mock_boto3.client.return_value = mock_s3
        result = save_validation_report(report, "AAPL", "test-bucket", "2026/05/23")
    assert result is True
    mock_s3.put_object.assert_called_once()
    call_kwargs = mock_s3.put_object.call_args[1]
    assert call_kwargs["Bucket"] == "test-bucket"
    assert "processed/validation/2026/05/23/AAPL.json" == call_kwargs["Key"]
