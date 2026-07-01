# API Documentation — Stock Pipeline

## REST API (Port 8000)
Start: uvicorn api.main:app --reload --port 8000
Docs: http://localhost:8000/docs

### Endpoints
| Method | Endpoint | Description |
|---|---|---|
| GET | /health | Health check |
| GET | /prices/{ticker} | Latest stock prices |
| GET | /anomalies/{ticker} | Anomaly detection results |
| GET | /predictions/{ticker} | 5-day price predictions |
| GET | /insights/{ticker} | GPT market insights |
| GET | /sentiment/{ticker} | News sentiment score |
| GET | /summary/{ticker} | Combined ticker summary |

## GraphQL API (Port 8001)
Start: uvicorn api.graphql_api:app --reload --port 8001
Playground: http://localhost:8001/graphql

### Example Queries
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

## WebSocket API (Port 8002)
Start: uvicorn api.websocket_server:app --reload --port 8002

### Endpoints
| Endpoint | Description | Interval |
|---|---|---|
| ws://localhost:8002/ws/prices | Live price stream | 30 seconds |
| ws://localhost:8002/ws/alerts | Live alert stream | 60 seconds |
| GET /ws/status | WebSocket health check | - |

### JavaScript Client Example
const ws = new WebSocket('ws://localhost:8002/ws/prices');
ws.onmessage = (event) => {
  const prices = JSON.parse(event.data);
  console.log(prices);
};
