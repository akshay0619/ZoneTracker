from datetime import datetime

import numpy as np
import pandas as pd
import pytest

from zonetracker.data.provider import drop_incomplete_daily, normalize_ohlcv
from zonetracker.data.resample import resample


@pytest.fixture
def daily() -> pd.DataFrame:
    """Business days Mon 2025-12-29 .. Tue 2026-07-14; bar i: open i, high i+1, low i-1, close i+0.5."""
    idx = pd.bdate_range("2025-12-29", "2026-07-14", name="date")
    i = np.arange(len(idx), dtype=float)
    return pd.DataFrame({"open": i, "high": i + 1, "low": i - 1, "close": i + 0.5, "volume": 1.0}, index=idx)


def test_daily_is_passthrough(daily):
    assert resample(daily, "D") is daily


def test_weekly_monday_start_and_ohlc_aggregation(daily):
    w = resample(daily, "W")
    first = w.iloc[0]  # Mon 29 Dec .. Fri 2 Jan (crosses the year boundary)
    assert w.index[0] == pd.Timestamp("2025-12-29")
    assert (first.open, first.high, first.low, first.close, first.volume) == (0, 5, -1, 4.5, 5)


def test_weekly_drops_forming_week(daily):
    # Last data is Tue 14 Jul: week of 13 Jul is still forming
    assert resample(daily, "W").index[-1] == pd.Timestamp("2026-07-06")


@pytest.mark.parametrize("tf, first, last", [
    ("M", "2025-12-01", "2026-06-01"),
    ("Q", "2025-10-01", "2026-04-01"),
    ("H", "2025-07-01", "2026-01-01"),
    ("Y", "2025-01-01", "2025-01-01"),
])
def test_period_starts_and_forming_period_dropped(daily, tf, first, last):
    out = resample(daily, tf)
    assert out.index[0] == pd.Timestamp(first) and out.index[-1] == pd.Timestamp(last)


def test_half_year_covers_jan_to_jun(daily):
    h = resample(daily, "H").loc["2026-01-01"]
    jan_jun = daily.loc["2026-01-01":"2026-06-30"]
    assert h.open == jan_jun.open.iloc[0] and h.close == jan_jun.close.iloc[-1]
    assert h.high == jan_jun.high.max() and h.volume == len(jan_jun)


def test_normalize_flattens_multiindex_and_cleans():
    idx = pd.DatetimeIndex(["2026-01-02", "2026-01-01", "2026-01-05", "2026-01-05"], tz="Asia/Kolkata")
    cols = pd.MultiIndex.from_product([["Open", "High", "Low", "Close", "Adj Close", "Volume"], ["X.NS"]])
    vals = [[1, 2, 0.5, 1.5, 1.4, 10], [1, 2, 0.5, 1.5, 1.4, np.nan],
            [np.nan] * 6, [3, 4, 2.5, 3.5, 3.4, 30]]
    df = normalize_ohlcv(pd.DataFrame(vals, index=idx, columns=cols))
    assert list(df.columns) == ["open", "high", "low", "close", "volume"]
    assert df.index.tz is None and df.index.is_monotonic_increasing
    assert list(df.index.strftime("%Y-%m-%d")) == ["2026-01-01", "2026-01-02", "2026-01-05"]
    assert df.loc["2026-01-01", "volume"] == 0  # NaN volume (indices) -> 0
    assert df.loc["2026-01-05", "close"] == 3.5  # duplicate date: last row wins


def test_normalize_repairs_impossible_candles():
    raw = pd.DataFrame({"Open": [5.6], "High": [5.6], "Low": [6.68], "Close": [6.68], "Volume": [1]},
                       index=pd.DatetimeIndex(["2010-02-01"]))
    row = normalize_ohlcv(raw).iloc[0]
    assert (row.high, row.low) == (6.68, 5.6)


def test_drop_incomplete_daily(daily):
    last_day = daily.index[-1].to_pydatetime()
    assert len(drop_incomplete_daily(daily, last_day.replace(hour=11))) == len(daily) - 1
    assert len(drop_incomplete_daily(daily, last_day.replace(hour=18))) == len(daily)
    assert len(drop_incomplete_daily(daily, datetime(2026, 7, 15, 11))) == len(daily)
