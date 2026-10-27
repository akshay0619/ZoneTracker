"""Zone engine state machine, ported from Pine zoneEngine (lines 237-439).

Feed one closed candle at a time via `update`. Rows with NaN prices must be dropped
before they reach the engine (Pine skips them with `not na(c)`).
"""
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from zonetracker.engine.candles import GapCandle, classify_with_gap
from zonetracker.engine.swings import SwingTracker, find_reversal
from zonetracker.engine.zones import (Zone, check_confirmation, classify_pattern, is_close_in_base,
                                      trim_zones, update_zones)


class State(Enum):
    SCANNING = "SCANNING"
    TRACKING_LEG_IN = "TRACKING_LEG_IN"
    IN_BASE = "IN_BASE"
    CONFIRMING = "CONFIRMING"


@dataclass(frozen=True)
class EngineConfig:
    max_base_candles: int = 3
    wick_to_wick: bool = False          # False = "Body to Wick" boundary mode
    leg_out_size_pct: float = 100.0     # 0 = off
    base_size_whole_range: bool = True  # False = "Largest Base Candle"
    use_wick_breach: bool = True        # False = "Close Beyond Zone"
    swing_len: int = 5
    max_zones_per_side: int = 10


@dataclass(frozen=True, slots=True)
class _Prev:
    t: datetime
    h: float
    l: float
    c: float
    adj_open: float


class ZoneEngine:
    def __init__(self, cfg: EngineConfig = EngineConfig()):
        self.cfg = cfg
        self.bar_index = -1
        self.state = State.SCANNING
        self.swings = SwingTracker(cfg.swing_len)
        self.demand_zones: list[Zone] = []
        self.supply_zones: list[Zone] = []
        self._prev: _Prev | None = None
        # Leg In
        self.leg_in_time: datetime | None = None
        self.leg_in_high = self.leg_in_low = 0.0
        self.leg_in_bullish = False
        # Base
        self.base_start_time: datetime | None = None
        self.base_end_time: datetime | None = None
        self.base_start_idx = 0
        self.base_high = self.base_low = 0.0
        self.base_highest_body_top = self.base_lowest_body_bottom = 0.0
        self.base_largest_candle = 0.0
        self.base_count = 0
        # Leg Out
        self.leg_out_attempts = 0
        self.max_leg_out_size = self.leg_out_high = self.leg_out_low = 0.0
        self.max_leg_out_close = self.min_leg_out_close = 0.0
        self.leg_out_run_bull = self.leg_out_run_bear = 0
        self.leg_out_gap = False

    def update(self, t: datetime, o: float, h: float, l: float, c: float) -> None:
        self.bar_index += 1
        prev = self._prev
        ph, pl, pc = (prev.h, prev.l, prev.c) if prev else (None, None, None)
        gc = classify_with_gap(o, h, l, c, ph, pl, pc)
        cur = gc.candle
        self.swings.update(self.bar_index, h, l)

        start_base = add_to_base = leg_in_from_current = False
        if self.state is State.SCANNING:
            leg_in_from_current = cur.is_exciting
        elif self.state is State.TRACKING_LEG_IN:
            start_base, leg_in_from_current = cur.is_boring, cur.is_exciting
        else:
            joins_base = (is_close_in_base(c, self.base_high, self.base_low)
                          or (self.state is State.IN_BASE and cur.is_boring))
            if joins_base:
                if self.base_count >= self.cfg.max_base_candles:
                    if cur.is_exciting:
                        leg_in_from_current = True
                    else:
                        self.state = State.SCANNING
                else:
                    add_to_base = True
            else:
                start_base, leg_in_from_current = self._leg_out(gc, t, h, l, c, prev)

        for zones in (self.demand_zones, self.supply_zones):
            update_zones(zones, self.bar_index, h, l, c, cur.is_exciting_bullish,
                         cur.is_exciting_bearish, self.cfg.use_wick_breach)

        if start_base:
            self._start_base(t, o, h, l, c, gc.size)
        if add_to_base:
            self._add_to_base(t, o, h, l, c, gc.size)
        if leg_in_from_current:
            self._set_leg_in(t, h, l, cur.is_exciting_bullish)
        self._prev = _Prev(t, h, l, c, gc.adj_open)

    def _leg_out(self, gc: GapCandle, t, h, l, c, prev: _Prev | None) -> tuple[bool, bool]:
        """Exciting candle leaving the base, or boring candle outside it. Returns (start_base, leg_in_from_current)."""
        cur = gc.candle
        if not cur.is_exciting:
            # Boring candle outside the base during Leg Out: previous attempt becomes the Leg In of a new base
            self.leg_in_time, self.leg_in_high, self.leg_in_low = prev.t, prev.h, prev.l
            self.leg_in_bullish = prev.c > prev.adj_open
            return True, False

        self.leg_out_attempts = 1 if self.state is State.IN_BASE else self.leg_out_attempts + 1
        first = self.leg_out_attempts == 1
        if first:
            self.max_leg_out_size, self.leg_out_high, self.leg_out_low = gc.size, h, l
            self.max_leg_out_close = self.min_leg_out_close = c
            self.leg_out_gap = gc.has_gap
        else:
            self.max_leg_out_size = max(self.max_leg_out_size, gc.size)
            self.leg_out_high, self.leg_out_low = max(self.leg_out_high, h), min(self.leg_out_low, l)
            self.max_leg_out_close = max(self.max_leg_out_close, c)
            self.min_leg_out_close = min(self.min_leg_out_close, c)
        self.leg_out_run_bull = (1 if first else self.leg_out_run_bull + 1) if cur.is_exciting_bullish else 0
        self.leg_out_run_bear = (1 if first else self.leg_out_run_bear + 1) if cur.is_exciting_bearish else 0
        self.state = State.CONFIRMING

        base_size = self.base_high - self.base_low if self.cfg.base_size_whole_range else self.base_largest_candle
        pct = self.cfg.leg_out_size_pct
        size_ok = pct == 0 or self.max_leg_out_size > base_size * pct / 100
        # Pine quirk kept: a directionless (zero-range) candle is checked as supply
        is_demand = cur.is_exciting_bullish
        if size_ok and check_confirmation(c, self.leg_in_high, self.leg_in_low,
                                          self.base_high, self.base_low, is_demand):
            self._add_zone(self._build_zone(is_demand))
            return False, True
        return False, self.leg_out_attempts >= 3

    def _build_zone(self, is_demand: bool) -> Zone:
        """Pine Section 4: proximal / distal, reversal level. Runs before Leg In is overwritten."""
        wick = self.cfg.wick_to_wick
        is_reversal = self.leg_in_bullish != is_demand
        sw = self.swings
        if is_demand:
            proximal = self.base_high if wick else self.base_highest_body_top
            distal = min(self.base_low, self.leg_out_low)
            if is_reversal:
                distal = min(distal, self.leg_in_low)
            leg_in_sets_distal = is_reversal and self.leg_in_low <= distal
            rev = find_reversal(sw.high_prices, sw.high_bars, self.base_start_idx, self.base_high, above=True)
            broke_rev = rev is not None and self.max_leg_out_close > rev
            max_move = self.leg_out_high - proximal
        else:
            proximal = self.base_low if wick else self.base_lowest_body_bottom
            distal = max(self.base_high, self.leg_out_high)
            if is_reversal:
                distal = max(distal, self.leg_in_high)
            leg_in_sets_distal = is_reversal and self.leg_in_high >= distal
            rev = find_reversal(sw.low_prices, sw.low_bars, self.base_start_idx, self.base_low, above=False)
            broke_rev = rev is not None and self.min_leg_out_close < rev
            max_move = proximal - self.leg_out_low
        return Zone(
            pattern=classify_pattern(self.leg_in_bullish, is_demand), is_demand=is_demand,
            leg_in_time=self.leg_in_time, leg_in_high=self.leg_in_high, leg_in_low=self.leg_in_low,
            leg_in_bullish=self.leg_in_bullish,
            base_start_time=self.base_start_time, base_end_time=self.base_end_time,
            base_high=self.base_high, base_low=self.base_low,
            base_highest_body_top=self.base_highest_body_top,
            base_lowest_body_bottom=self.base_lowest_body_bottom, base_count=self.base_count,
            leg_out_count=self.leg_out_attempts, leg_out_high=self.leg_out_high, leg_out_low=self.leg_out_low,
            leg_out_confirm_bar=self.bar_index,
            leg_out_run=self.leg_out_run_bull if is_demand else self.leg_out_run_bear,
            run_open=True, leg_out_gap=self.leg_out_gap, max_move=max_move,
            reversal_level=rev, broke_reversal=broke_rev,
            start_time=self.leg_in_time if leg_in_sets_distal else self.base_start_time,
            proximal=proximal, distal=distal,
        )

    def _add_zone(self, zone: Zone) -> None:
        zones = self.demand_zones if zone.is_demand else self.supply_zones
        zones.append(zone)
        trim_zones(zones, self.cfg.max_zones_per_side)

    def _start_base(self, t, o, h, l, c, size) -> None:
        self.state = State.IN_BASE
        self.base_start_time = self.base_end_time = t
        self.base_start_idx = self.bar_index
        self.base_high, self.base_low = h, l
        self.base_highest_body_top, self.base_lowest_body_bottom = max(o, c), min(o, c)
        self.base_largest_candle = size
        self.base_count = 1
        self.leg_out_attempts = 0

    def _add_to_base(self, t, o, h, l, c, size) -> None:
        self.state = State.IN_BASE
        self.base_end_time = t
        self.base_high, self.base_low = max(self.base_high, h), min(self.base_low, l)
        self.base_highest_body_top = max(self.base_highest_body_top, o, c)
        self.base_lowest_body_bottom = min(self.base_lowest_body_bottom, o, c)
        self.base_largest_candle = max(self.base_largest_candle, size)
        self.base_count += 1
        self.leg_out_attempts = 0

    def _set_leg_in(self, t, h, l, bullish: bool) -> None:
        self.state = State.TRACKING_LEG_IN
        self.leg_in_time, self.leg_in_high, self.leg_in_low = t, h, l
        self.leg_in_bullish = bullish
        self.leg_out_attempts = 0
