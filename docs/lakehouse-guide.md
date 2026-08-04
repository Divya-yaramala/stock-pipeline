# Data Lakehouse Guide — Stock Pipeline

## Overview
The pipeline implements the medallion architecture with
3 data layers: Bronze, Silver, and Gold.

## Medallion Architecture

### 🥉 Bronze Layer (Raw)
Location: S3 lakehouse/bronze/YYYY/MM/DD/ticker/
Retention: 365 days
Contents: Exact raw data from Yahoo Finance API
Use cases:
- Reprocessing when bugs found in silver layer
- Audit trail of original API responses
- Data lineage starting point

### 🥈 Silver Layer (Clean)
Location: S3 lakehouse/silver/YYYY/MM/DD/ticker/
Retention: 730 days (2 years)
Contents: Validated data (quality score >= 80%)
Use cases:
- ML model training features
- Analytics and reporting
- Time series analysis

### 🥇 Gold Layer (Business)
Location: S3 lakehouse/gold/YYYY/MM/DD/ticker/
Retention: 1825 days (5 years)
Contents: Pre-aggregated business metrics
Use cases:
- Executive dashboards
- KPI tracking
- Business intelligence

## Data Flow
```
Yahoo Finance API
      ↓
Bronze (raw) → Validate → Silver (clean) → Aggregate → Gold (business)
      ↓               ↓                          ↓
  Always          Only if                  Daily OHLCV
  written       score >= 80%              summaries
```

## Delta Versioning
Every write creates a transaction log entry:
```
delta/log/ticker/version_timestamp.json
```

Contains:
- operation: INSERT, UPDATE, DELETE, SCHEMA_CHANGE
- records_added / records_deleted
- schema_changed: True/False
- timestamp

### Time Travel
Load table state as of any past date:
```python
python -c "
from ingestion.delta_versioner import time_travel_query
import os
records = time_travel_query('AAPL', '2026-06-01', os.getenv('AWS_BUCKET_NAME'))
print(f'AAPL had {len(records)} records as of 2026-06-01')
"
```

### Table Optimization
Compact small delta log files weekly:
```python
python -c "
from ingestion.delta_versioner import optimize_delta_table
import os
result = optimize_delta_table('AAPL', os.getenv('AWS_BUCKET_NAME'))
print('Files compacted:', result['files_compacted'])
"
```

## Cost Analysis
| Layer | Size | Retention | Monthly Cost |
|---|---|---|---|
| Bronze | ~50MB/year | 1 year | ~$0.02 |
| Silver | ~30MB/year | 2 years | ~$0.03 |
| Gold | ~5MB/year | 5 years | ~$0.01 |
| Delta log | ~1MB/year | indefinite | ~$0.001 |
| Total | | | ~$0.06/month |
