# Dashboard Preview — Stock Intelligence Dashboard

## Main Dashboard (http://localhost:8503)
The main dashboard shows:
- Live KPI metrics for selected ticker
- 30-day interactive price chart
- Anomaly overlay markers (red dots)
- Prophet prediction extension (dashed line)
- Volume bar chart
- Technical indicators summary

## Pages
- **Portfolio Tracker** — Holdings and daily returns
- **Anomaly Monitor** — Real-time anomaly alerts
- **Price Predictions** — 5-day Prophet forecasts

## How to Run
streamlit run dashboard/app.py --server.port 8503
Open: http://localhost:8503

## Color Scheme
- AAPL: #555555 (dark gray)
- MSFT: #00A4EF (Microsoft blue)
- GOOGL: #4285F4 (Google blue)
- AMZN: #FF9900 (Amazon orange)
- TSLA: #CC0000 (Tesla red)
