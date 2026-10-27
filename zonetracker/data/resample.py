"""Build higher-timeframe candles from daily OHLCV.

Matches Pine's HTF engines, which are fed `open[1]...` with lookahead_off: the period that
contains the latest daily bar is still forming and is always dropped.
"""
import pandas as pd

HTF = ("W", "M", "Q", "H", "Y")
_PERIOD_ALIAS = {"W": "W-SUN", "M": "M", "Q": "Q-DEC", "Y": "Y-DEC"}  # W-SUN = Monday..Sunday weeks


def period_start(index: pd.DatetimeIndex, tf: str) -> pd.DatetimeIndex:
    """Start date of the period each daily bar belongs to."""
    if tf == "H":
        month = (index.month - 1) // 6 * 6 + 1  # Jan-Jun -> 1, Jul-Dec -> 7
        return pd.DatetimeIndex(pd.to_datetime(pd.DataFrame({"year": index.year, "month": month, "day": 1})))
    return index.to_period(_PERIOD_ALIAS[tf]).start_time


def resample(daily: pd.DataFrame, tf: str) -> pd.DataFrame:
    """`daily` needs lowercase open/high/low/close/volume and a sorted, tz-naive DatetimeIndex."""
    if tf == "D":
        return daily
    keys = pd.DatetimeIndex(period_start(daily.index, tf), name="date")
    out = daily.groupby(keys).agg(
        open=("open", "first"), high=("high", "max"), low=("low", "min"),
        close=("close", "last"), volume=("volume", "sum"),
    )
    return out.iloc[:-1]
