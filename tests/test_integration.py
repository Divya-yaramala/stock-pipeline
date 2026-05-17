import logging
import pandas as pd
import numpy as np
import pytest
from datetime import datetime
from unittest.mock import MagicMock, patch, call

import ingestion.fetch_stocks as fetch_stocks
import ingestion.anomaly_detector as anomaly_detector
import ingestion.price_predictor as price_predictor
import ingestion.market_insights as market_insights
from scripts.setup_postgres import load_to_postgres


# ── helpers ──────────────────────────────────────────────────────────────────

def _mock_yf_df() -> pd.DataFrame:
    """Minimal OHLCV DataFrame with integer index (JSON-serialisable)."""
    return pd.DataFrame({
        "Open": [150.0], "High": [155.0], "Low": [148.0],
        "Close": [153.0], "Volume": [1_000_000],
    })


def _mock_s3(get_raises: bool = True) -> MagicMock:
    s3 = MagicMock()
    s3.put_object.return_value = {}
    if get_raises:
        s3.get_object.side_effect = Exception("NoSuchKey")
    return s3


def _mock_openai_client() -> MagicMock:
    client = MagicMock()
    client.chat.completions.create.return_value.choices[0].message.content = (
        "Markets show resilience. Indicators remain steady. Outlook is stable."
    )
    return client


# ── Test 1 ────────────────────────────────────────────────────────────────────

def test_full_pipeline_flow(caplog):
    mock_s3 = _mock_s3(get_raises=True)
    mock_oi  = _mock_openai_client()

    with caplog.at_level(logging.INFO), \
         patch("ingestion.fetch_stocks.yf.download",       return_value=_mock_yf_df()), \
         patch("ingestion.fetch_stocks.boto3.client",       return_value=mock_s3), \
         patch("ingestion.anomaly_detector.boto3.client",   return_value=mock_s3), \
         patch("ingestion.price_predictor.boto3.client",    return_value=mock_s3), \
         patch("ingestion.market_insights.boto3.client",    return_value=mock_s3), \
         patch("ingestion.market_insights.openai.OpenAI",   return_value=mock_oi):

        fetch_stocks.run_pipeline()
        anomaly_detector.run_anomaly_detection()
        price_predictor.run_price_prediction()
        market_insights.run_market_insights()

    assert "Pipeline complete" in caplog.text
    assert "Anomaly detection complete" in caplog.text
    assert "Price prediction complete" in caplog.text
    assert "Market insights complete" in caplog.text


# ── Test 2 ────────────────────────────────────────────────────────────────────

def test_s3_paths_are_consistent():
    date     = datetime.now().strftime("%Y/%m/%d")
    mock_s3  = MagicMock()
    mock_s3.put_object.return_value = {}
    mock_s3.get_object.side_effect  = Exception("NoSuchKey")

    # fetch_stocks writes raw/stocks/YYYY/MM/DD/ticker.json
    with patch("ingestion.fetch_stocks.boto3.client", return_value=mock_s3):
        fetch_stocks.upload_to_s3({"Open": {0: 150.0}}, "AAPL", "test-bucket", date)
    raw_key = mock_s3.put_object.call_args[1]["Key"]
    assert raw_key == f"raw/stocks/{date}/AAPL.json"

    # anomaly_detector reads from the same raw path
    mock_s3.reset_mock()
    mock_s3.get_object.side_effect = Exception("NoSuchKey")
    with patch("ingestion.anomaly_detector.boto3.client", return_value=mock_s3):
        anomaly_detector.load_stock_data_from_s3("AAPL", "test-bucket", date)
    anomaly_read_key = mock_s3.get_object.call_args[1]["Key"]
    assert anomaly_read_key == f"raw/stocks/{date}/AAPL.json"

    # anomaly_detector writes to processed/anomalies/YYYY/MM/DD/ticker.json
    mock_s3.reset_mock()
    mock_s3.get_object.side_effect = None
    mock_s3.put_object.return_value = {}
    sample_df = pd.DataFrame({
        "open": [150.0], "high": [155.0], "low": [148.0],
        "close": [153.0], "volume": [1_000_000.0],
    })
    detected = anomaly_detector.detect_anomalies(sample_df, "AAPL")
    with patch("ingestion.anomaly_detector.boto3.client", return_value=mock_s3):
        anomaly_detector.save_anomaly_results(detected, "AAPL", "test-bucket", date)
    anomaly_write_key = mock_s3.put_object.call_args[1]["Key"]
    assert anomaly_write_key == f"processed/anomalies/{date}/AAPL.json"

    # price_predictor writes to processed/predictions/YYYY/MM/DD/ticker.json
    mock_s3.reset_mock()
    forecast_df = pd.DataFrame({
        "ds":          pd.date_range("2026-05-17", periods=5),
        "yhat":        [150.0] * 5,
        "yhat_lower":  [145.0] * 5,
        "yhat_upper":  [155.0] * 5,
    })
    with patch("ingestion.price_predictor.boto3.client", return_value=mock_s3):
        price_predictor.save_predictions_to_s3(forecast_df, "AAPL", "test-bucket", date)
    pred_write_key = mock_s3.put_object.call_args[1]["Key"]
    assert pred_write_key == f"processed/predictions/{date}/AAPL.json"

    # market_insights reads from all 3 paths
    mock_s3.reset_mock()
    mock_s3.get_object.side_effect = Exception("NoSuchKey")
    with patch("ingestion.market_insights.boto3.client", return_value=mock_s3):
        market_insights.load_todays_data("AAPL", "test-bucket", date)
    read_keys = {c[1]["Key"] for c in mock_s3.get_object.call_args_list}
    assert f"raw/stocks/{date}/AAPL.json"                    in read_keys
    assert f"processed/anomalies/{date}/AAPL.json"           in read_keys
    assert f"processed/predictions/{date}/AAPL.json"         in read_keys


# ── Test 3 ────────────────────────────────────────────────────────────────────

def test_idempotency():
    mock_conn = MagicMock()
    mock_cur  = MagicMock()
    mock_conn.cursor.return_value = mock_cur

    insert_sql = (
        "INSERT INTO staging.stock_prices_raw "
        "(ticker, trade_date, open_price, high_price, low_price, close_price, volume) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s) "
        "ON CONFLICT (ticker, trade_date) DO NOTHING"
    )
    rows = [("AAPL", "2026-05-17", 150.0, 155.0, 148.0, 153.0, 1_000_000)]

    with patch("scripts.setup_postgres.get_connection", return_value=mock_conn):
        result1 = load_to_postgres(rows, insert_sql)
        result2 = load_to_postgres(rows, insert_sql)

    assert result1 is True
    assert result2 is True
    assert "ON CONFLICT" in insert_sql
    assert mock_cur.execute.call_count == 2
