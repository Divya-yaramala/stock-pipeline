# Data Dictionary — Stock Pipeline

## PostgreSQL Tables

### staging.stock_prices_raw
| Column | Type | Description |
|---|---|---|
| ticker | VARCHAR(10) | Stock ticker symbol (AAPL, MSFT, etc.) |
| trade_date | DATE | Trading date |
| open_price | NUMERIC(12,4) | Opening price USD |
| high_price | NUMERIC(12,4) | Daily high price USD |
| low_price | NUMERIC(12,4) | Daily low price USD |
| close_price | NUMERIC(12,4) | Closing price USD |
| volume | BIGINT | Total shares traded |
| source | VARCHAR(50) | Data source (yahoo_finance) |
| ingested_at | TIMESTAMP | When record was loaded |

### staging.stock_anomalies
| Column | Type | Description |
|---|---|---|
| ticker | VARCHAR(10) | Stock ticker symbol |
| trade_date | DATE | Date of anomaly |
| is_anomaly | BOOLEAN | True if anomaly detected |
| anomaly_score | NUMERIC(10,4) | Isolation Forest score |
| anomaly_label | VARCHAR(20) | SPIKE/DROP/VOLUME/NORMAL |
| detected_at | TIMESTAMP | Detection timestamp |

### staging.stock_predictions
| Column | Type | Description |
|---|---|---|
| ticker | VARCHAR(10) | Stock ticker symbol |
| prediction_date | DATE | Date predictions made |
| forecast_date | DATE | Date being forecast |
| predicted_price | NUMERIC(12,4) | Predicted close price |
| lower_bound | NUMERIC(12,4) | 80% confidence lower |
| upper_bound | NUMERIC(12,4) | 80% confidence upper |
| model_version | VARCHAR(50) | Model version used |

## S3 Prefixes
| Prefix | Description | Retention |
|---|---|---|
| raw/stocks/YYYY/MM/DD/ | Raw OHLCV data | 90 days |
| processed/anomalies/ | Anomaly results | 180 days |
| processed/predictions/ | Forecasts | 90 days |
| processed/insights/ | GPT summaries | 90 days |
| processed/sentiment/ | News sentiment | 30 days |
| processed/technical/ | Technical indicators | 30 days |
| processed/features/ | ML feature matrices | 30 days |
| models/registry/ | ML model artifacts | Indefinite |
| models/drift/ | Drift detection reports | 90 days |
| lineage/ | Data lineage records | Indefinite |
| audit/ | Security audit logs | Indefinite |
| cache/ | S3 cache entries | 7 days |
| chaos/ | Chaos engineering events | 30 days |

## Snowflake Tables

### MARTS.STOCK_DAILY_SUMMARY
| Column | Type | Description |
|---|---|---|
| ticker | VARCHAR(10) | Stock ticker |
| trade_date | DATE | Trading date |
| avg_price | NUMERIC(12,4) | Average close price |
| price_change_pct | NUMERIC(10,4) | Daily change % |
| anomaly_count | INTEGER | Anomalies detected |
| quality_score | NUMERIC(5,2) | Data quality score |
