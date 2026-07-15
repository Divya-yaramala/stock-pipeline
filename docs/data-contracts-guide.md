# Data Contracts Guide — Stock Pipeline

## Overview
Data contracts define formal agreements between data producers
and consumers. The pipeline has 1 registered contract covering
the core stock price event schema.

## Registered Contracts

### C001 — stock_price_event v1.0.0
Owner: data_engineering
Consumers: ml_team, analytics, trading

Schema:
| Field | Type | Required | Validation |
|---|---|---|---|
| ticker | string | ✅ | Pattern: ^[A-Z]{1,5}$ |
| trade_date | string | ✅ | Format: YYYY-MM-DD |
| open_price | float | ✅ | min: 0 |
| high_price | float | ✅ | min: 0 |
| low_price | float | ✅ | min: 0 |
| close_price | float | ✅ | min: 0 |
| volume | integer | ✅ | min: 0 |

SLA:
- Freshness: < 25 hours
- Quality threshold: > 95%

## Registered Schemas
| Schema | Version | Description |
|---|---|---|
| stock_prices_raw | 1.0.0 | Raw OHLCV data from Yahoo Finance |
| stock_anomalies | 1.0.0 | Isolation Forest anomaly results |
| stock_predictions | 1.0.0 | Prophet 5-day forecasts |
| stock_sentiment | 1.0.0 | Keyword-based sentiment scores |

## Schema Evolution Rules

### Safe Changes (backward compatible)
- Adding new optional fields
- Adding new enum values
- Relaxing constraints (e.g. min → lower min)

### Breaking Changes (require version bump)
- Removing required fields
- Changing field types
- Tightening constraints
- Renaming fields

## Validating Data Against Contract

```python
from ingestion.data_contract_manager import validate_against_contract
from ingestion.data_contract_manager import STOCK_PRICE_CONTRACT
data = {
    'ticker': 'AAPL',
    'trade_date': '2026-07-14',
    'open_price': 185.0,
    'high_price': 190.0,
    'low_price': 183.0,
    'close_price': 188.0,
    'volume': 1000000
}
result = validate_against_contract(data, STOCK_PRICE_CONTRACT)
print('Valid:', result['valid'])
print('Violations:', result['violations'])
```
