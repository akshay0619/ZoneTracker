import pytest

from zonetracker.engine.candles import classify_candle


def test_exciting_bullish():
    ct = classify_candle(o=100, h=110, l=99, c=109)  # body 9 of range 11
    assert ct.is_exciting and ct.is_exciting_bullish
    assert not ct.is_boring and not ct.is_exciting_bearish
    assert ct.body_ratio == pytest.approx(9 / 11 * 100)


def test_exciting_bearish():
    ct = classify_candle(o=109, h=110, l=99, c=100)
    assert ct.is_exciting and ct.is_exciting_bearish
    assert not ct.is_exciting_bullish


def test_boring_small_body():
    ct = classify_candle(o=100, h=110, l=90, c=102)  # body 2 of range 20
    assert ct.is_boring and not ct.is_exciting
    assert not ct.is_exciting_bullish and not ct.is_exciting_bearish


def test_exactly_half_body_is_boring():
    # Pine uses a strict ">" so a 50% body is boring
    ct = classify_candle(o=100, h=102, l=100, c=101)
    assert ct.is_boring
    assert ct.body_ratio == pytest.approx(50.0)


def test_zero_range_is_exciting_but_directionless():
    ct = classify_candle(o=100, h=100, l=100, c=100)
    assert ct.is_exciting and not ct.is_boring
    assert not ct.is_exciting_bullish and not ct.is_exciting_bearish
    assert ct.body_ratio == 100.0


def test_doji_with_range_is_boring():
    ct = classify_candle(o=100, h=105, l=95, c=100)
    assert ct.is_boring
    assert ct.body_ratio == 0.0
