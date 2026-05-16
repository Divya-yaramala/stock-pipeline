import pytest
import psycopg2
from unittest.mock import MagicMock, patch

from scripts.setup_postgres import get_connection, create_schemas, create_tables, load_to_postgres


def test_get_connection_success():
    mock_conn = MagicMock()
    with patch("scripts.setup_postgres.psycopg2.connect", return_value=mock_conn) as mock_connect:
        conn = get_connection()
    mock_connect.assert_called_once()
    assert conn is mock_conn


def test_get_connection_failure():
    with patch(
        "scripts.setup_postgres.psycopg2.connect",
        side_effect=psycopg2.OperationalError("Connection refused"),
    ):
        with pytest.raises(psycopg2.OperationalError):
            get_connection()


def test_create_schemas_executes_sql():
    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_conn.cursor.return_value.__enter__.return_value = mock_cur

    create_schemas(mock_conn)

    executed = [call[0][0] for call in mock_cur.execute.call_args_list]
    assert any("staging" in sql for sql in executed)
    assert any("marts" in sql for sql in executed)
    mock_conn.commit.assert_called_once()


def test_create_staging_table_executes_sql():
    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_conn.cursor.return_value.__enter__.return_value = mock_cur

    create_tables(mock_conn)

    executed = [call[0][0] for call in mock_cur.execute.call_args_list]
    assert any("stock_prices_raw" in sql for sql in executed)
    assert any("stock_anomalies" in sql for sql in executed)
    assert any("stock_predictions" in sql for sql in executed)
    assert any("stock_insights" in sql for sql in executed)
    mock_conn.commit.assert_called_once()


def test_load_to_postgres_success():
    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_conn.cursor.return_value = mock_cur

    insert_sql = (
        "INSERT INTO staging.stock_prices_raw (ticker, trade_date) "
        "VALUES (%s, %s) ON CONFLICT DO NOTHING"
    )
    rows = [("AAPL", "2026-05-16")]

    with patch("scripts.setup_postgres.get_connection", return_value=mock_conn):
        result = load_to_postgres(rows, insert_sql)

    assert result is True
    mock_cur.execute.assert_called_once_with(insert_sql, ("AAPL", "2026-05-16"))
    mock_conn.commit.assert_called_once()


def test_load_to_postgres_failure():
    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_conn.cursor.return_value = mock_cur
    mock_cur.execute.side_effect = Exception("Insert failed")

    insert_sql = (
        "INSERT INTO staging.stock_prices_raw (ticker, trade_date) "
        "VALUES (%s, %s) ON CONFLICT DO NOTHING"
    )
    rows = [("AAPL", "2026-05-16")]

    with patch("scripts.setup_postgres.get_connection", return_value=mock_conn):
        result = load_to_postgres(rows, insert_sql)

    assert result is False
