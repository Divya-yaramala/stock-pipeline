import time
from datetime import date, timedelta
from typing import Any, Optional

import pandas as pd
import plotly.graph_objects as go
import psycopg2
import streamlit as st
import yfinance as yf

from dashboard.config import (
    ANOMALY_COLOR,
    PREDICTION_COLOR,
    REFRESH_INTERVAL,
    TICKER_COLORS,
    TICKER_NAMES,
    TICKERS,
)

st.set_page_config(
    page_title="Stock Intelligence Dashboard",
    layout="wide",
    page_icon="📈",
)


def get_db_connection() -> Optional[Any]:
    import os

    try:
        return psycopg2.connect(
            host=os.getenv("POSTGRES_HOST", "localhost"),
            port=int(os.getenv("POSTGRES_PORT", "5432")),
            database=os.getenv("POSTGRES_DB", "stocks"),
            user=os.getenv("POSTGRES_USER", "postgres"),
            password=os.getenv("POSTGRES_PASSWORD", ""),
        )
    except Exception:
        return None


def load_stock_prices(conn: Optional[Any], ticker: str, days: int) -> pd.DataFrame:
    if conn is None:
        return pd.DataFrame()
    start_date = date.today() - timedelta(days=days)
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT trade_date, open_price, high_price, low_price,
                       close_price, volume
                FROM stock_prices
                WHERE ticker = %s AND trade_date >= %s
                ORDER BY trade_date ASC
                """,
                (ticker, start_date),
            )
            rows = cur.fetchall()
            if not rows:
                return pd.DataFrame()
            return pd.DataFrame(
                rows,
                columns=["trade_date", "open", "high", "low", "close", "volume"],
            )
    except Exception:
        return pd.DataFrame()


def load_anomalies(conn: Optional[Any], ticker: str, days: int) -> pd.DataFrame:
    if conn is None:
        return pd.DataFrame()
    start_date = date.today() - timedelta(days=days)
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT trade_date, close_price, is_anomaly, anomaly_score
                FROM stock_anomalies
                WHERE ticker = %s AND trade_date >= %s AND is_anomaly = TRUE
                ORDER BY trade_date DESC
                """,
                (ticker, start_date),
            )
            rows = cur.fetchall()
            if not rows:
                return pd.DataFrame(
                    columns=["trade_date", "close_price", "is_anomaly", "anomaly_score"]
                )
            return pd.DataFrame(
                rows, columns=["trade_date", "close_price", "is_anomaly", "anomaly_score"]
            )
    except Exception:
        return pd.DataFrame(columns=["trade_date", "close_price", "is_anomaly", "anomaly_score"])


def load_predictions(conn: Optional[Any], ticker: str) -> pd.DataFrame:
    if conn is None:
        return pd.DataFrame()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT forecast_date, predicted_price, lower_bound, upper_bound
                FROM stock_predictions
                WHERE ticker = %s AND forecast_date >= CURRENT_DATE
                ORDER BY forecast_date ASC
                LIMIT 5
                """,
                (ticker,),
            )
            rows = cur.fetchall()
            if not rows:
                return pd.DataFrame(
                    columns=["forecast_date", "predicted_price", "lower_bound", "upper_bound"]
                )
            return pd.DataFrame(
                rows, columns=["forecast_date", "predicted_price", "lower_bound", "upper_bound"]
            )
    except Exception:
        return pd.DataFrame(
            columns=["forecast_date", "predicted_price", "lower_bound", "upper_bound"]
        )


def fetch_live_price(ticker: str) -> Optional[dict]:
    try:
        data = yf.Ticker(ticker)
        hist = data.history(period="2d")
        if hist.empty:
            return None
        current = float(hist["Close"].iloc[-1])
        previous = float(hist["Close"].iloc[-2]) if len(hist) > 1 else current
        delta = current - previous
        delta_pct = (delta / previous) * 100 if previous != 0 else 0.0
        return {
            "price": current,
            "delta": delta,
            "delta_pct": delta_pct,
            "volume": int(hist["Volume"].iloc[-1]),
        }
    except Exception:
        return None


def main() -> None:
    st.title("📈 Stock Intelligence Dashboard")
    st.markdown("Real-time monitoring · AI anomaly detection · 5-day price forecasts")

    st.sidebar.header("Controls")
    selected_ticker = st.sidebar.selectbox(
        "Select Ticker",
        TICKERS,
        format_func=lambda t: f"{t} — {TICKER_NAMES[t]}",
    )
    days_options = {"7 days": 7, "30 days": 30, "90 days": 90}
    selected_label = st.sidebar.selectbox("Date Range", list(days_options.keys()), index=1)
    days = days_options[selected_label]
    auto_refresh = st.sidebar.toggle("Auto-Refresh (60s)", value=False)
    show_anomalies = st.sidebar.checkbox("Show Anomalies", value=True)
    show_predictions = st.sidebar.checkbox("Show Predictions", value=True)

    conn = get_db_connection()
    prices_df = load_stock_prices(conn, selected_ticker, days)
    anomalies_df = load_anomalies(conn, selected_ticker, days)
    predictions_df = load_predictions(conn, selected_ticker)
    live = fetch_live_price(selected_ticker)

    k1, k2, k3, k4 = st.columns(4)
    if live:
        k1.metric(
            "Current Price",
            f"${live['price']:.2f}",
            f"{live['delta']:+.2f} ({live['delta_pct']:+.2f}%)",
        )
    else:
        k1.metric("Current Price", "N/A")

    if not prices_df.empty:
        k2.metric("30-Day High", f"${prices_df['high'].max():.2f}")
        k3.metric("30-Day Low", f"${prices_df['low'].min():.2f}")
        k4.metric(
            "Today's Volume",
            f"{int(prices_df['volume'].iloc[-1]):,}" if not prices_df.empty else "N/A",
        )
    else:
        k2.metric("30-Day High", "N/A")
        k3.metric("30-Day Low", "N/A")
        k4.metric("Today's Volume", "N/A")

    st.subheader(f"{selected_ticker} Price Chart")
    color = TICKER_COLORS.get(selected_ticker, "#1f77b4")
    fig = go.Figure()

    if not prices_df.empty:
        fig.add_trace(
            go.Scatter(
                x=prices_df["trade_date"],
                y=prices_df["close"],
                mode="lines",
                name="Close Price",
                line=dict(color=color, width=2),
            )
        )
        if show_anomalies and not anomalies_df.empty:
            fig.add_trace(
                go.Scatter(
                    x=anomalies_df["trade_date"],
                    y=anomalies_df["close_price"],
                    mode="markers",
                    name="Anomaly",
                    marker=dict(color=ANOMALY_COLOR, size=10, symbol="x"),
                )
            )
        if show_predictions and not predictions_df.empty:
            fig.add_trace(
                go.Scatter(
                    x=predictions_df["forecast_date"],
                    y=predictions_df["predicted_price"],
                    mode="lines+markers",
                    name="Forecast",
                    line=dict(color=PREDICTION_COLOR, width=2, dash="dash"),
                )
            )

    fig.update_layout(
        xaxis_title="Date",
        yaxis_title="Price (USD)",
        height=400,
        margin=dict(l=0, r=0, t=30, b=0),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    st.plotly_chart(fig, use_container_width=True)

    col_a, col_b = st.columns(2)

    with col_a:
        st.subheader("Anomaly Summary")
        if not anomalies_df.empty:
            display_df = anomalies_df[["trade_date", "close_price", "anomaly_score"]].copy()
            display_df.columns = ["Date", "Price", "Anomaly Score"]
            st.dataframe(display_df, use_container_width=True)
        else:
            st.info("No anomalies detected in selected range.")

    with col_b:
        st.subheader("5-Day Price Forecast")
        if not predictions_df.empty:
            display_df = predictions_df[
                ["forecast_date", "predicted_price", "lower_bound", "upper_bound"]
            ].copy()
            display_df.columns = ["Date", "Predicted", "Lower", "Upper"]
            st.dataframe(display_df, use_container_width=True)
        else:
            st.info("No forecast data available.")

    col_c, col_d = st.columns(2)

    with col_c:
        st.subheader("Volume")
        if not prices_df.empty:
            vol_fig = go.Figure(
                go.Bar(
                    x=prices_df["trade_date"],
                    y=prices_df["volume"],
                    marker_color=color,
                )
            )
            vol_fig.update_layout(
                xaxis_title="Date",
                yaxis_title="Volume",
                height=300,
                margin=dict(l=0, r=0, t=10, b=0),
            )
            st.plotly_chart(vol_fig, use_container_width=True)
        else:
            st.info("No volume data available.")

    with col_d:
        st.subheader("Technical Indicators")
        if not prices_df.empty and len(prices_df) >= 20:
            close = prices_df["close"]
            sma20 = float(close.rolling(20).mean().iloc[-1])
            sma50 = float(close.rolling(min(50, len(close))).mean().iloc[-1])
            delta_series = close.diff()
            gain = delta_series.clip(lower=0).rolling(14).mean()
            loss = (-delta_series.clip(upper=0)).rolling(14).mean()
            rs = gain / loss.replace(0, float("nan"))
            rsi = float((100 - (100 / (1 + rs))).iloc[-1])
            st.metric("SMA 20", f"${sma20:.2f}")
            st.metric("SMA 50", f"${sma50:.2f}")
            st.metric("RSI (14)", f"{rsi:.1f}")
        else:
            st.info("Need ≥ 20 data points for indicators.")

    st.markdown("---")
    st.caption(
        f"Stock Intelligence Dashboard · {selected_ticker} · "
        f"Data refreshes every {REFRESH_INTERVAL}s when auto-refresh is enabled"
    )

    if auto_refresh:
        time.sleep(REFRESH_INTERVAL)
        st.rerun()


if __name__ == "__main__":
    main()
