"""Swing pivots and the reversal level, ported from Pine lines 162-170 and 253-271."""
import math
from collections import deque


class PivotDetector:
    """Incremental ta.pivothigh / ta.pivotlow: feed one value per bar.

    Returns the pivot value on the bar where it is confirmed (`right` bars after the
    pivot), else None. Ties: the pivot must be strictly beyond the right-side bars and
    at least equal to the left-side bars, so among equal highs the rightmost wins.
    NOTE: tie-breaking must be confirmed against TradingView in the validation phase.
    """

    def __init__(self, left: int, right: int, is_high: bool):
        self.left, self.right, self.is_high = left, right, is_high
        self._win: deque[float] = deque(maxlen=left + right + 1)

    def update(self, value: float) -> float | None:
        self._win.append(value)
        if len(self._win) < self._win.maxlen or any(math.isnan(v) for v in self._win):
            return None
        vals = list(self._win)
        c = vals[self.left]
        left, right = vals[:self.left], vals[self.left + 1:]
        if self.is_high:
            ok = all(c >= v for v in left) and all(c > v for v in right)
        else:
            ok = all(c <= v for v in left) and all(c < v for v in right)
        return c if ok else None


class SwingTracker:
    """Keeps the last `keep` confirmed swing highs/lows with the bar index of the pivot."""

    def __init__(self, swing_len: int = 5, keep: int = 50):
        self.swing_len, self.keep = swing_len, keep
        self._ph = PivotDetector(swing_len, swing_len, is_high=True)
        self._pl = PivotDetector(swing_len, swing_len, is_high=False)
        self.high_prices: list[float] = []
        self.high_bars: list[int] = []
        self.low_prices: list[float] = []
        self.low_bars: list[int] = []

    def update(self, bar_index: int, h: float, l: float) -> None:
        ph, pl = self._ph.update(h), self._pl.update(l)
        if ph is not None:
            self._push(self.high_prices, self.high_bars, ph, bar_index - self.swing_len)
        if pl is not None:
            self._push(self.low_prices, self.low_bars, pl, bar_index - self.swing_len)

    def _push(self, prices: list[float], bars: list[int], price: float, bar: int) -> None:
        prices.append(price)
        bars.append(bar)
        if len(prices) > self.keep:
            prices.pop(0)
            bars.pop(0)


def find_reversal(prices: list[float], bars: list[int], before_bar: int,
                  beyond: float, above: bool) -> float | None:
    """Most recent swing left of `before_bar` lying beyond `beyond` (above for demand, below for supply)."""
    for price, bar in zip(reversed(prices), reversed(bars)):
        if bar < before_bar and (price > beyond if above else price < beyond):
            return price
    return None
