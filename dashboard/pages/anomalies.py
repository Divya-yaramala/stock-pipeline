import streamlit as st

st.set_page_config(page_title="Anomaly Monitor", page_icon="🚨")
st.title("🚨 Anomaly Monitor")
st.markdown("Real-time anomaly detection across all tickers.")
st.info("Connect PostgreSQL to see live anomaly data.")

TICKERS = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"]
for ticker in TICKERS:
    st.metric(label=ticker, value="No anomalies detected", delta="✅ Normal")
