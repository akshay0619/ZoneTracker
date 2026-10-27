"""Candle classification, ported from the Pine `classifyCandle` (lines 141-147)."""
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CandleType:
    is_boring: bool
    is_exciting: bool
    is_exciting_bullish: bool
    is_exciting_bearish: bool
    body_ratio: float  # body as % of the high-low range


def classify_candle(o: float, h: float, l: float, c: float) -> CandleType:
    """Exciting = body strictly greater than 50% of range; zero-range candles count as exciting."""
    body_range = abs(c - o)
    candle_range = h - l
    is_zero_range = candle_range == 0
    ratio = 100.0 if is_zero_range else body_range / candle_range * 100
    exciting = is_zero_range or body_range > candle_range * 0.5
    return CandleType(
        is_boring=not exciting,
        is_exciting=exciting,
        is_exciting_bullish=exciting and c > o,
        is_exciting_bearish=exciting and c < o,
        body_ratio=ratio,
    )


@dataclass(frozen=True, slots=True)
class GapCandle:
    candle: CandleType  # classification after gap adjustment
    has_gap: bool
    adj_open: float     # previous close when the gap is filled, else the real open
    size: float         # high-low range including the filled gap


def classify_with_gap(
    o: float, h: float, l: float, c: float,
    prev_h: float | None, prev_l: float | None, prev_c: float | None,
) -> GapCandle:
    """Pine zoneEngine Section 1 (lines 239-245). Pass None for prev_* on the first bar.

    An exciting candle that gaps outside the previous range is re-measured from the
    previous close, so the gap counts as part of its body.
    """
    outside_prev = prev_h is not None and (l > prev_h or h < prev_l)
    has_gap = prev_c is not None and o != prev_c and outside_prev
    raw = classify_candle(o, h, l, c)
    fill_gap = has_gap and raw.is_exciting
    adj_open = prev_c if fill_gap else o
    size = max(h, adj_open) - min(l, adj_open)
    if not fill_gap:
        return GapCandle(raw, has_gap, adj_open, size)
    adjusted = CandleType(
        is_boring=False,
        is_exciting=True,
        is_exciting_bullish=c > adj_open,
        is_exciting_bearish=c < adj_open,
        body_ratio=abs(c - adj_open) / size * 100 if size else 100.0,  # Pine x/0 = na; never hit on clean data
    )
    return GapCandle(adjusted, has_gap, adj_open, size)
