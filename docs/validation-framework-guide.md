# Validation Framework Guide — Stock Pipeline

## Overview
The pipeline implements 8 validation rules across 6 categories
ensuring data quality at every pipeline stage.

## Validation Rules

| Rule | Category | Description |
|---|---|---|
| V001 schema_validation | structural | Required fields present + correct types |
| V002 range_validation | statistical | Values within expected ranges |
| V003 referential_integrity | relational | Ticker references valid |
| V004 temporal_consistency | temporal | Sequential dates, no future dates |
| V005 business_rules | business | High >= Low, Close in range |
| V006 completeness_check | completeness | No nulls in required fields |
| V007 uniqueness_check | uniqueness | No duplicate ticker+date combos |
| V008 statistical_outliers | statistical | No values beyond 5 std deviations |

## Business Rules (V005)
Financial data must satisfy:
- high_price >= low_price (always)
- close_price <= high_price (always)
- close_price >= low_price (always)
- open_price > 0 (always)
- volume > 0 (trading days)

## Field Ranges (V002)
| Field | Min | Max |
|---|---|---|
| open_price | 0.01 | 100,000 |
| high_price | 0.01 | 100,000 |
| low_price | 0.01 | 100,000 |
| close_price | 0.01 | 100,000 |
| volume | 1 | 10,000,000,000 |

## Contract Health Score
health_score = 100 - violation_rate_pct
- 100: No violations (perfect)
- 90-99: Minor issues (1-10% violation rate)
- 70-89: Needs attention
- < 70: Critical — investigate immediately

## Running Validation
```python
# Full validation suite
python -c "
from ingestion.pipeline_validator import run_validation_suite
records = [
    {'ticker': 'AAPL', 'trade_date': '2026-07-29',
     'open_price': 185.0, 'high_price': 190.0,
     'low_price': 183.0, 'close_price': 188.0, 'volume': 1000000}
]
result = run_validation_suite(records, 'AAPL')
print(f'Pass rate: {result[\"pass_rate_pct\"]:.1f}%')
for r in result['results']:
    status = '✅' if r['passed'] else '❌'
    print(f'  {status} {r[\"rule_id\"]}: {r.get(\"violations\", [])}')
"
```
