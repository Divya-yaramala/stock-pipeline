# Recommendation Engine Guide — Stock Pipeline

## Overview
The pipeline includes a profile-based stock recommendation
engine matching stocks to investor risk profiles.

## Investor Profiles

### Conservative Profile
- Risk tolerance: LOW
- Preferred sectors: Technology
- Min quality score: 90%
- Max volatility: 15%
- Best for: Capital preservation investors

### Moderate Profile
- Risk tolerance: MEDIUM
- Preferred sectors: Technology, Consumer Discretionary
- Min quality score: 80%
- Max volatility: 25%
- Best for: Balanced growth investors

### Aggressive Profile
- Risk tolerance: HIGH
- Preferred sectors: Technology, Consumer Discretionary
- Min quality score: 70%
- Max volatility: 40%
- Best for: Growth-focused investors

## Scoring Algorithm
Score = weighted combination of:
- Quality score match: 40% weight
- Volatility match: 30% weight
- Sector match: 20% weight
- Sentiment score: 10% weight

## Example Recommendations

### Conservative Profile Output
1. AAPL (score: 92.5)
   - Quality score 95% (above 90% threshold) ✅
   - Volatility 12% (below 15% threshold) ✅
   - Technology sector matches preference ✅

2. MSFT (score: 88.3)
   - Quality score 93% (above 90% threshold) ✅
   - Volatility 16% (slightly above 15%) ⚠️
   - Technology sector matches preference ✅

### Aggressive Profile Output
1. TSLA (score: 78.2)
   - High growth potential
   - Volatility 40% within aggressive threshold
   - Consumer Discretionary sector match

## Similar Ticker Finder
Uses Euclidean distance on normalized metrics:
- quality_score
- volatility
- sentiment_score

AAPL similar to: MSFT (distance: 0.12), GOOGL (distance: 0.31)

## Running Recommendations
```python
python -c "
from ingestion.stock_recommender import get_recommendations
metrics = {
    'AAPL': {'quality_score': 95.0, 'volatility': 0.12, 'sector': 'Technology', 'sentiment': 0.8},
    'TSLA': {'quality_score': 78.0, 'volatility': 0.40, 'sector': 'Consumer Discretionary', 'sentiment': 0.5},
}
recs = get_recommendations('conservative', metrics, top_n=3)
for r in recs:
    print(r['ticker'], '-', r['score'])
"
```
