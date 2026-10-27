from datetime import timedelta

from tests.factories import D0, run
from zonetracker.engine.engine import EngineConfig, State, ZoneEngine

LEG_IN_BEAR = (110, 111, 99, 100)   # exciting bearish: high 111, low 99
BASE = (100, 103, 98, 101)          # boring: base 98-103 (size 5), bodies 100-101


def test_dbr_demand_zone_on_first_attempt():
    eng = run(LEG_IN_BEAR, BASE, (101, 115, 100, 114))  # close 114 > leg-in high 111
    assert eng.supply_zones == [] and len(eng.demand_zones) == 1
    z = eng.demand_zones[0]
    assert (z.pattern, z.proximal, z.distal) == ("DBR", 101, 98)
    assert (z.leg_out_count, z.leg_out_run, z.leg_out_confirm_bar) == (1, 1, 2)
    assert z.max_move == 14  # 115 - 101
    assert z.start_time == D0 + timedelta(days=1)  # base start: leg-in low 99 is not the distal
    assert z.reversal_level is None and not z.is_tested
    # Confirming candle becomes the new Leg In
    assert eng.state is State.TRACKING_LEG_IN and eng.leg_in_high == 115


def test_leg_in_low_sets_distal_and_start_time():
    eng = run((110, 111, 95, 97), (97, 101, 96, 98), (98, 113, 97, 112))
    z = eng.demand_zones[0]
    assert z.distal == 95 and z.start_time == D0


def test_rbr_continuation_ignores_leg_in_for_distal():
    eng = run((100, 110, 99, 109), (108, 111, 106, 109), (109, 122, 108, 121))
    z = eng.demand_zones[0]
    assert (z.pattern, z.proximal, z.distal) == ("RBR", 109, 106)


def test_rbd_supply_zone():
    eng = run((100, 110, 99, 109), (109, 112, 107, 110), (110, 111, 95, 96))
    z = eng.supply_zones[0]
    assert (z.pattern, z.proximal, z.distal, z.max_move) == ("RBD", 109, 112, 14)
    assert (z.top, z.bottom) == (112, 109)


def test_confirmation_on_second_attempt():
    eng = run(LEG_IN_BEAR, BASE, (101, 109, 100, 108), (108, 114, 107, 113))
    z = eng.demand_zones[0]
    assert (z.leg_out_count, z.leg_out_run, z.leg_out_high, z.leg_out_low) == (2, 2, 114, 100)
    assert z.max_move == 13


def test_leg_out_too_small_fails_after_three_attempts():
    wide_base = (105, 120, 100, 107)  # base size 20; each Leg Out candle is smaller
    eng = run((100, 110, 99, 109), wide_base, (110, 125, 109, 124), (124, 135, 123, 134), (134, 145, 133, 144))
    assert eng.demand_zones == []
    assert eng.state is State.TRACKING_LEG_IN and eng.leg_in_high == 145


def test_size_check_off_confirms_same_sequence():
    eng = run((100, 110, 99, 109), (105, 120, 100, 107), (110, 125, 109, 124),
              engine=ZoneEngine(EngineConfig(leg_out_size_pct=0)))
    assert len(eng.demand_zones) == 1


def test_boring_outside_base_turns_previous_attempt_into_leg_in():
    eng = run(LEG_IN_BEAR, BASE, (101, 109, 100, 108), (108, 110, 105, 107))
    assert eng.demand_zones == []
    assert eng.state is State.IN_BASE and eng.base_count == 1
    assert (eng.leg_in_time, eng.leg_in_high, eng.leg_in_low, eng.leg_in_bullish) == (D0 + timedelta(days=2), 109, 100, True)
    assert (eng.base_high, eng.base_low) == (110, 105)


def test_reversal_level_found_and_broken():
    candles = [(100, 104, 96, 101), (101, 130, 100, 102), (102, 104, 98, 101),  # swing high 130 at bar 1
               (101, 102, 90, 91), (91, 94, 89, 92), (92, 135, 91, 134)]        # DBR, leg out closes 134
    eng = run(*candles, engine=ZoneEngine(EngineConfig(swing_len=1)))
    z = eng.demand_zones[0]
    assert z.reversal_level == 130 and z.broke_reversal


def test_wick_to_wick_proximal():
    eng = run(LEG_IN_BEAR, BASE, (101, 115, 100, 114), engine=ZoneEngine(EngineConfig(wick_to_wick=True)))
    assert eng.demand_zones[0].proximal == 103
