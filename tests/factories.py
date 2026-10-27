from datetime import datetime, timedelta

from zonetracker.engine.engine import ZoneEngine
from zonetracker.engine.zones import Zone

T = D0 = datetime(2026, 1, 1)


def run(*candles, engine: ZoneEngine | None = None) -> ZoneEngine:
    """Feed (o, h, l, c) tuples as consecutive daily candles starting at D0."""
    eng = engine or ZoneEngine()
    for o, h, l, c in candles:
        eng.update(D0 + timedelta(days=eng.bar_index + 1), o, h, l, c)
    return eng


def make_zone(is_demand: bool = True, proximal: float = 101, distal: float = 97, **overrides) -> Zone:
    fields = dict(
        pattern="DBR", is_demand=is_demand,
        leg_in_time=T, leg_in_high=110, leg_in_low=100, leg_in_bullish=False,
        base_start_time=T, base_end_time=T, base_high=102, base_low=98,
        base_highest_body_top=101, base_lowest_body_bottom=99, base_count=2,
        leg_out_count=1, leg_out_high=115, leg_out_low=97, leg_out_confirm_bar=10,
        leg_out_run=1, run_open=True, leg_out_gap=False, max_move=14.0,
        reversal_level=None, broke_reversal=False, start_time=T,
        proximal=proximal, distal=distal,
    )
    fields.update(overrides)
    return Zone(**fields)
