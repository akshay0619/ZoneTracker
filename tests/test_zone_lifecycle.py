from tests.factories import make_zone
from zonetracker.engine.zones import trim_zones, update_zones

# Demand zone: proximal 101, distal 97, confirmed on bar 10.  Supply: proximal 99, distal 103.


def test_confirm_bar_itself_is_skipped():
    zones = [make_zone()]
    update_zones(zones, bar_index=10, h=105, l=90, c=95, ex_bull=False, ex_bear=True)
    assert len(zones) == 1 and not zones[0].is_tested


def test_touching_proximal_marks_tested():
    zones = [make_zone()]
    update_zones(zones, 11, h=106, l=101, c=104, ex_bull=False, ex_bear=False)
    assert zones[0].is_tested


def test_wick_exactly_on_distal_is_not_a_breach():
    zones = [make_zone()]
    update_zones(zones, 11, h=103, l=97, c=99, ex_bull=False, ex_bear=False)
    assert len(zones) == 1 and zones[0].is_tested


def test_demand_wick_breach_removes_zone():
    zones = [make_zone()]
    update_zones(zones, 11, h=103, l=96.95, c=99, ex_bull=False, ex_bear=False)
    assert zones == []


def test_close_mode_ignores_wick_breach():
    zones = [make_zone()]
    update_zones(zones, 11, h=103, l=96, c=99, ex_bull=False, ex_bear=False, use_wick=False)
    assert len(zones) == 1
    update_zones(zones, 12, h=99, l=95, c=96.5, ex_bull=False, ex_bear=True, use_wick=False)
    assert zones == []


def test_supply_touch_and_breach():
    zones = [make_zone(is_demand=False, proximal=99, distal=103)]
    update_zones(zones, 11, h=99, l=95, c=96, ex_bull=False, ex_bear=False)
    assert zones[0].is_tested
    update_zones(zones, 12, h=103.05, l=98, c=102, ex_bull=False, ex_bear=False)
    assert zones == []


def test_max_move_grows_until_tested_then_freezes():
    zones = [make_zone(max_move=14.0)]
    update_zones(zones, 11, h=120, l=110, c=118, ex_bull=False, ex_bear=False)
    assert zones[0].max_move == 19.0  # 120 - 101
    update_zones(zones, 12, h=125, l=100, c=110, ex_bull=False, ex_bear=False)  # tests the zone
    assert zones[0].max_move == 24.0  # the touching bar still counts
    update_zones(zones, 13, h=140, l=110, c=130, ex_bull=False, ex_bear=False)
    assert zones[0].max_move == 24.0


def test_reversal_break_only_before_first_test():
    zones = [make_zone(reversal_level=130.0)]
    update_zones(zones, 11, h=125, l=101, c=120, ex_bull=False, ex_bear=False)  # tested, no break
    update_zones(zones, 12, h=140, l=120, c=135, ex_bull=False, ex_bear=False)
    assert not zones[0].broke_reversal
    fresh = [make_zone(reversal_level=130.0)]
    update_zones(fresh, 11, h=140, l=120, c=131, ex_bull=False, ex_bear=False)
    assert fresh[0].broke_reversal


def test_leg_out_run_counts_until_first_non_continuation():
    zones = [make_zone(leg_out_run=1)]
    for bar, bull in [(11, True), (12, True), (13, False), (14, True)]:
        update_zones(zones, bar, h=120, l=110, c=118, ex_bull=bull, ex_bear=False)
    assert zones[0].leg_out_run == 3 and not zones[0].run_open


def test_trim_keeps_newest():
    zones = [make_zone(proximal=p) for p in range(1, 15)]
    trim_zones(zones, max_zones=10)
    assert [z.proximal for z in zones] == list(range(5, 15))
