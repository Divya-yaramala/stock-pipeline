import streamlit as st

st.set_page_config(page_title="Price Predictions", page_icon="📈")
st.title("📈 Price Predictions")
st.markdown("5-day Prophet price forecasts for all tickers.")
st.info("Connect PostgreSQL to see live prediction data.")

st.subheader("About the Model")
st.markdown("""
- **Algorithm:** Facebook Prophet
- **Forecast horizon:** 5 days
- **Confidence interval:** 80%
- **Features:** Historical OHLCV + trend + seasonality
- **Retrain frequency:** Weekly or on drift detection
""")
