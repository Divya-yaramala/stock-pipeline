import streamlit as st

st.set_page_config(page_title="Portfolio Tracker", page_icon="💼")
st.title("💼 Portfolio Tracker")
st.markdown("Track your stock portfolio performance over time.")

PORTFOLIO = {
    "AAPL": 10,
    "MSFT": 5,
    "GOOGL": 3,
    "AMZN": 2,
    "TSLA": 8,
}

st.subheader("Current Holdings")
for ticker, shares in PORTFOLIO.items():
    st.metric(label=f"{ticker}", value=f"{shares} shares")
