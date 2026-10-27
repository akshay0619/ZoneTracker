import math

from zonetracker.engine.swings import PivotDetector, SwingTracker, find_reversal


def feed(det: PivotDetector, values: list[float]) -> list[float | None]:
    return [det.update(v) for v in values]


def test_pivot_high_confirmed_right_bars_later():
    out = feed(PivotDetector(2, 2, is_high=True), [1, 2, 5, 2, 1, 0])
    assert out == [None, None, None, None, 5, None]


def test_pivot_low_mirror():
    out = feed(PivotDetector(2, 2, is_high=False), [5, 4, 1, 4, 5])
    assert out[-1] == 1


def test_equal_highs_rightmost_wins():
    # Windows of 3: [1,5,5] -> right tie fails; [5,5,1] -> left tie allowed
    out = feed(PivotDetector(1, 1, is_high=True), [1, 5, 5, 1])
    assert out == [None, None, None, 5]


def test_nan_in_window_blocks_pivot():
    out = feed(PivotDetector(1, 1, is_high=True), [math.nan, 5, 1, 0])
    assert out == [None, None, None, None]


def test_tracker_records_pivot_bar_not_confirm_bar():
    st = SwingTracker(swing_len=2)
    highs = [1, 2, 5, 2, 1]
    for i, h in enumerate(highs):
        st.update(i, h, l=0.5)
    assert st.high_prices == [5] and st.high_bars == [2]


def test_tracker_keeps_only_latest():
    st = SwingTracker(swing_len=1, keep=3)
    highs = [1, 5, 1, 6, 1, 7, 1, 8, 1]  # pivots 5, 6, 7, 8
    for i, h in enumerate(highs):
        st.update(i, h, l=0.0)
    assert st.high_prices == [6, 7, 8]


def test_find_reversal_most_recent_beyond_and_before_base():
    prices, bars = [130, 120, 125, 140], [5, 8, 12, 20]
    # Base starts at bar 15: bar-20 swing is excluded; most recent above 110 is 125
    assert find_reversal(prices, bars, before_bar=15, beyond=110, above=True) == 125
    # Only 130 lies above 128
    assert find_reversal(prices, bars, before_bar=15, beyond=128, above=True) == 130


def test_find_reversal_supply_and_none():
    prices, bars = [90, 95], [3, 6]
    assert find_reversal(prices, bars, before_bar=10, beyond=92, above=False) == 90
    assert find_reversal(prices, bars, before_bar=10, beyond=80, above=False) is None
    assert find_reversal([], [], before_bar=10, beyond=80, above=True) is None
