import logging
import os
from datetime import datetime
from typing import List, Optional

import psycopg2
import uvicorn
from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Stock Pipeline API", version="1.0.0")


class StockPrice(BaseModel):
    ticker: str
    trade_date: str
    open_price: float
    high_price: float
    low_price: float
    close_price: float
    volume: int


class AnomalyResult(BaseModel):
    ticker: str
    trade_date: str
    is_anomaly: bool
    anomaly_score: float
    anomaly_label: str


class PredictionResult(BaseModel):
    ticker: str
    prediction_date: str
    predicted_close: float
    lower_bound: float
    upper_bound: float


def get_db_connection():
    """Return a psycopg2 connection using environment variables."""
    conn = psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=int(os.getenv("POSTGRES_PORT", "5432")),
        dbname=os.getenv("POSTGRES_DB", "stockdb"),
        user=os.getenv("POSTGRES_USER", "postgres"),
        password=os.getenv("POSTGRES_PASSWORD", ""),
    )
    try:
        yield conn
    finally:
        conn.close()


@app.get("/health")
def health_check():
    """Return API health status."""
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}


@app.get("/tickers")
def get_tickers(conn=Depends(get_db_connection)):
    """Return list of distinct tickers available in the database."""
    with conn.cursor() as cur:
        cur.execute("SELECT DISTINCT ticker FROM staging.stock_prices_raw ORDER BY ticker")
        rows = cur.fetchall()
    return [row[0] for row in rows]


@app.get("/prices/{ticker}", response_model=List[StockPrice])
def get_prices(ticker: str, days: int = 30, conn=Depends(get_db_connection)):
    """Return the last N days of stock prices for a ticker."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT ticker, trade_date::text, open_price, high_price,
                   low_price, close_price, volume
            FROM staging.stock_prices_raw
            WHERE ticker = %s
              AND trade_date >= CURRENT_DATE - INTERVAL '%s days'
            ORDER BY trade_date DESC
            """,
            (ticker.upper(), days),
        )
        rows = cur.fetchall()
    return [
        StockPrice(
            ticker=r[0],
            trade_date=r[1],
            open_price=r[2],
            high_price=r[3],
            low_price=r[4],
            close_price=r[5],
            volume=r[6],
        )
        for r in rows
    ]


@app.get("/anomalies/{ticker}", response_model=List[AnomalyResult])
def get_anomalies(ticker: str, days: int = 30, conn=Depends(get_db_connection)):
    """Return anomaly detection results for a ticker."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT ticker, trade_date::text, is_anomaly, anomaly_score, anomaly_label
            FROM staging.stock_anomalies
            WHERE ticker = %s
              AND trade_date >= CURRENT_DATE - INTERVAL '%s days'
            ORDER BY trade_date DESC
            """,
            (ticker.upper(), days),
        )
        rows = cur.fetchall()
    return [
        AnomalyResult(
            ticker=r[0],
            trade_date=r[1],
            is_anomaly=r[2],
            anomaly_score=r[3],
            anomaly_label=r[4],
        )
        for r in rows
    ]


@app.get("/predictions/{ticker}", response_model=List[PredictionResult])
def get_predictions(ticker: str, conn=Depends(get_db_connection)):
    """Return latest price predictions for a ticker."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT ticker, prediction_date::text, predicted_close, lower_bound, upper_bound
            FROM staging.stock_predictions
            WHERE ticker = %s
            ORDER BY prediction_date DESC
            LIMIT 5
            """,
            (ticker.upper(),),
        )
        rows = cur.fetchall()
    return [
        PredictionResult(
            ticker=r[0],
            prediction_date=r[1],
            predicted_close=r[2],
            lower_bound=r[3],
            upper_bound=r[4],
        )
        for r in rows
    ]


@app.get("/insights/{ticker}")
def get_insights(ticker: str, conn=Depends(get_db_connection)):
    """Return the latest LLM market insight for a ticker."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT ticker, insight_date::text, insight_text
            FROM staging.stock_insights
            WHERE ticker = %s
            ORDER BY insight_date DESC
            LIMIT 1
            """,
            (ticker.upper(),),
        )
        row = cur.fetchone()
    if not row:
        return {"ticker": ticker.upper(), "insight_text": None}
    return {"ticker": row[0], "insight_date": row[1], "insight_text": row[2]}


@app.get("/summary/{ticker}")
def get_summary(ticker: str, conn=Depends(get_db_connection)):
    """Return a combined summary of latest price, anomaly status, prediction, and insight."""
    upper = ticker.upper()
    with conn.cursor() as cur:
        cur.execute(
            "SELECT close_price, trade_date::text FROM staging.stock_prices_raw "
            "WHERE ticker = %s ORDER BY trade_date DESC LIMIT 1",
            (upper,),
        )
        price_row = cur.fetchone()

        cur.execute(
            "SELECT is_anomaly FROM staging.stock_anomalies "
            "WHERE ticker = %s ORDER BY trade_date DESC LIMIT 1",
            (upper,),
        )
        anomaly_row = cur.fetchone()

        cur.execute(
            "SELECT predicted_close FROM staging.stock_predictions "
            "WHERE ticker = %s ORDER BY prediction_date DESC LIMIT 1",
            (upper,),
        )
        prediction_row = cur.fetchone()

        cur.execute(
            "SELECT insight_text FROM staging.stock_insights "
            "WHERE ticker = %s ORDER BY insight_date DESC LIMIT 1",
            (upper,),
        )
        insight_row = cur.fetchone()

    return {
        "ticker": upper,
        "latest_price": price_row[0] if price_row else None,
        "trade_date": price_row[1] if price_row else None,
        "is_anomaly": anomaly_row[0] if anomaly_row else None,
        "predicted_close": prediction_row[0] if prediction_row else None,
        "insight_text": insight_row[0] if insight_row else None,
    }


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
