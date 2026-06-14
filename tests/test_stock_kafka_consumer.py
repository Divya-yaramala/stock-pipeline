from unittest.mock import MagicMock, patch

from ingestion.stock_kafka_consumer import (
    CONSUMER_GROUP_ID,
    INSERT_SQL,
    create_stock_consumer,
    process_stock_event,
)

SAMPLE_EVENT = {
    "ticker": "AAPL",
    "open": 170.0,
    "high": 175.0,
    "low": 168.0,
    "close": 173.0,
    "volume": 50_000_000,
    "timestamp": "2026-06-14T18:00:00+00:00",
    "source": "yahoo_finance",
}


def _mock_conn():
    conn = MagicMock()
    conn.cursor.return_value = MagicMock()
    return conn


def test_process_stock_event_success():
    conn = _mock_conn()
    result = process_stock_event(SAMPLE_EVENT, conn)
    assert result is True
    conn.cursor.return_value.execute.assert_called_once()
    conn.commit.assert_called_once()


def test_process_stock_event_failure():
    conn = _mock_conn()
    conn.cursor.return_value.execute.side_effect = Exception("DB error")
    result = process_stock_event(SAMPLE_EVENT, conn)
    assert result is False
    conn.rollback.assert_called_once()


def test_create_stock_consumer_success():
    mock_consumer_instance = MagicMock()
    with patch("ingestion.stock_kafka_consumer.KafkaConsumer", return_value=mock_consumer_instance):
        consumer = create_stock_consumer()
    assert consumer is mock_consumer_instance


def test_process_event_idempotent():
    assert "ON CONFLICT DO NOTHING" in INSERT_SQL


def test_consumer_group_id():
    assert CONSUMER_GROUP_ID == "stock-consumer-group"
