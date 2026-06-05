# REST API Documentation

## Base URL
http://localhost:8000

## Endpoints

### Health Check
GET /health
Response: {"status": "healthy", "timestamp": "2026-06-04T12:00:00"}

### Get All Tickers
GET /tickers
Response: ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"]

### Get Stock Prices
GET /prices/{ticker}?days=30
Response: List of StockPrice objects

### Get Anomalies
GET /anomalies/{ticker}?days=30
Response: List of AnomalyResult objects

### Get Predictions
GET /predictions/{ticker}
Response: List of PredictionResult objects

### Get Insights
GET /insights/{ticker}
Response: Latest LLM insight text

### Get Summary
GET /summary/{ticker}
Response: Combined price + anomaly + prediction + insight

## Running Locally
uvicorn api.main:app --reload --port 8000

## Swagger UI
http://localhost:8000/docs

## Authentication
Currently no authentication required.
Future: Add API key authentication.
