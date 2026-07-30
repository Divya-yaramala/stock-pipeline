# Predictive Monitoring Guide — Stock Pipeline

## Overview
The pipeline uses predictive analytics to alert BEFORE
issues become critical — not after they happen.

## Predictive Models

### 1. Anomaly Probability Predictor
Algorithm: Z-score → Sigmoid function
Input: Last 10 prices
Output: Probability 0-1 that next price is anomalous

How it works:
1. Calculate mean and std of recent 10 prices
2. Z-score = (latest - mean) / std
3. Probability = 1 / (1 + exp(-abs(z_score)))

Interpretation:
- < 0.5: Normal
- 0.5-0.7: Watch
- 0.7-0.9: Warning
- > 0.9: Critical

### 2. Quality Degradation Predictor
Algorithm: Linear trend extrapolation
Input: Last 7 quality scores
Output: Days until quality drops below threshold

How it works:
1. Fit linear trend to quality scores
2. If slope < 0 (declining): project forward
3. Calculate days until threshold (default 80%) is breached

Example:
Scores: [95, 93, 91, 89, 87, 85, 83] → slope = -2/day
Threshold: 80%
Current: 83% → 1.5 days until breach → Alert now!

### 3. SLA Risk Predictor
Algorithm: Moving average of completion times
Input: Last 7 pipeline completion hours
Output: Predicted completion hour for next run

If predicted hour > SLA target:
→ ALERT: SLA at risk for tomorrow

## Intelligent Monitoring Features

### Metric Correlation
Discovers relationships between metrics:
- quality_score ↔ anomaly_rate (usually negative)
- pipeline_duration ↔ data_volume (usually positive)
- sentiment_score ↔ price_return (variable)

### Root Cause Hypotheses
When metric degrades, generates hypotheses:
"quality_score dropped → possible cause: anomaly_rate increased (correlation: 0.85)"
"quality_score dropped → possible cause: pipeline_duration increased (correlation: 0.72)"

### Health Fingerprinting
MD5 hash of all current metric values
Same fingerprint = same health state
Different fingerprint = something changed

Daily fingerprint comparison:
- Match: normal operation
- Mismatch: investigate what changed

## Running Predictions
```python
# Check anomaly probability for each ticker
python -c "
from ingestion.predictive_alerter import predict_anomaly_probability
tickers_prices = {
    'AAPL': [185+i*0.1 for i in range(10)],
    'TSLA': [250, 248, 252, 249, 251, 248, 250, 247, 249, 280],
}
for ticker, prices in tickers_prices.items():
    prob = predict_anomaly_probability(prices)
    status = '⚠️ WARNING' if prob > 0.7 else '✅ Normal'
    print(f'{ticker}: {prob:.2%} {status}')
"
```
