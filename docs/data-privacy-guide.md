# Data Privacy Guide — Stock Pipeline

## Overview
The stock pipeline handles financial data which requires
careful privacy management even though it contains no PII.

## Privacy Policies

| Policy | Classification | Retention | Encryption |
|---|---|---|---|
| financial_data | CONFIDENTIAL | 365 days | ✅ Required |
| ml_features | INTERNAL | 90 days | ❌ Optional |
| audit_logs | CONFIDENTIAL | 730 days | ✅ Required |
| cache_data | PUBLIC | 7 days | ❌ Optional |

## PII Patterns Detected

| PII Type | Example | Risk Level |
|---|---|---|
| Email | user@example.com | High |
| Phone | 555-123-4567 | High |
| SSN | 123-45-6789 | High |
| Credit Card | 4111-1111-1111-1111 | High |
| IP Address | 192.168.1.1 | Low |

## Why PII Scanning Matters
Even though stock price data has no PII:
- Audit logs may capture user actions with PII
- Error messages may accidentally include PII
- Test data may contain real PII
- Log files from yfinance API may include IPs

## Running Privacy Checks

```bash
# Full privacy check
python -c "from ingestion.data_privacy_manager import run_privacy_check; import os; print(run_privacy_check(os.getenv('AWS_BUCKET_NAME')))"

# Scan specific prefix
python -c "from ingestion.pii_detector import run_pii_scan; import os; print(run_pii_scan(os.getenv('AWS_BUCKET_NAME'), 'audit/'))"
```

## Data Classification Levels
- PUBLIC: Freely shareable (cache, public reports)
- INTERNAL: Internal use only (ML features, processed data)
- CONFIDENTIAL: Restricted access (financial data, audit logs)

## Anonymization
For data sharing or testing use anonymize_dataset:

```python
from ingestion.data_privacy_manager import anonymize_dataset
data = [{'ticker': 'AAPL', 'analyst_email': 'john@example.com', 'price': 185.0}]
print(anonymize_dataset(data, ['analyst_email']))
```
