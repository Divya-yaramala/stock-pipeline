# API Versioning Guide — Stock Pipeline

## Current Version: 2.0.0

## Version History
| Version | Day | Changes |
|---|---|---|
| 1.0.0 | Day 26 | Initial 7 endpoints (health, prices, anomalies, predictions, insights, sentiment, summary) |
| 2.0.0 | Day 68 | Added 6 endpoints (quality-gates, feature-flags, data-products, events, pipeline-health, privacy-scan) |

## Endpoint Categories
| Category | Endpoints | Purpose |
|---|---|---|
| system | /health, /feature-flags | System status |
| market_data | /prices, /summary | Stock price data |
| ml | /anomalies, /predictions | ML model outputs |
| ai | /insights | GPT summaries |
| nlp | /sentiment | News sentiment |
| quality | /quality-gates | Data quality |
| governance | /data-products | Data mesh |
| observability | /events/summary, /pipeline-health | Monitoring |
| security | /privacy-scan | PII detection |

## Swagger UI
Interactive API docs available at:
http://localhost:8000/docs

## API Clients

### Python Client Example
```python
import requests

BASE_URL = "http://localhost:8000"

# Get stock prices
response = requests.get(f"{BASE_URL}/prices/AAPL", params={"days": 30})
prices = response.json()

# Get anomalies
response = requests.get(f"{BASE_URL}/anomalies/AAPL")
anomalies = response.json()

# Get pipeline health
response = requests.get(f"{BASE_URL}/pipeline-health")
health = response.json()

# Get feature flags
response = requests.get(f"{BASE_URL}/feature-flags")
flags = response.json()
```

### JavaScript Client Example
```javascript
const BASE_URL = 'http://localhost:8000';

// Get predictions
const response = await fetch(`${BASE_URL}/predictions/AAPL`);
const predictions = await response.json();

// Get data products
const resp = await fetch(`${BASE_URL}/data-products`);
const products = await resp.json();
```

## Future API Plans
- v3.0.0: Add POST endpoints for triggering pipeline steps
- v3.0.0: Add authentication (API keys)
- v3.0.0: Add rate limiting
- v4.0.0: Add WebSocket subscriptions endpoint
