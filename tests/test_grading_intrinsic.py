import pytest

from tests.factories import make_zone, run
from zonetracker.engine.grading import intrinsic_score

# Factory default: DBR demand, proximal 101 / distal 97 (height 4), 1 Leg Out attempt,
# 2 base candles, max_move 14 (3.5:1), no gap, no reversal break, fresh.


def test_factory_default_breakdown():
    s = intrinsic_score(make_zone())
    assert (s.freshness, s.strength, s.time_at_zone, s.move_from_zone, s.reversal_break) == (2, 2, 2, 0, 0)
    assert s.move_ratio == pytest.approx(3.5)
    assert s.total == 6


def test_tested_zone_loses_freshness():
    assert intrinsic_score(make_zone(is_tested=True)).freshness == 0


@pytest.mark.parametrize("overrides, expected", [
    (dict(leg_out_gap=True, leg_out_count=3), 2),                    # gap beats everything
    (dict(leg_out_count=1), 2),                                      # reversal, 1 attempt
    (dict(leg_out_count=2), 1),                                      # reversal, 2+ attempts
    (dict(leg_in_bullish=True, leg_out_run=4), 2),                   # continuation (RBR), run > 3
    (dict(leg_in_bullish=True, leg_out_run=3, leg_out_count=1), 1),  # continuation, run 3
])
def test_strength(overrides, expected):
    assert intrinsic_score(make_zone(**overrides)).strength == expected


@pytest.mark.parametrize("count, expected", [(1, 2), (2, 2), (3, 1), (4, 1), (5, 0)])
def test_time_at_zone(count, expected):
    assert intrinsic_score(make_zone(base_count=count)).time_at_zone == expected


def test_move_from_zone_threshold_daily_vs_intraday():
    z = make_zone(max_move=16.0)  # exactly 4:1 -> ">=" passes on daily
    assert intrinsic_score(z).move_from_zone == 2
    z = make_zone(max_move=12.0)  # 3:1 -> fails daily, passes intraday
    assert intrinsic_score(z).move_from_zone == 0
    assert intrinsic_score(z, intraday=True).move_from_zone == 2


def test_zero_height_zone_scores_no_move():
    assert intrinsic_score(make_zone(proximal=100, distal=100)).move_ratio == 0


def test_reversal_break_points():
    assert intrinsic_score(make_zone(broke_reversal=True)).reversal_break == 2


def test_score_on_engine_built_zone():
    # DBR from the engine tests: proximal 101, distal 98, max_move 14 (4.67:1)
    z = run((110, 111, 99, 100), (100, 103, 98, 101), (101, 115, 100, 114)).demand_zones[0]
    s = intrinsic_score(z)
    assert (s.freshness, s.strength, s.time_at_zone, s.move_from_zone, s.reversal_break) == (2, 2, 2, 2, 0)
    assert s.total == 8
