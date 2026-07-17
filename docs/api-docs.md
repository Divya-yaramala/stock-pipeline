# API Documentation — Stock Pipeline v2.0.0

## Overview
The stock pipeline exposes 13 REST endpoints across 3 APIs:
- REST API (port 8000) — 13 endpoints
- GraphQL API (port 8001) — 4 resolvers
- WebSocket API (port 8002) — 2 streams

## REST API (Port 8000)
Start: `uvicorn api.main:app --reload --port 8000`
Docs: http://localhost:8000/docs

### Market Data Endpoints
| Method | Endpoint | Description |
|---|---|---|
| GET | /health | Health check |
| GET | /prices/{ticker} | Latest prices (days param) |
| GET | /summary/{ticker} | Combined summary |

### ML Endpoints
| Method | Endpoint | Description |
|---|---|---|
| GET | /anomalies/{ticker} | Anomaly detection results |
| GET | /predictions/{ticker} | 5-day Prophet forecasts |

### AI/NLP Endpoints
| Method | Endpoint | Description |
|---|---|---|
| GET | /insights/{ticker} | GPT-3.5 market insights |
| GET | /sentiment/{ticker} | News sentiment score |

### Quality and Governance Endpoints
| Method | Endpoint | Description |
|---|---|---|
| GET | /quality-gates/{ticker} | Quality gate check results |
| GET | /feature-flags | All feature flag values |
| GET | /data-products | Data mesh product registry |

### Observability Endpoints
| Method | Endpoint | Description |
|---|---|---|
| GET | /events/summary | Event bus summary for today |
| GET | /pipeline-health | Overall pipeline health score |
| GET | /privacy-scan/{prefix} | PII scan results for S3 prefix |

### Self-Documenting Endpoints
| Method | Endpoint | Description |
|---|---|---|
| GET | /api-docs/summary | API version and endpoint count |
| GET | /api-docs/endpoints/{category} | Endpoints by category |

## GraphQL API (Port 8001)
Start: `uvicorn api.graphql_api:app --reload --port 8001`
Playground: http://localhost:8001/graphql

### Example Queries
```graphql
query {
  tickers
  stockPrices(ticker: "AAPL", days: 7) {
    ticker
    closePrice
    tradeDate
  }
  anomalies(ticker: "AAPL", onlyAnomalies: true) {
    ticker
    isAnomaly
    anomalyScore
  }
  portfolioSummary {
    totalValue
    dailyReturnPct
  }
}
```

## WebSocket API (Port 8002)
Start: `uvicorn api.websocket_server:app --reload --port 8002`

### Endpoints
| Endpoint | Description | Interval |
|---|---|---|
| ws://localhost:8002/ws/prices | Live price stream | 30 seconds |
| ws://localhost:8002/ws/alerts | Live alert stream | 60 seconds |
| GET /ws/status | WebSocket health check | - |

### JavaScript Client Example
```javascript
const ws = new WebSocket('ws://localhost:8002/ws/prices');
ws.onmessage = (event) => {
  const prices = JSON.parse(event.data);
  console.log(prices);
};
```
