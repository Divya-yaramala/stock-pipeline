from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd

from ingestion.price_predictor import (
    load_historical_data_from_s3,
    prepare_prophet_data,
    save_predictions_to_s3,
    train_and_predict,
)


def _make_ohlcv_df(n: int = 30) -> pd.DataFrame:
    rng = np.random.default_rng(42)
    dates = [datetime(2026, 1, 1) + timedelta(days=i) for i in range(n)]
    return pd.DataFrame(
        {
            "date": dates,
            "open": rng.uniform(90, 110, n),
            "high": rng.uniform(100, 120, n),
            "low": rng.uniform(80, 100, n),
            "close": rng.uniform(90, 110, n),
            "volume": rng.uniform(900_000, 1_100_000, n),
        }
    )


def _make_forecast_df(n: int = 5) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "ds": pd.date_range("2026-05-14", periods=n),
            "yhat": np.linspace(150.0, 155.0, n),
            "yhat_lower": np.linspace(145.0, 150.0, n),
            "yhat_upper": np.linspace(155.0, 160.0, n),
        }
    )


def test_prepare_prophet_data_columns():
    df = _make_ohlcv_df(10)
    result = prepare_prophet_data(df)
    assert list(result.columns) == ["ds", "y"]


def test_prepare_prophet_data_not_empty():
    df = _make_ohlcv_df(10)
    result = prepare_prophet_data(df)
    assert len(result) == len(df)


def test_train_and_predict_returns_forecast():
    df = _make_ohlcv_df(30)
    prophet_df = prepare_prophet_data(df)
    result = train_and_predict(prophet_df, "AAPL")
    assert "yhat" in result.columns
    assert "yhat_lower" in result.columns
    assert "yhat_upper" in result.columns


def test_train_and_predict_forecast_length():
    df = _make_ohlcv_df(30)
    prophet_df = prepare_prophet_data(df)
    result = train_and_predict(prophet_df, "AAPL", forecast_days=5)
    assert len(result) == 5


def test_save_predictions_to_s3_success():
    df = _make_forecast_df()
    mock_s3 = MagicMock()
    mock_s3.put_object.return_value = {}
    with patch("ingestion.price_predictor.boto3.client", return_value=mock_s3):
        result = save_predictions_to_s3(df, "AAPL", "test-bucket", "2026/05/14")
    assert result is True


def test_save_predictions_to_s3_failure():
    df = _make_forecast_df()
    mock_s3 = MagicMock()
    mock_s3.put_object.side_effect = Exception("S3 write error")
    with patch("ingestion.price_predictor.boto3.client", return_value=mock_s3):
        result = save_predictions_to_s3(df, "AAPL", "test-bucket", "2026/05/14")
    assert result is False


def test_load_historical_data_empty():
    mock_s3 = MagicMock()
    mock_s3.get_object.side_effect = Exception("NoSuchKey")
    with patch("ingestion.price_predictor.boto3.client", return_value=mock_s3):
        df = load_historical_data_from_s3("AAPL", "test-bucket", days=5)
    assert df.empty
