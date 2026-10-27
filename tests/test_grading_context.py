import pytest

from tests.factories import make_zone
from zonetracker.engine.grading import (coinciding_points, grade_of, grade_timeframes, nearest_opposing,
                                        overlaps_any, reward_risk_points)

# Default demand zone: proximal 101, distal 97 (height 4), intrinsic score 6


def supply(proximal: float, distal: float | None = None, **kw):
    return make_zone(is_demand=False, proximal=proximal, distal=distal or proximal + 4, **kw)


def demand(proximal: float = 101, distal: float = 97, **kw):
    return make_zone(is_demand=True, proximal=proximal, distal=distal, **kw)


def test_nearest_opposing_picks_closest_fresh_beyond_ref():
    pool = [supply(120), supply(113), supply(110, is_tested=True), supply(95), demand(130)]
    assert nearest_opposing(pool, for_demand=True, ref=101) == 113
    assert nearest_opposing([demand(90), demand(80), demand(99)], for_demand=False, ref=95) == 90


@pytest.mark.parametrize("opp_proximal, points", [(113, 3.0), (109, 1.5), (108, 0.0)])  # R:R 3.0 / 2.0 / 1.75
def test_reward_risk_thresholds(opp_proximal, points):
    assert reward_risk_points(demand(), [supply(opp_proximal)])[0] == points


def test_reward_risk_open_space_and_zero_height():
    assert reward_risk_points(demand(), []) == (2.0, None)
    assert reward_risk_points(demand(100, 100), [supply(110)]) == (0.0, None)


def test_overlap_touching_edges_counts_and_side_matters():
    assert overlaps_any([demand(97, 93)], True, top=101, bottom=97)        # touches at 97
    assert not overlaps_any([demand(96, 93)], True, top=101, bottom=97)
    assert not overlaps_any([supply(98, 100)], True, top=101, bottom=97)   # opposite side


def test_coinciding_higher_beats_inner():
    z = demand()
    assert coinciding_points(z, inner=[demand(100, 98)], higher=[demand(99, 95)]) == 2
    assert coinciding_points(z, inner=[demand(100, 98)], higher=[]) == 1
    assert coinciding_points(z, inner=[], higher=[]) == 0


@pytest.mark.parametrize("total, grade", [(13, "A+"), (12.5, "A"), (11, "A"), (10.5, "B"), (8, "B"), (7.5, "C")])
def test_grade_boundaries(total, grade):
    assert grade_of(total) == grade


def test_grade_timeframes_daily_zone_reaches_a():
    zones = {
        "D": [demand()],
        "W": [supply(113)],          # R:R 3:1 -> 3 points (higher TF counts for R:R)
        "M": [demand(100, 95)],      # overlaps -> 2 points (M is the "higher" TF for D)
    }
    d = grade_timeframes(zones)["D"][0]
    assert (d.intrinsic.total, d.rr_points, d.coinciding, d.total, d.grade) == (6, 3, 2, 11, "A")


def test_lower_tf_zones_are_ignored_for_rr():
    zones = {"D": [supply(103)], "W": [demand()]}
    w = grade_timeframes(zones)["W"][0]
    assert w.rr_points == 2.0 and w.rr is None  # D supply is below W's TF, so open space


def test_half_yearly_inner_only_and_yearly_no_coinciding():
    zones = {"H": [demand()], "Y": [demand(100, 95)]}
    graded = grade_timeframes(zones)
    assert graded["H"][0].coinciding == 1
    assert graded["Y"][0].coinciding == 0
