import snowflake.connector
import os
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def get_snowflake_connection() -> snowflake.connector.connection.SnowflakeConnection:
    """Creates and returns a Snowflake connection using environment variables."""
    try:
        conn = snowflake.connector.connect(
            account=os.environ["SNOWFLAKE_ACCOUNT"],
            user=os.environ["SNOWFLAKE_USER"],
            password=os.environ["SNOWFLAKE_PASSWORD"],
            warehouse=os.environ.get("SNOWFLAKE_WAREHOUSE", "STOCK_PIPELINE_WH"),
            database=os.environ.get("SNOWFLAKE_DATABASE", "STOCK_PIPELINE_DB"),
            schema=os.environ.get("SNOWFLAKE_SCHEMA", "MARTS"),
            role=os.environ.get("SNOWFLAKE_ROLE", "SYSADMIN"),
        )
        logger.info("Successfully connected to Snowflake")
        return conn
    except Exception as e:
        logger.error("Failed to connect to Snowflake: %s", e)
        raise


def create_snowflake_objects(conn) -> None:
    """Creates database, schemas, and warehouse if they do not exist."""
    steps = [
        (
            "CREATE DATABASE IF NOT EXISTS STOCK_PIPELINE_DB",
            "Database STOCK_PIPELINE_DB",
        ),
        (
            "CREATE SCHEMA IF NOT EXISTS STOCK_PIPELINE_DB.RAW",
            "Schema RAW",
        ),
        (
            "CREATE SCHEMA IF NOT EXISTS STOCK_PIPELINE_DB.STAGING",
            "Schema STAGING",
        ),
        (
            "CREATE SCHEMA IF NOT EXISTS STOCK_PIPELINE_DB.MARTS",
            "Schema MARTS",
        ),
        (
            """CREATE WAREHOUSE IF NOT EXISTS STOCK_PIPELINE_WH
               WITH WAREHOUSE_SIZE = 'X-SMALL'
                    AUTO_SUSPEND  = 60
                    AUTO_RESUME   = TRUE""",
            "Warehouse STOCK_PIPELINE_WH (X-SMALL)",
        ),
    ]
    cur = conn.cursor()
    for sql, label in steps:
        cur.execute(sql)
        logger.info("Created %s", label)
    cur.close()


def create_snowflake_tables(conn) -> None:
    """Creates raw-layer tables mirroring the postgres staging schema."""
    tables = [
        (
            """CREATE TABLE IF NOT EXISTS STOCK_PIPELINE_DB.RAW.STOCK_PRICES (
                ID          NUMBER AUTOINCREMENT PRIMARY KEY,
                TICKER      VARCHAR(10)    NOT NULL,
                TRADE_DATE  DATE           NOT NULL,
                OPEN_PRICE  NUMBER(12, 4),
                HIGH_PRICE  NUMBER(12, 4),
                LOW_PRICE   NUMBER(12, 4),
                CLOSE_PRICE NUMBER(12, 4)  NOT NULL,
                VOLUME      NUMBER(20),
                INGESTED_AT TIMESTAMP_NTZ  DEFAULT CURRENT_TIMESTAMP(),
                UNIQUE (TICKER, TRADE_DATE)
            ) CLUSTER BY (TICKER, TRADE_DATE)""",
            "RAW.STOCK_PRICES",
        ),
        (
            """CREATE TABLE IF NOT EXISTS STOCK_PIPELINE_DB.RAW.STOCK_ANOMALIES (
                ID            NUMBER AUTOINCREMENT PRIMARY KEY,
                TICKER        VARCHAR(10)  NOT NULL,
                TRADE_DATE    DATE         NOT NULL,
                IS_ANOMALY    BOOLEAN      NOT NULL,
                ANOMALY_SCORE NUMBER(10, 6),
                UNIQUE (TICKER, TRADE_DATE)
            ) CLUSTER BY (TICKER, TRADE_DATE)""",
            "RAW.STOCK_ANOMALIES",
        ),
        (
            """CREATE TABLE IF NOT EXISTS STOCK_PIPELINE_DB.RAW.STOCK_PREDICTIONS (
                ID              NUMBER AUTOINCREMENT PRIMARY KEY,
                TICKER          VARCHAR(10)    NOT NULL,
                PREDICTION_DATE DATE           NOT NULL,
                PREDICTED_CLOSE NUMBER(12, 4),
                LOWER_BOUND     NUMBER(12, 4),
                UPPER_BOUND     NUMBER(12, 4),
                UNIQUE (TICKER, PREDICTION_DATE)
            ) CLUSTER BY (TICKER, PREDICTION_DATE)""",
            "RAW.STOCK_PREDICTIONS",
        ),
        (
            """CREATE TABLE IF NOT EXISTS STOCK_PIPELINE_DB.RAW.STOCK_INSIGHTS (
                ID           NUMBER AUTOINCREMENT PRIMARY KEY,
                TICKER       VARCHAR(10)  NOT NULL,
                INSIGHT_DATE DATE         NOT NULL,
                INSIGHT_TEXT TEXT,
                UNIQUE (TICKER, INSIGHT_DATE)
            ) CLUSTER BY (TICKER, INSIGHT_DATE)""",
            "RAW.STOCK_INSIGHTS",
        ),
    ]
    cur = conn.cursor()
    for sql, label in tables:
        cur.execute(sql)
        logger.info("Created table %s", label)
    cur.close()


def setup_snowflake() -> None:
    conn = get_snowflake_connection()
    try:
        create_snowflake_objects(conn)
        create_snowflake_tables(conn)
        logger.info("Snowflake setup complete")
    finally:
        conn.close()


if __name__ == "__main__":
    setup_snowflake()
