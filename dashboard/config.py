from typing import Dict, List

TICKERS: List[str] = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"]

TICKER_NAMES: Dict[str, str] = {
    "AAPL": "Apple Inc.",
    "MSFT": "Microsoft Corp.",
    "GOOGL": "Alphabet Inc.",
    "AMZN": "Amazon.com Inc.",
    "TSLA": "Tesla Inc.",
}

TICKER_COLORS: Dict[str, str] = {
    "AAPL": "#555555",
    "MSFT": "#00A4EF",
    "GOOGL": "#4285F4",
    "AMZN": "#FF9900",
    "TSLA": "#CC0000",
}

REFRESH_INTERVAL: int = 60
DEFAULT_DAYS: int = 30
ANOMALY_COLOR: str = "red"
PREDICTION_COLOR: str = "orange"
