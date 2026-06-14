import json
import logging
import os

import psycopg2
from kafka import KafkaConsumer

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
TOPIC_STOCK_PRICES = os.getenv("KAFKA_TOPIC_STOCK_PRICES", "stock-prices")
CONSUMER_GROUP_ID = "stock-consumer-group"

INSERT_SQL = """
INSERT INTO staging.stock_prices_raw
    (ticker, trade_date, open_price, high_price, low_price, close_price, volume, ingested_at)
VALUES
    (%(ticker)s, %(trade_date)s, %(open)s, %(high)s, %(low)s, %(close)s, %(volume)s, NOW())
ON CONFLICT DO NOTHING
"""


def create_stock_consumer() -> KafkaConsumer:
    consumer = KafkaConsumer(
        TOPIC_STOCK_PRICES,
        bootstrap_servers=BOOTSTRAP_SERVERS,
        group_id=CONSUMER_GROUP_ID,
        auto_offset_reset="earliest",
        value_deserializer=lambda x: json.loads(x.decode("utf-8")),
    )
    logger.info(
        "Kafka consumer connected to %s, group=%s, topic=%s",
        BOOTSTRAP_SERVERS,
        CONSUMER_GROUP_ID,
        TOPIC_STOCK_PRICES,
    )
    return consumer


def process_stock_event(event: dict, conn) -> bool:
    try:
        cursor = conn.cursor()
        params = {
            "ticker": event.get("ticker"),
            "trade_date": event.get("timestamp", "")[:10],
            "open": event.get("open"),
            "high": event.get("high"),
            "low": event.get("low"),
            "close": event.get("close"),
            "volume": event.get("volume"),
        }
        cursor.execute(INSERT_SQL, params)
        conn.commit()
        cursor.close()
        logger.info("Processed event for %s on %s", params["ticker"], params["trade_date"])
        return True
    except Exception as e:
        logger.error("Failed to process event: %s", e)
        try:
            conn.rollback()
        except Exception:
            pass
        return False


def run_stock_consumer() -> None:
    conn = psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=int(os.getenv("POSTGRES_PORT", "5432")),
        dbname=os.getenv("POSTGRES_DB", "stock_pipeline"),
        user=os.getenv("POSTGRES_USER", "pipeline_user"),
        password=os.getenv("POSTGRES_PASSWORD", ""),
    )
    consumer = create_stock_consumer()
    logger.info("Stock consumer started — waiting for events")

    processed = 0
    failed = 0
    try:
        for message in consumer:
            event = message.value
            if process_stock_event(event, conn):
                processed += 1
            else:
                failed += 1
            if (processed + failed) % 10 == 0:
                logger.info("Consumer summary: %d processed, %d failed", processed, failed)
    except KeyboardInterrupt:
        logger.info("Consumer stopped by user")
    finally:
        consumer.close()
        conn.close()
        logger.info(
            "Consumer shut down — total processed: %d, failed: %d", processed, failed
        )


if __name__ == "__main__":
    run_stock_consumer()
