# Streaming Analytics Guide — Stock Pipeline

## Overview
The pipeline includes real-time streaming analytics using
sliding window algorithms for continuous price monitoring.

## Sliding Window Analytics

### How Sliding Windows Work
Window size: 20 prices (configurable)
New price → appended to window
Old price → automatically dropped (deque maxlen)

### Window Statistics
| Statistic | Description |
|---|---|
| mean | Average price in window |
| std | Standard deviation |
| min | Minimum price |
| max | Maximum price |
| latest | Most recent price |
| change_pct | % change from oldest to latest |

### Z-Score Anomaly Detection
- Z-score = (latest - mean) / std
- Z > 2.5 → SPIKE anomaly
- Z < -2.5 → DROP anomaly
- |Z| <= 2.5 → normal

## Real-Time Aggregation

### OHLCV Bar Aggregation
Groups prices into N-minute bars:
- Open: first price in window
- High: maximum price
- Low: minimum price
- Close: last price in window
- Volume: sum of volumes

### VWAP (Volume Weighted Average Price)
VWAP = Σ(price × volume) / Σ(volume)
Industry standard for intraday fair value

### Volume Profile
Distributes volume across price buckets.
Point of Control (POC) = price with most volume.
Indicates key support/resistance levels.

### Momentum Detection
Short MA vs Long MA comparison:
- short_period: 5 prices
- long_period: 20 prices
- bullish: short MA > long MA
- bearish: short MA < long MA

## Running Streaming Analytics
```bash
# Process 30 prices through sliding window
python -c "
from ingestion.streaming_analytics import process_price_stream
prices = [185+i*0.1 for i in range(30)]
print(process_price_stream('AAPL', prices, window_size=20))
"

# Calculate VWAP
python -c "
from ingestion.realtime_aggregator import calculate_vwap
prices = [{'price': 185.0+i, 'volume': 1000*(i+1)} for i in range(5)]
print('VWAP:', calculate_vwap(prices))
"
```
