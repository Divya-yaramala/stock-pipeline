"""Fetch OHLCV data from Yahoo Finance via yfinance."""
import logging
from datetime import date, timedelta

import pandas as pd
import yfinance as yf

logger = logging.getLogger(__name__)


def _last_weekday(ref: date) -> date:
    """Return the most recent weekday on or before ref."""
    d = ref
    while d.weekday() >= 5:
        d -= timedelta(days=1)
    return d


def fetch_stock_data(
    symbols: list[str],
    target_date: date | None = None,
    lookback_days: int = 1,
) -> pd.DataFrame:
    """
    Fetch OHLCV data for given symbols ending on target_date.

    Args:
        symbols: Ticker symbols to fetch.
        target_date: Latest date to include (defaults to last trading day).
        lookback_days: How many trading days of history to pull.

    Returns:
        DataFrame with columns: symbol, date, open, high, low, close, volume.
        Empty DataFrame when the market was closed for all symbols.
    """
    if target_date is None:
        target_date = _last_weekday(date.today() - timedelta(days=1))

    # Add calendar buffer so weekends / holidays don't shrink the window
    start = target_date - timedelta(days=lookback_days * 3)
    end = target_date + timedelta(days=1)  # yfinance end is exclusive

    logger.info(
        "Fetching %d symbol(s) | window %s → %s", len(symbols), start, target_date
    )

    frames: list[pd.DataFrame] = []
    for symbol in symbols:
        try:
            raw = yf.download(
                symbol,
                start=start.isoformat(),
                end=end.isoformat(),
                auto_adjust=True,
                progress=False,
                multi_level_index=False,
            )
            if raw.empty:
                logger.warning("No data returned for %s", symbol)
                continue

            df = raw.reset_index().rename(
                columns={
                    "Date": "date",
                    "Open": "open",
                    "High": "high",
                    "Low": "low",
                    "Close": "close",
                    "Volume": "volume",
                }
            )

            # Normalise tz-aware DatetimeTZDtype to plain date
            if hasattr(df["date"].dtype, "tz"):
                df["date"] = df["date"].dt.tz_localize(None)
            df["date"] = pd.to_datetime(df["date"]).dt.date

            df = (
                df[df["date"] <= target_date]
                .tail(lookback_days)
                .assign(symbol=symbol)[["symbol", "date", "open", "high", "low", "close", "volume"]]
                .dropna(subset=["close"])
            )

            frames.append(df)
            logger.info("  ✓ %s — %d row(s)", symbol, len(df))

        except Exception:
            logger.exception("Failed to fetch %s", symbol)

    if not frames:
        logger.warning("No data fetched for any symbol on %s", target_date)
        return pd.DataFrame(
            columns=["symbol", "date", "open", "high", "low", "close", "volume"]
        )

    result = pd.concat(frames, ignore_index=True)
    logger.info("Total rows fetched: %d", len(result))
    return result
