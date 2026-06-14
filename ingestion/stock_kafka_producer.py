import json
import logging
import os
import time
from datetime import datetime, timezone

from kafka import KafkaProducer

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

TICKERS = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"]

BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
TOPIC_STOCK_PRICES = os.getenv("KAFKA_TOPIC_STOCK_PRICES", "stock-prices")


def create_producer() -> KafkaProducer:
    producer = KafkaProducer(
        bootstrap_servers=BOOTSTRAP_SERVERS,
        value_serializer=lambda x: json.dumps(x).encode("utf-8"),
        acks="all",
        retries=3,
    )
    logger.info("Kafka producer connected to %s", BOOTSTRAP_SERVERS)
    return producer


def publish_stock_event(producer: KafkaProducer, ticker: str, price_data: dict) -> bool:
    try:
        event = {
            "ticker": ticker,
            "open": price_data.get("open"),
            "high": price_data.get("high"),
            "low": price_data.get("low"),
            "close": price_data.get("close"),
            "volume": price_data.get("volume"),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "source": "yahoo_finance",
        }
        producer.send(TOPIC_STOCK_PRICES, value=event)
        producer.flush()
        logger.info("Published event for %s to topic %s", ticker, TOPIC_STOCK_PRICES)
        return True
    except Exception as e:
        logger.error("Failed to publish event for %s: %s", ticker, e)
        return False


def run_stock_producer(interval_seconds: int = 300) -> None:
    import yfinance as yf

    producer = create_producer()
    logger.info("Stock producer started — publishing every %ds", interval_seconds)

    try:
        while True:
            published = 0
            failed = 0
            for ticker in TICKERS:
                try:
                    data = yf.Ticker(ticker).fast_info
                    price_data = {
                        "open": getattr(data, "open", None),
                        "high": getattr(data, "day_high", None),
                        "low": getattr(data, "day_low", None),
                        "close": getattr(data, "last_price", None),
                        "volume": getattr(data, "three_month_average_volume", None),
                    }
                    if publish_stock_event(producer, ticker, price_data):
                        published += 1
                    else:
                        failed += 1
                except Exception as e:
                    logger.error("Error fetching %s: %s", ticker, e)
                    failed += 1

            logger.info(
                "Producer run complete: %d published, %d failed — sleeping %ds",
                published,
                failed,
                interval_seconds,
            )
            time.sleep(interval_seconds)

    except KeyboardInterrupt:
        logger.info("Producer stopped by user")
    finally:
        producer.close()
        logger.info("Kafka producer closed")


if __name__ == "__main__":
    run_stock_producer()
