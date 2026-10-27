import pytest

from tests.factories import make_zone
from zonetracker.engine.zones import check_confirmation, classify_pattern, is_close_in_base


@pytest.mark.parametrize("close, expected", [(98, True), (102, True), (100, True), (97.99, False), (102.01, False)])
def test_is_close_in_base_inclusive_edges(close, expected):
    assert is_close_in_base(close, base_high=102, base_low=98) is expected


def test_demand_confirmation_needs_close_above_leg_in_and_base():
    # Leg In high 110 is above base high 102, so close must beat 110
    assert not check_confirmation(110, 110, 95, 102, 98, is_demand=True)  # strict ">"
    assert check_confirmation(110.5, 110, 95, 102, 98, is_demand=True)


def test_supply_confirmation_needs_close_below_leg_in_and_base():
    # Base low 98 is below Leg In low 100, so close must break 98
    assert not check_confirmation(99, 110, 100, 102, 98, is_demand=False)
    assert check_confirmation(97.5, 110, 100, 102, 98, is_demand=False)


@pytest.mark.parametrize("leg_in_bull, leg_out_bull, name", [
    (True, True, "RBR"), (False, True, "DBR"), (True, False, "RBD"), (False, False, "DBD"),
])
def test_classify_pattern(leg_in_bull, leg_out_bull, name):
    assert classify_pattern(leg_in_bull, leg_out_bull) == name


def test_zone_top_bottom_by_side():
    demand = make_zone(True, proximal=101, distal=97)
    supply = make_zone(False, proximal=99, distal=103)
    assert (demand.top, demand.bottom) == (101, 97)
    assert (supply.top, supply.bottom) == (103, 99)


def test_zone_is_mutable_and_starts_fresh():
    z = make_zone(True, 101, 97)
    assert z.is_tested is False
    z.is_tested = True
    assert z.is_tested
