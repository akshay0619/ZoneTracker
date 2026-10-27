import pandas as pd
import pytest

from tests.factories import make_zone
from zonetracker.engine.grading import grade_timeframes
from zonetracker.signals import LiveStatus, classify, distance_pct, live_status

FRESH, TESTED, BREACHED = LiveStatus(False, False), LiveStatus(True, False), LiveStatus(True, True)


def graded(tf: str, **zone_kw):
    """Factory zone graded alone on `tf`: 6 intrinsic + 2 open-space R:R = 8 -> grade B."""
    return grade_timeframes({tf: [make_zone(**zone_kw)]})[tf][0]


@pytest.mark.parametrize("price, expected", [
    (103.0, "Approaching"),   # 1.98% above demand proximal 101
    (104.5, None),            # 3.47%: too far
    (101.0, "Reacting"),      # on the proximal line = inside
    (99.0, "Reacting"),
    (97.0, "Reacting"),       # on distal, still not breached
])
def test_demand_signals_no_grade_filter(price, expected):
    assert classify(graded("M"), price, FRESH) == expected


def test_supply_approaching_from_below():
    g = graded("M", is_demand=False, proximal=99, distal=103)
    assert distance_pct(g.zone, 97) == pytest.approx(2.0202, abs=1e-3)
    assert classify(g, 97, FRESH) == "Approaching"
    assert classify(g, 100, FRESH) == "Reacting"
    assert classify(g, 104, FRESH) is None


def test_tested_zone_can_react_but_not_approach():
    g = graded("M")
    assert classify(g, 103, TESTED) is None
    assert classify(g, 99, TESTED) == "Reacting"


def test_breached_zone_never_signals():
    assert classify(graded("M"), 99, BREACHED) is None


def test_grade_minimums_only_on_daily_and_weekly():
    for tf in ("D", "W"):
        g = graded(tf)  # grade B
        assert g.grade == "B"
        assert classify(g, 103, FRESH) is None          # Approaching needs A
        assert classify(g, 99, FRESH) == "Reacting"     # Reacting needs B
    assert classify(graded("Q"), 103, FRESH) == "Approaching"


def test_live_status_from_forming_bars():
    demand = make_zone()  # proximal 101, distal 97
    bars = lambda lows, highs: pd.DataFrame({"low": lows, "high": highs})
    assert live_status(demand, bars([105, 102], [110, 108])) == LiveStatus(False, False)
    assert live_status(demand, bars([105, 100.5], [110, 108])) == LiveStatus(True, False)
    assert live_status(demand, bars([105, 96.9], [110, 108])) == LiveStatus(True, True)
    supply = make_zone(is_demand=False, proximal=99, distal=103)
    assert live_status(supply, bars([90, 91], [95, 103.1])) == LiveStatus(True, True)
    assert live_status(demand, bars([], [])) == LiveStatus(False, False)
