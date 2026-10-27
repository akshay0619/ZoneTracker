import pytest

from zonetracker.engine.candles import classify_with_gap

# Previous candle used by most tests: H 100, L 95, C 99
PREV = dict(prev_h=100, prev_l=95, prev_c=99)


def test_first_bar_has_no_gap():
    g = classify_with_gap(105, 110, 104, 109, None, None, None)
    assert not g.has_gap
    assert g.adj_open == 105 and g.size == 6


def test_overlapping_range_is_not_a_gap():
    # Opened above prev high but traded back into the prev range (gap filled intraday)
    g = classify_with_gap(103, 108, 99, 107, **PREV)
    assert not g.has_gap
    assert g.adj_open == 103


def test_gap_up_exciting_measured_from_prev_close():
    g = classify_with_gap(105, 110, 104, 109, **PREV)
    assert g.has_gap
    assert g.adj_open == 99
    assert g.size == 11  # 110 - 99
    assert g.candle.is_exciting_bullish
    assert g.candle.body_ratio == pytest.approx(10 / 11 * 100)


def test_gap_up_red_candle_flips_to_bullish():
    # Raw candle is exciting bearish, but it still closed far above prev close
    g = classify_with_gap(110, 111, 104, 105, **PREV)
    assert g.candle.is_exciting_bullish
    assert not g.candle.is_exciting_bearish


def test_gap_with_boring_candle_is_not_adjusted():
    g = classify_with_gap(105, 110, 101, 106, **PREV)
    assert g.has_gap
    assert g.candle.is_boring
    assert g.adj_open == 105 and g.size == 9


def test_gap_down_exciting_bearish():
    g = classify_with_gap(90, 91, 84, 85, prev_h=100, prev_l=95, prev_c=96)
    assert g.has_gap
    assert g.adj_open == 96 and g.size == 12  # 96 - 84
    assert g.candle.is_exciting_bearish
