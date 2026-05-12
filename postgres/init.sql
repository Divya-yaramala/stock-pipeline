-- ── Bootstrap script — runs once on first container start ─────────────────────

-- Create Airflow metadata database
SELECT 'CREATE DATABASE airflow_db'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'airflow_db') \gexec

-- ── Warehouse schemas ─────────────────────────────────────────────────────────
\c warehouse

CREATE SCHEMA IF NOT EXISTS raw;
CREATE SCHEMA IF NOT EXISTS staging;
CREATE SCHEMA IF NOT EXISTS intermediate;
CREATE SCHEMA IF NOT EXISTS mart;
CREATE SCHEMA IF NOT EXISTS seeds;

-- ── Raw layer ─────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS raw.stock_prices (
    id            BIGSERIAL    PRIMARY KEY,
    symbol        VARCHAR(10)  NOT NULL,
    date          DATE         NOT NULL,
    open          NUMERIC(14, 4),
    high          NUMERIC(14, 4),
    low           NUMERIC(14, 4),
    close         NUMERIC(14, 4) NOT NULL,
    volume        BIGINT,
    s3_key        VARCHAR(500) DEFAULT '',
    _loaded_at    TIMESTAMPTZ  NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT uq_stock_prices_symbol_date UNIQUE (symbol, date)
);

CREATE INDEX IF NOT EXISTS idx_stock_prices_symbol
    ON raw.stock_prices (symbol);

CREATE INDEX IF NOT EXISTS idx_stock_prices_date
    ON raw.stock_prices (date);

-- ── Permissions ───────────────────────────────────────────────────────────────
GRANT USAGE ON SCHEMA raw, staging, intermediate, mart, seeds
    TO CURRENT_USER;

GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA raw
    TO CURRENT_USER;

GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA raw
    TO CURRENT_USER;
