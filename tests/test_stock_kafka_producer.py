from unittest.mock import MagicMock, patch

from ingestion.stock_kafka_producer import create_producer, publish_stock_event

SAMPLE_PRICE_DATA = {
    "open": 170.0,
    "high": 175.0,
    "low": 168.0,
    "close": 173.0,
    "volume": 50_000_000,
}


def test_publish_stock_event_success():
    mock_producer = MagicMock()
    result = publish_stock_event(mock_producer, "AAPL", SAMPLE_PRICE_DATA)
    assert result is True
    mock_producer.send.assert_called_once()
    mock_producer.flush.assert_called_once()


def test_publish_stock_event_failure():
    mock_producer = MagicMock()
    mock_producer.send.side_effect = Exception("Kafka unavailable")
    result = publish_stock_event(mock_producer, "AAPL", SAMPLE_PRICE_DATA)
    assert result is False


def test_event_format_has_required_keys():
    mock_producer = MagicMock()
    publish_stock_event(mock_producer, "AAPL", SAMPLE_PRICE_DATA)
    call_kwargs = mock_producer.send.call_args.kwargs
    event = call_kwargs["value"]
    for key in ["ticker", "open", "high", "low", "close", "volume", "timestamp"]:
        assert key in event, f"Missing key: {key}"
    assert event["ticker"] == "AAPL"
    assert event["source"] == "yahoo_finance"


def test_create_producer_success():
    mock_producer_instance = MagicMock()
    with patch("ingestion.stock_kafka_producer.KafkaProducer", return_value=mock_producer_instance):
        producer = create_producer()
    assert producer is mock_producer_instance


def test_publish_all_tickers():
    mock_producer = MagicMock()
    tickers = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"]
    for ticker in tickers:
        publish_stock_event(mock_producer, ticker, SAMPLE_PRICE_DATA)
    assert mock_producer.send.call_count == 5
