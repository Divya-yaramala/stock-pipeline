from datetime import date, timedelta
from unittest.mock import MagicMock, patch

import pandas as pd

from ingestion.incremental_loader import (
    backfill_ticker,
    get_last_loaded_date,
    get_missing_dates,
)


def _make_conn(fetchone_result=None):
    """Build a MagicMock psycopg2 connection with a cursor returning fetchone_result."""
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = fetchone_result
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
    mock_conn.cursor.return_value.__exit__.return_value = False
    return mock_conn, mock_cursor


def test_get_last_loaded_date_exists():
    mock_conn, _ = _make_conn(fetchone_result=(date(2026, 1, 15),))
    result = get_last_loaded_date("AAPL", mock_conn)
    assert result == "2026-01-15"


def test_get_last_loaded_date_empty():
    mock_conn, _ = _make_conn(fetchone_result=(None,))
    result = get_last_loaded_date("AAPL", mock_conn)
    assert result is None


def test_get_missing_dates_returns_list():
    five_days_ago = (date.today() - timedelta(days=5)).strftime("%Y-%m-%d")
    mock_conn, _ = _make_conn()
    with patch("ingestion.incremental_loader.get_last_loaded_date", return_value=five_days_ago):
        result = get_missing_dates("AAPL", mock_conn)
    assert isinstance(result, list)
    assert len(result) > 0


def test_get_missing_dates_no_gaps():
    yesterday = (date.today() - timedelta(days=1)).strftime("%Y-%m-%d")
    mock_conn, _ = _make_conn()
    with patch("ingestion.incremental_loader.get_last_loaded_date", return_value=yesterday):
        result = get_missing_dates("AAPL", mock_conn)
    assert result == []


def test_backfill_ticker_success():
    mock_df = pd.DataFrame(
        {
            "open": [150.0],
            "high": [155.0],
            "low": [148.0],
            "close": [153.0],
            "volume": [1000000],
        },
        index=pd.DatetimeIndex([pd.Timestamp("2026-01-02")], name="Date"),
    )
    mock_conn, _ = _make_conn()

    with patch("ingestion.incremental_loader.boto3") as mock_boto3:
        with patch("ingestion.incremental_loader.yf") as mock_yf:
            mock_s3 = MagicMock()
            mock_boto3.client.return_value = mock_s3
            mock_yf.download.return_value = mock_df
            result = backfill_ticker("AAPL", mock_conn, "test-bucket", "2026-01-01", "2026-01-03")

    assert result > 0
    mock_s3.put_object.assert_called_once()


def test_backfill_ticker_dry_run():
    with patch("scripts.backfill.incremental_loader", create=True) as mock_loader:
        from scripts.backfill import run_backfill

        run_backfill("AAPL", "2026-01-01", "2026-01-31", dry_run=True)
    mock_loader.backfill_ticker.assert_not_called()
