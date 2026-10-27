"""Zone type and small helpers, ported from Pine lines 111-156.

VWAP confluence (`vwapIn`) is intentionally dropped: on daily+ candles it is meaningless.
"""
from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True)
class Zone:
    # Mutable on purpose: the engine updates tested/move/run fields bar by bar (Pine objects are references)
    pattern: str            # RBR / DBR / RBD / DBD
    is_demand: bool
    leg_in_time: datetime
    leg_in_high: float
    leg_in_low: float
    leg_in_bullish: bool
    base_start_time: datetime
    base_end_time: datetime
    base_high: float
    base_low: float
    base_highest_body_top: float
    base_lowest_body_bottom: float
    base_count: int
    leg_out_count: int      # Leg Out attempts needed to confirm
    leg_out_high: float
    leg_out_low: float
    leg_out_confirm_bar: int
    leg_out_run: int        # consecutive exciting candles in the zone's direction
    run_open: bool
    leg_out_gap: bool
    max_move: float         # furthest move away from proximal before first test
    reversal_level: float | None
    broke_reversal: bool
    start_time: datetime
    proximal: float
    distal: float
    is_tested: bool = False

    @property
    def top(self) -> float:
        return self.proximal if self.is_demand else self.distal

    @property
    def bottom(self) -> float:
        return self.distal if self.is_demand else self.proximal


def is_close_in_base(close: float, base_high: float, base_low: float) -> bool:
    return base_low <= close <= base_high


def check_confirmation(close: float, leg_in_high: float, leg_in_low: float,
                       base_high: float, base_low: float, is_demand: bool) -> bool:
    """Demand: close above both Leg In and base highs. Supply: close below both lows."""
    if is_demand:
        return close > max(leg_in_high, base_high)
    return close < min(leg_in_low, base_low)


def classify_pattern(leg_in_bullish: bool, leg_out_bullish: bool) -> str:
    if leg_out_bullish:
        return "RBR" if leg_in_bullish else "DBR"
    return "RBD" if leg_in_bullish else "DBD"


def trim_zones(zones: list[Zone], max_zones: int) -> None:
    """Drop the oldest zones beyond the per-side limit (Pine trimZones)."""
    while len(zones) > max_zones:
        zones.pop(0)


def update_zones(zones: list[Zone], bar_index: int, h: float, l: float, c: float,
                 ex_bull: bool, ex_bear: bool, use_wick: bool = True) -> None:
    """Pine updateZones (lines 174-193), mutating `zones` in place.

    Reaching proximal marks a zone Tested; going beyond distal (wick or close) removes it.
    Before the first test it also tracks Move From Zone and the reversal break; the
    Leg Out run keeps counting while candles stay exciting in the zone's direction.
    """
    for i in range(len(zones) - 1, -1, -1):
        z = zones[i]
        if bar_index <= z.leg_out_confirm_bar:
            continue
        if z.is_demand:
            breached = (l if use_wick else c) < z.distal
            touched = l <= z.proximal
        else:
            breached = (h if use_wick else c) > z.distal
            touched = h >= z.proximal
        if not z.is_tested:
            z.max_move = max(z.max_move, h - z.proximal if z.is_demand else z.proximal - l)
            rev = z.reversal_level
            if rev is not None and (c > rev if z.is_demand else c < rev):
                z.broke_reversal = True
        if z.run_open:
            cont = ex_bull if z.is_demand else ex_bear
            z.leg_out_run += 1 if cont else 0
            z.run_open = cont
        z.is_tested = z.is_tested or touched
        if breached:
            del zones[i]
