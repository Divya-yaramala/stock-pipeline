# Adaptive Modeling Guide — Stock Pipeline

## Overview
The pipeline uses adaptive modeling that automatically
selects the best algorithm based on current market regime.

## Market Regimes

### Trending Regime
Condition: abs(momentum) > 2%
Characteristics:
- Strong directional price movement
- Low mean reversion
- Momentum indicators reliable

Best model: Gradient Boosting
Why: Handles sequential patterns and trend continuation

### Volatile Regime
Condition: std/mean > 3%
Characteristics:
- High price variability
- Unpredictable direction
- Risk of large losses

Best model: Ensemble (RF + GB + Linear)
Why: Averaging reduces individual model variance

### Mean-Reverting Regime
Condition: autocorrelation < -0.3
Characteristics:
- Prices revert to mean
- Oscillating pattern
- Bollinger Bands effective

Best model: Linear Regression
Why: Stable, interpretable, captures linear reversion

## Online Features

### Rolling Window Features (window=20)
| Feature | Formula | Signal |
|---|---|---|
| price_mean | mean(prices[-20:]) | Fair value |
| price_std | std(prices[-20:]) | Volatility |
| price_momentum | latest/oldest - 1 | Trend direction |
| volume_mean | mean(volumes[-20:]) | Avg activity |
| volume_ratio | latest/mean | Unusual activity |
| price_acceleration | momentum change rate | Trend strength |

### Microstructure Features
| Feature | Description |
|---|---|
| bid_ask_spread_proxy | (high-low)/close |
| price_impact | volume × price change |
| trade_intensity | volume / time |

## Concept Drift Detection
Monitor: Recent MAE vs baseline MAE
Threshold: 20% increase → drift detected

Actions:
- < 20% increase: continue (no drift)
- 20-50% increase: adjust_weights (partial adaptation)
- > 50% increase: retrain (full model refresh)

## Running Adaptive Pipeline
python -c "
from ingestion.adaptive_model import run_adaptive_modeling
import os
prices = [185+i*0.5 for i in range(30)]
volumes = [1000000+i*5000 for i in range(30)]
result = run_adaptive_modeling('AAPL', prices, volumes, os.getenv('AWS_BUCKET_NAME'))
print('Regime:', result.get('regime'))
print('Model used:', result.get('model_used'))
print('Prediction:', result.get('prediction'))
"
