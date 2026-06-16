import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Optional

import uvicorn
import yfinance as yf
from fastapi import FastAPI, WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

TICKERS = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"]

app = FastAPI(title="Stock Pipeline WebSocket Server")


async def get_live_price(ticker: str) -> Optional[dict]:
    try:
        info = yf.Ticker(ticker).fast_info
        price = getattr(info, "last_price", None)
        prev_close = getattr(info, "previous_close", None)
        if price is None:
            return None
        change_pct = ((price - prev_close) / prev_close * 100) if prev_close else 0.0
        return {
            "ticker": ticker,
            "price": round(float(price), 2),
            "change_pct": round(float(change_pct), 2),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        logger.error("Failed to fetch live price for %s: %s", ticker, e)
        return None


async def broadcast_prices(websocket: WebSocket, tickers: list) -> None:
    while True:
        prices = []
        for ticker in tickers:
            data = await get_live_price(ticker)
            if data:
                prices.append(data)

        payload = {
            "type": "PRICES",
            "data": prices,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        await websocket.send_text(json.dumps(payload))
        logger.info("Broadcast prices for %d tickers", len(prices))
        await asyncio.sleep(30)


@app.websocket("/ws/prices")
async def websocket_prices(websocket: WebSocket):
    await websocket.accept()
    client = websocket.client
    logger.info("Client connected to /ws/prices: %s", client)
    try:
        await broadcast_prices(websocket, TICKERS)
    except WebSocketDisconnect:
        logger.info("Client disconnected from /ws/prices: %s", client)
    except Exception as e:
        logger.error("WebSocket error on /ws/prices: %s", e)


@app.websocket("/ws/alerts")
async def websocket_alerts(websocket: WebSocket):
    await websocket.accept()
    client = websocket.client
    logger.info("Client connected to /ws/alerts: %s", client)
    try:
        while True:
            for ticker in TICKERS:
                alert = {
                    "type": "ALERT",
                    "ticker": ticker,
                    "message": f"Monitoring {ticker} — no unusual activity detected",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
                await websocket.send_text(json.dumps(alert))
            await asyncio.sleep(60)
    except WebSocketDisconnect:
        logger.info("Client disconnected from /ws/alerts: %s", client)
    except Exception as e:
        logger.error("WebSocket error on /ws/alerts: %s", e)


@app.get("/ws/status")
def ws_status():
    return {
        "websocket_url": "ws://localhost:8002/ws/prices",
        "alerts_url": "ws://localhost:8002/ws/alerts",
        "status": "running",
        "tickers": TICKERS,
    }


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8002)
