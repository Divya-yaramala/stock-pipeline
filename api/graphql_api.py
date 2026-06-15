import logging
import os
from typing import List, Optional

import psycopg2
import strawberry
import uvicorn
from fastapi import FastAPI
from strawberry.fastapi import GraphQLRouter

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

TICKERS = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"]


def _get_conn():
    return psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=int(os.getenv("POSTGRES_PORT", "5432")),
        dbname=os.getenv("POSTGRES_DB", "stock_pipeline"),
        user=os.getenv("POSTGRES_USER", "pipeline_user"),
        password=os.getenv("POSTGRES_PASSWORD", ""),
    )


@strawberry.type
class StockPrice:
    ticker: str
    trade_date: str
    open_price: float
    high_price: float
    low_price: float
    close_price: float
    volume: int


@strawberry.type
class AnomalyResult:
    ticker: str
    trade_date: str
    is_anomaly: bool
    anomaly_score: float
    anomaly_label: str


@strawberry.type
class TechnicalIndicators:
    ticker: str
    date: str
    sma_20: Optional[float]
    rsi_14: Optional[float]
    macd: Optional[float]


@strawberry.type
class PortfolioSummary:
    total_value: float
    daily_return_pct: float
    top_holding: str
    quality_score: float


@strawberry.type
class Query:
    @strawberry.field
    def stock_prices(self, ticker: str, days: int = 30) -> List[StockPrice]:
        try:
            conn = _get_conn()
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT ticker, trade_date::text, open_price, high_price,
                       low_price, close_price, volume
                FROM staging.stock_prices_raw
                WHERE ticker = %s
                ORDER BY trade_date DESC
                LIMIT %s
                """,
                (ticker.upper(), days),
            )
            rows = cursor.fetchall()
            cursor.close()
            conn.close()
            return [
                StockPrice(
                    ticker=r[0],
                    trade_date=r[1],
                    open_price=float(r[2]),
                    high_price=float(r[3]),
                    low_price=float(r[4]),
                    close_price=float(r[5]),
                    volume=int(r[6]),
                )
                for r in rows
            ]
        except Exception as e:
            logger.error("stock_prices query failed: %s", e)
            return []

    @strawberry.field
    def anomalies(self, ticker: str, only_anomalies: bool = False) -> List[AnomalyResult]:
        try:
            conn = _get_conn()
            cursor = conn.cursor()
            sql = """
                SELECT ticker, trade_date::text, is_anomaly, anomaly_score
                FROM staging.stock_anomalies
                WHERE ticker = %s
            """
            if only_anomalies:
                sql += " AND is_anomaly = TRUE"
            sql += " ORDER BY trade_date DESC LIMIT 30"
            cursor.execute(sql, (ticker.upper(),))
            rows = cursor.fetchall()
            cursor.close()
            conn.close()
            return [
                AnomalyResult(
                    ticker=r[0],
                    trade_date=r[1],
                    is_anomaly=bool(r[2]),
                    anomaly_score=float(r[3]),
                    anomaly_label="ANOMALY" if r[2] else "NORMAL",
                )
                for r in rows
            ]
        except Exception as e:
            logger.error("anomalies query failed: %s", e)
            return []

    @strawberry.field
    def portfolio_summary(self) -> PortfolioSummary:
        return PortfolioSummary(
            total_value=125_430.50,
            daily_return_pct=1.23,
            top_holding="AAPL",
            quality_score=94.5,
        )

    @strawberry.field
    def tickers(self) -> List[str]:
        return TICKERS


schema = strawberry.Schema(query=Query)
graphql_app = GraphQLRouter(schema)

app = FastAPI(title="Stock Pipeline GraphQL API")
app.include_router(graphql_app, prefix="/graphql")


@app.get("/health")
def health():
    return {"status": "healthy"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)
