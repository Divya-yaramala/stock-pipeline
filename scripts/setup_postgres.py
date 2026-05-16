import logging
import os

import psycopg2

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def get_connection() -> psycopg2.extensions.connection:
    return psycopg2.connect(
        host=os.environ.get("POSTGRES_HOST", "localhost"),
        port=int(os.environ.get("POSTGRES_PORT", "5432")),
        user=os.environ.get("POSTGRES_USER", "pipeline_user"),
        password=os.environ.get("POSTGRES_PASSWORD", ""),
        dbname=os.environ.get("POSTGRES_DB", "stock_pipeline"),
    )


def create_schemas(conn: psycopg2.extensions.connection) -> None:
    with conn.cursor() as cur:
        cur.execute("CREATE SCHEMA IF NOT EXISTS staging")
        cur.execute("CREATE SCHEMA IF NOT EXISTS marts")
    conn.commit()
    logger.info("Created schemas: staging, marts")


def create_tables(conn: psycopg2.extensions.connection) -> None:
    statements = [
        """
        CREATE TABLE IF NOT EXISTS staging.stock_prices_raw (
            id          SERIAL PRIMARY KEY,
            ticker      VARCHAR(10)    NOT NULL,
            trade_date  DATE           NOT NULL,
            open_price  NUMERIC(12, 4),
            high_price  NUMERIC(12, 4),
            low_price   NUMERIC(12, 4),
            close_price NUMERIC(12, 4) NOT NULL,
            volume      BIGINT,
            ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (ticker, trade_date)
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS staging.stock_anomalies (
            id            SERIAL PRIMARY KEY,
            ticker        VARCHAR(10) NOT NULL,
            trade_date    DATE        NOT NULL,
            is_anomaly    BOOLEAN     NOT NULL,
            anomaly_score NUMERIC(10, 6),
            UNIQUE (ticker, trade_date)
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS staging.stock_predictions (
            id              SERIAL PRIMARY KEY,
            ticker          VARCHAR(10)    NOT NULL,
            prediction_date DATE           NOT NULL,
            predicted_close NUMERIC(12, 4),
            lower_bound     NUMERIC(12, 4),
            upper_bound     NUMERIC(12, 4),
            UNIQUE (ticker, prediction_date)
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS staging.stock_insights (
            id           SERIAL PRIMARY KEY,
            ticker       VARCHAR(10) NOT NULL,
            insight_date DATE        NOT NULL,
            insight_text TEXT,
            UNIQUE (ticker, insight_date)
        )
        """,
    ]
    with conn.cursor() as cur:
        for sql in statements:
            cur.execute(sql)
    conn.commit()
    logger.info("Created staging tables: stock_prices_raw, stock_anomalies, stock_predictions, stock_insights")


def load_to_postgres(rows: list[tuple], insert_sql: str) -> bool:
    try:
        conn = get_connection()
        cur = conn.cursor()
        for row in rows:
            cur.execute(insert_sql, row)
        conn.commit()
        cur.close()
        conn.close()
        logger.info(f"Loaded {len(rows)} rows successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to load data to Postgres: {e}")
        return False


def setup_database() -> None:
    logger.info("Setting up database...")
    conn = get_connection()
    create_schemas(conn)
    create_tables(conn)
    conn.close()
    logger.info("Database setup complete")


if __name__ == "__main__":
    setup_database()
