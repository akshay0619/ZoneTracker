from datetime import timedelta

from tests.factories import D0, run
from zonetracker.engine.engine import State

LEG_IN_BULL = (100, 110, 99, 109)    # exciting bullish, body 9/11
BASE_1 = (105, 108, 102, 106)        # boring, body 1/6
BASE_2 = (107, 112, 104, 110)        # boring, closes above base 1 (still joins: IN_BASE + boring)
BASE_3_EXC = (103, 109, 102.5, 108)  # exciting bullish but closes inside the base -> joins


def test_boring_candle_keeps_scanning():
    assert run(BASE_1).state is State.SCANNING


def test_exciting_candle_starts_leg_in():
    eng = run(LEG_IN_BULL)
    assert eng.state is State.TRACKING_LEG_IN
    assert (eng.leg_in_time, eng.leg_in_high, eng.leg_in_low, eng.leg_in_bullish) == (D0, 110, 99, True)


def test_consecutive_exciting_candle_replaces_leg_in():
    eng = run(LEG_IN_BULL, (112, 120, 111, 119))
    assert eng.leg_in_high == 120 and eng.leg_in_time == D0 + timedelta(days=1)


def test_boring_after_leg_in_starts_base_with_real_open_bodies():
    eng = run(LEG_IN_BULL, BASE_1)
    assert eng.state is State.IN_BASE
    assert (eng.base_high, eng.base_low, eng.base_count, eng.base_start_idx) == (108, 102, 1, 1)
    assert (eng.base_highest_body_top, eng.base_lowest_body_bottom) == (106, 105)


def test_base_grows_with_boring_and_inside_closing_exciting_candles():
    eng = run(LEG_IN_BULL, BASE_1, BASE_2, BASE_3_EXC)
    assert eng.state is State.IN_BASE and eng.base_count == 3
    assert (eng.base_high, eng.base_low) == (112, 102)
    assert (eng.base_highest_body_top, eng.base_lowest_body_bottom) == (110, 103)
    assert eng.base_largest_candle == 8  # BASE_2 range
    assert eng.base_end_time == D0 + timedelta(days=3)
    assert eng.leg_in_high == 110  # Leg In untouched while the base builds


def test_full_base_plus_boring_resets_to_scanning():
    eng = run(LEG_IN_BULL, BASE_1, BASE_2, BASE_3_EXC, (106, 109, 104, 107))
    assert eng.state is State.SCANNING


def test_full_base_plus_inside_exciting_becomes_new_leg_in():
    eng = run(LEG_IN_BULL, BASE_1, BASE_2, BASE_3_EXC, (110, 111, 103, 104))
    assert eng.state is State.TRACKING_LEG_IN
    assert not eng.leg_in_bullish and eng.leg_in_high == 111
