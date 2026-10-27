import pandas as pd
import pytest

from zonetracker.data.resample import resample
from zonetracker.scan import forming_bars, scan_instrument

# DBR demand (proximal 101, distal 98) then a pullback closing 103.5 (2.48% above proximal)
CANDLES = [(110, 111, 99, 100), (100, 103, 98, 101), (101, 115, 100, 114), (114, 114.5, 103, 103.5)]


def frame(candles, start="2026-01-05") -> pd.DataFrame:
    idx = pd.bdate_range(start, periods=len(candles), name="date")
    df = pd.DataFrame(candles, columns=["open", "high", "low", "close"], index=idx, dtype=float)
    return df.assign(volume=0.0)


def test_forming_bars_are_the_open_week():
    idx = pd.bdate_range("2026-06-29", "2026-07-14", name="date")
    daily = pd.DataFrame({"open": 1.0, "high": 1.0, "low": 1.0, "close": 1.0, "volume": 0.0}, index=idx)
    w = resample(daily, "W")
    assert forming_bars(daily, "W", w).index.strftime("%m-%d").tolist() == ["07-13", "07-14"]
    assert forming_bars(daily, "D", daily).empty


def test_scan_finds_daily_approaching_without_grade_filter():
    rows = scan_instrument(frame(CANDLES), {"symbol": "TEST"}, graded_tfs=())
    assert len(rows) == 1
    r = rows[0]
    assert (r["symbol"], r["tf"], r["signal"], r["side"], r["pattern"]) == ("TEST", "D", "Approaching", "Demand", "DBR")
    assert (r["proximal"], r["distal"], r["close"], r["distance_pct"]) == (101, 98, 103.5, pytest.approx(2.48))
    assert r["grade"] == "B" and r["score"] == 10


def test_scan_daily_grade_filter_blocks_b_grade_approaching():
    assert scan_instrument(frame(CANDLES), {"symbol": "TEST"}) == []


def test_scan_reacting_when_price_back_inside():
    candles = CANDLES[:3] + [(114, 114.5, 99.5, 100)]  # closes inside 98-101, low above distal
    rows = scan_instrument(frame(candles), {"symbol": "TEST"})
    assert [(r["tf"], r["signal"], r["grade"]) for r in rows] == [("D", "Reacting", "B")]
