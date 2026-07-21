# Distributed Computing Guide — Stock Pipeline

## Overview
The pipeline uses ThreadPoolExecutor for parallel processing
across all 5 tickers simultaneously.

## Parallel Processing Architecture

### Sequential vs Parallel
Sequential (old):
```
AAPL → MSFT → GOOGL → AMZN → TSLA = 25 seconds
```

Parallel (new):
```
AAPL ┐
MSFT ├→ ThreadPoolExecutor(max_workers=5) → 5 seconds
GOOGL│
AMZN ├→ 5x speedup!
TSLA ┘
```

### Worker Configuration
| Task | Workers | Reason |
|---|---|---|
| Ticker processing | 5 | One per ticker |
| S3 uploads | 10 | I/O bound, more workers = faster |
| API calls | 5 | Rate limit friendly |

## Pipeline Bottleneck Analysis

### Typical Pipeline Step Times
| Step | Typical Duration | Bottleneck? |
|---|---|---|
| fetch_stocks | 3-8s | ⚠️ Sometimes |
| validate | 0.5-1s | ✅ Fast |
| anomaly_detect | 2-5s | ✅ OK |
| price_predict | 5-15s | ⚠️ Often |
| gpt_insights | 3-10s | ⚠️ API dependent |
| snowflake_sync | 5-20s | ⚠️ Network dependent |

### Optimization Recommendations
If fetch_stocks > 10s:
- Add caching for Yahoo Finance responses
- Reduce number of tickers
- Check Yahoo Finance rate limits

If price_predict > 15s:
- Reduce Prophet forecast horizon
- Use simpler model for less volatile tickers
- Cache predictions (they change slowly)

If snowflake_sync > 20s:
- Check Snowflake warehouse size (XSMALL vs SMALL)
- Reduce batch size
- Check network latency to Snowflake

## Running Distributed Pipeline
```bash
python -c "
from ingestion.distributed_task_manager import run_distributed_pipeline
import os
result = run_distributed_pipeline(
    ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA'],
    ['fetch', 'validate', 'anomaly', 'predict'],
    os.getenv('AWS_BUCKET_NAME')
)
print('Tickers processed:', result['tickers_processed'])
print('Total time:', result['total_seconds'], 'seconds')
"
```
