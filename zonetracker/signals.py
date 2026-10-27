"""Approaching / Reacting rules applied to graded zones at the latest daily close."""
from dataclasses import dataclass

import pandas as pd

from zonetracker.engine.grading import GRADE_RANK, GradedZone
from zonetracker.engine.zones import Zone

APPROACH_PCT = 3.0
GRADED_TFS = ("D", "W")                    # grade minimums only apply here
MIN_GRADE = {"Approaching": "A", "Reacting": "B"}


@dataclass(frozen=True, slots=True)
class LiveStatus:
    tested: bool
    breached: bool


def live_status(z: Zone, forming: pd.DataFrame) -> LiveStatus:
    """Zone state including daily bars of the still-forming HTF candle (not yet seen by the engine)."""
    if z.is_demand:
        return LiveStatus(z.is_tested or bool((forming.low <= z.proximal).any()),
                          bool((forming.low < z.distal).any()))
    return LiveStatus(z.is_tested or bool((forming.high >= z.proximal).any()),
                      bool((forming.high > z.distal).any()))


def distance_pct(z: Zone, price: float) -> float:
    """Signed % from price to proximal, positive when price is on the zone's approach side."""
    return (price - z.proximal) / z.proximal * 100 if z.is_demand else (z.proximal - price) / z.proximal * 100


def classify(g: GradedZone, price: float, status: LiveStatus,
             graded_tfs: tuple[str, ...] = GRADED_TFS) -> str | None:
    """Returns "Approaching", "Reacting" or None."""
    z = g.zone
    if status.breached:
        return None
    if z.bottom <= price <= z.top:
        signal = "Reacting"
    elif not status.tested and 0 < distance_pct(z, price) <= APPROACH_PCT:
        signal = "Approaching"
    else:
        return None
    if g.timeframe in graded_tfs and GRADE_RANK[g.grade] < GRADE_RANK[MIN_GRADE[signal]]:
        return None
    return signal
