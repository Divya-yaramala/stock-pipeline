import pytest
import pandas as pd
import numpy as np
from unittest.mock import MagicMock, patch
import json

from ingestion.anomaly_detector import detect_anomalies, load_stock_data_from_s3, save_anomaly_results


def _make_normal_df(n: int = 20) -> pd.DataFrame:
    rng = np.random.default_rng(42)
    return pd.DataFrame({
        "open": rng.uniform(90, 110, n),
        "high": rng.uniform(100, 120, n),
        "low": rng.uniform(80, 100, n),
        "close": rng.uniform(90, 110, n),
        "volume": rng.uniform(900_000, 1_100_000, n),
    })


def test_detect_anomalies_returns_dataframe():
    df = _make_normal_df(20)
    result = detect_anomalies(df, "AAPL")
    assert "is_anomaly" in result.columns
    assert "anomaly_score" in result.columns


def test_detect_anomalies_flags_outlier():
    normal = _make_normal_df(19)
    outlier = pd.DataFrame({
        "open": [50_000.0],
        "high": [60_000.0],
        "low": [40_000.0],
        "close": [55_000.0],
        "volume": [999_999_999.0],
    })
    df = pd.concat([normal, outlier], ignore_index=True)
    result = detect_anomalies(df, "TEST")
    assert result.loc[19, "is_anomaly"] == True


def test_load_stock_data_from_s3_success():
    sample_data = {
        "open": {"0": 100.0},
        "high": {"0": 105.0},
        "low": {"0": 95.0},
        "close": {"0": 102.0},
        "volume": {"0": 1_000_000.0},
    }
    mock_body = MagicMock()
    mock_body.read.return_value = json.dumps(sample_data).encode("utf-8")
    mock_s3 = MagicMock()
    mock_s3.get_object.return_value = {"Body": mock_body}

    with patch("ingestion.anomaly_detector.boto3.client", return_value=mock_s3):
        df = load_stock_data_from_s3("AAPL", "test-bucket", "2026/05/13")

    assert not df.empty


def test_load_stock_data_from_s3_failure():
    mock_s3 = MagicMock()
    mock_s3.get_object.side_effect = Exception("S3 connection error")

    with patch("ingestion.anomaly_detector.boto3.client", return_value=mock_s3):
        df = load_stock_data_from_s3("AAPL", "test-bucket", "2026/05/13")

    assert df.empty


def test_save_anomaly_results_success():
    df = _make_normal_df(5)
    df["is_anomaly"] = False
    df["anomaly_score"] = 0.1
    mock_s3 = MagicMock()
    mock_s3.put_object.return_value = {}

    with patch("ingestion.anomaly_detector.boto3.client", return_value=mock_s3):
        result = save_anomaly_results(df, "AAPL", "test-bucket", "2026/05/13")

    assert result is True


def test_save_anomaly_results_failure():
    df = _make_normal_df(5)
    df["is_anomaly"] = False
    df["anomaly_score"] = 0.1
    mock_s3 = MagicMock()
    mock_s3.put_object.side_effect = Exception("S3 write error")

    with patch("ingestion.anomaly_detector.boto3.client", return_value=mock_s3):
        result = save_anomaly_results(df, "AAPL", "test-bucket", "2026/05/13")

    assert result is False
