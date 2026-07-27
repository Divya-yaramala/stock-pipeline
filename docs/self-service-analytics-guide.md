# Self-Service Analytics Guide — Stock Pipeline

## Overview
Business users can access pipeline metrics without
engineering support using the self-service analytics module.

## Available Metrics (8 total)

| ID | Metric | Category | Description |
|---|---|---|---|
| M001 | price_return_pct | price | Daily price return % |
| M002 | volatility_20d | risk | 20-day rolling volatility |
| M003 | anomaly_rate_pct | quality | % days with anomaly detected |
| M004 | sentiment_score | nlp | News sentiment score |
| M005 | prediction_accuracy_pct | ml | Forecast accuracy % |
| M006 | quality_score | quality | Overall data quality score |
| M007 | sla_compliance_pct | operations | SLA compliance % |
| M008 | pipeline_duration_minutes | operations | Pipeline run duration |

## Building Custom Reports

### Example: Risk Report for All Tickers
```python
python -c "
from ingestion.self_service_analytics import build_custom_report
import os, datetime
result = build_custom_report(
    metrics=['M001', 'M002', 'M003'],
    tickers=['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA'],
    date=datetime.datetime.now().strftime('%Y/%m/%d'),
    bucket=os.getenv('AWS_BUCKET_NAME')
)
print(result)
"
```

### Example: ML Quality Report
```python
python -c "
from ingestion.self_service_analytics import build_custom_report
import os, datetime
result = build_custom_report(
    metrics=['M005', 'M006', 'M007'],
    tickers=['AAPL', 'MSFT'],
    date=datetime.datetime.now().strftime('%Y/%m/%d'),
    bucket=os.getenv('AWS_BUCKET_NAME')
)
print(result)
"
```

## Comparing Metrics Across Tickers
```python
python -c "
from ingestion.self_service_analytics import compare_metrics
import os, datetime
result = compare_metrics(
    metric_id='M001',
    tickers=['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA'],
    date=datetime.datetime.now().strftime('%Y/%m/%d'),
    bucket=os.getenv('AWS_BUCKET_NAME')
)
print('Best ticker:', result['leader'])
"
```

## Data Mesh Access Workflow
1. Consumer team requests access:
   `request_data_access(product_id, requester, purpose, bucket)`

2. Data owner approves:
   `approve_access_request(request_id, approver, bucket)`

3. Consumer gets sample data:
   `get_data_product_sample(product_id, num_records=10, bucket)`

4. Producer publishes updates:
   `publish_data_product_update(product_id, version, changelog, bucket)`
