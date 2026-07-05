# ADR 031 - Streamlit Real-Time Dashboard

## Status
Accepted

## Context
The pipeline produces rich data — prices, anomalies, predictions, and technical indicators — but
there was no visual interface for non-technical stakeholders to explore it. A dashboard needed to
connect to the PostgreSQL staging database, display live prices from yfinance, and surface AI
outputs (anomaly markers, forecast lines) in an interactive chart without requiring any frontend
engineering.

## Decision
Built a Streamlit dashboard (`dashboard/app.py`) with Plotly charts, a sidebar control panel, and
a 60-second auto-refresh loop. The dashboard is containerised in its own Dockerfile and registered
as a service in docker-compose on port 8503.

## Reasons
- Streamlit is pure Python — no JavaScript, HTML, or CSS required
- Plotly provides interactive charts (zoom, hover, pan) with a single `go.Figure()` call
- Auto-refresh via `time.sleep` + `st.rerun()` avoids a WebSocket server dependency
- Separate `dashboard/config.py` keeps ticker lists and colour constants out of app logic
- Docker service means the dashboard ships and scales with the rest of the stack

## Consequences
- `st.rerun()` causes a full page reload on every refresh cycle — acceptable for 60-second intervals
- Dashboard requires a live PostgreSQL connection; shows graceful "N/A" fallback when unavailable
- Streamlit's global `set_page_config` must be the first Streamlit call — tested by import order
