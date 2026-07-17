import logging
import os
from datetime import datetime
from typing import Any, Dict, List

import psycopg2
import uvicorn
from fastapi import Depends, FastAPI
from pydantic import BaseModel

from api.api_docs import router as api_docs_router
from ingestion.data_product_manager import list_data_products
from ingestion.event_bus import get_event_summary
from ingestion.feature_flag_manager import get_all_flags
from ingestion.pii_detector import run_pii_scan
from ingestion.quality_gate import run_quality_gates
from ingestion.resource_manager import run_resource_check
from ingestion.sla_reporter import run_sla_reporting

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Stock Pipeline API", version="2.0.0")
app.include_router(api_docs_router)


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


def _bucket() -> str:
    return str(os.getenv("AWS_BUCKET_NAME", ""))


@app.get("/health")
def health_check() -> Dict[str, Any]:
    """Return API health status."""
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}


@app.get("/tickers")
def get_tickers(conn=Depends(get_db_connection)) -> List[str]:
    """Return list of distinct tickers available in the database."""
    with conn.cursor() as cur:
        cur.execute("SELECT DISTINCT ticker FROM staging.stock_prices_raw ORDER BY ticker")
        rows = cur.fetchall()
    return [row[0] for row in rows]


@app.get("/prices/{ticker}", response_model=List[StockPrice])
def get_prices(ticker: str, days: int = 30, conn=Depends(get_db_connection)) -> List[StockPrice]:
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
def get_anomalies(
    ticker: str, days: int = 30, conn=Depends(get_db_connection)
) -> List[AnomalyResult]:
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
def get_predictions(ticker: str, conn=Depends(get_db_connection)) -> List[PredictionResult]:
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
def get_insights(ticker: str, conn=Depends(get_db_connection)) -> Dict[str, Any]:
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


@app.get("/sentiment/{ticker}")
def get_sentiment(ticker: str, conn=Depends(get_db_connection)) -> Dict[str, Any]:
    """Return the latest news sentiment score for a ticker."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT ticker, analysis_date::text, sentiment_label, sentiment_score
            FROM staging.stock_sentiment
            WHERE ticker = %s
            ORDER BY analysis_date DESC
            LIMIT 1
            """,
            (ticker.upper(),),
        )
        row = cur.fetchone()
    if not row:
        return {"ticker": ticker.upper(), "sentiment_label": None, "sentiment_score": None}
    return {
        "ticker": row[0],
        "analysis_date": row[1],
        "sentiment_label": row[2],
        "sentiment_score": row[3],
    }


@app.get("/summary/{ticker}")
def get_summary(ticker: str, conn=Depends(get_db_connection)) -> Dict[str, Any]:
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


# ── New endpoints (v2) ─────────────────────────────────────────────────────────


@app.get("/quality-gates/{ticker}")
def get_quality_gates(ticker: str) -> Dict[str, Any]:
    """Run quality gate check for a ticker using sample metrics."""
    sample_metrics: Dict[str, Any] = {
        "hours_since_update": 2.0,
        "completeness_pct": 98.0,
        "quality_score": 91.0,
        "anomaly_rate_pct": 3.0,
        "prediction_accuracy_pct": 82.0,
    }
    return run_quality_gates(sample_metrics, ticker.upper())


@app.get("/feature-flags")
def get_feature_flags() -> Dict[str, Any]:
    """Return all current feature flag values — never exposes secrets."""
    return get_all_flags(_bucket())


@app.get("/data-products")
def get_data_products() -> List[Dict[str, Any]]:
    """List all registered data mesh products."""
    return list_data_products(_bucket())


@app.get("/events/summary")
def get_events_summary() -> Dict[str, Any]:
    """Return today's event bus summary grouped by event type."""
    today = datetime.utcnow().strftime("%Y/%m/%d")
    return get_event_summary(_bucket(), today)


@app.get("/pipeline-health")
def get_pipeline_health() -> Dict[str, Any]:
    """Return overall pipeline health combining quality gates, SLA, and resource checks."""
    bucket = _bucket()
    try:
        sla = run_sla_reporting(bucket)
        sla_compliance: float = float(sla.get("overall_compliance_pct", 0.0))
    except Exception:
        sla_compliance = 0.0

    try:
        resources = run_resource_check(bucket)
        resource_ok: bool = bool(resources.get("all_healthy", False))
    except Exception:
        resource_ok = False

    sample_metrics: Dict[str, Any] = {
        "hours_since_update": 2.0,
        "completeness_pct": 98.0,
        "quality_score": 91.0,
        "anomaly_rate_pct": 3.0,
        "prediction_accuracy_pct": 82.0,
    }
    try:
        gates = run_quality_gates(sample_metrics, "AAPL")
        gates_passed: int = int(gates.get("passed", 0))
        gates_total: int = int(gates.get("total", 1))
    except Exception:
        gates_passed, gates_total = 0, 1

    health_score = round(
        (gates_passed / gates_total * 40)
        + (sla_compliance / 100 * 40)
        + (20 if resource_ok else 0),
        1,
    )
    return {
        "health_score": health_score,
        "gates_passed": gates_passed,
        "gates_total": gates_total,
        "sla_compliance_pct": sla_compliance,
        "resources_healthy": resource_ok,
        "checked_at": datetime.utcnow().isoformat(),
    }


@app.get("/privacy-scan/{prefix:path}")
def get_privacy_scan(prefix: str) -> Dict[str, Any]:
    """Scan an S3 prefix for PII and return scan results."""
    return run_pii_scan(_bucket(), prefix)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
