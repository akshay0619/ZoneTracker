"""Daily OHLCV providers. Only daily data is fetched; higher timeframes come from resample.py."""
from datetime import datetime, time
from typing import Protocol

import pandas as pd
import yfinance as yf

COLUMNS = ["open", "high", "low", "close", "volume"]
NSE_CLOSE_BUFFER = time(15, 45)  # NSE closes 15:30 IST; give Yahoo 15 minutes to settle the candle


class DataProvider(Protocol):
    def daily(self, symbol: str) -> pd.DataFrame: ...


def normalize_ohlcv(raw: pd.DataFrame) -> pd.DataFrame:
    """Flatten yfinance columns, lowercase them, drop NaN rows / duplicates, tz-naive sorted index."""
    df = raw.copy()
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df.columns = [str(c).lower() for c in df.columns]
    df = df[COLUMNS].dropna(subset=["open", "high", "low", "close"])
    df["volume"] = df["volume"].fillna(0)
    idx = pd.DatetimeIndex(df.index)
    df.index = (idx.tz_localize(None) if idx.tz is not None else idx).normalize().rename("date")
    df = df[~df.index.duplicated(keep="last")].sort_index().astype(float)
    # Yahoo occasionally ships impossible candles (e.g. high < low): widen high/low to cover O and C
    prices = df[["open", "high", "low", "close"]]
    df["high"], df["low"] = prices.max(axis=1), prices.min(axis=1)
    return df


def drop_incomplete_daily(df: pd.DataFrame, now_ist: datetime) -> pd.DataFrame:
    """Drop today's candle if fetched before the session has settled (Pine only uses confirmed bars)."""
    if len(df) and df.index[-1].date() == now_ist.date() and now_ist.time() < NSE_CLOSE_BUFFER:
        return df.iloc[:-1]
    return df


class YFinanceProvider:
    """Split-adjusted, NOT dividend-adjusted prices: matches TradingView's default chart settings."""

    def daily(self, symbol: str) -> pd.DataFrame:
        raw = yf.download(symbol, period="max", interval="1d", auto_adjust=False,
                          progress=False, multi_level_index=False)
        if raw is None or raw.empty:
            raise ValueError(f"No data returned for {symbol}")
        return drop_incomplete_daily(normalize_ohlcv(raw), _now_ist())

    def daily_many(self, symbols: list[str], chunk: int = 50) -> dict[str, pd.DataFrame]:
        """Batch download; symbols Yahoo returns nothing for are left out of the result."""
        out: dict[str, pd.DataFrame] = {}
        now_ist = _now_ist()
        for i in range(0, len(symbols), chunk):
            part = symbols[i:i + chunk]
            raw = yf.download(part, period="max", interval="1d", auto_adjust=False,
                              progress=False, group_by="ticker", threads=True)
            for sym in part:
                if sym not in raw.columns.get_level_values(0):
                    continue
                df = normalize_ohlcv(raw[sym])
                if len(df):
                    out[sym] = drop_incomplete_daily(df, now_ist)
        return out


def _now_ist() -> datetime:
    return pd.Timestamp.now(tz="Asia/Kolkata").tz_localize(None).to_pydatetime()
