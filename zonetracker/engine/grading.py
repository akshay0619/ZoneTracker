"""Zone grading, ported from Pine exportZones (lines 206-219) and the grading block (632-667)."""
from collections.abc import Iterable
from dataclasses import dataclass

from zonetracker.engine.zones import Zone


@dataclass(frozen=True, slots=True)
class IntrinsicScore:
    """The 10 points that depend only on the zone itself (max 2 each)."""
    freshness: float
    strength: float
    time_at_zone: float
    move_from_zone: float
    reversal_break: float
    move_ratio: float  # Move From Zone as a multiple of zone height

    @property
    def total(self) -> float:
        return self.freshness + self.strength + self.time_at_zone + self.move_from_zone + self.reversal_break


def intrinsic_score(z: Zone, intraday: bool = False) -> IntrinsicScore:
    reversal_pattern = z.leg_in_bullish != z.is_demand  # DBR / RBD
    freshness = 0.0 if z.is_tested else 2.0
    if z.leg_out_gap:
        strength = 2.0
    elif reversal_pattern:
        strength = 2.0 if z.leg_out_count == 1 else 1.0
    else:
        strength = 2.0 if z.leg_out_run > 3 else 1.0
    time_at_zone = 2.0 if z.base_count <= 2 else 1.0 if z.base_count <= 4 else 0.0
    height = abs(z.proximal - z.distal)
    move_ratio = z.max_move / height if height > 0 else 0.0
    move_from_zone = 2.0 if move_ratio >= (3.0 if intraday else 4.0) else 0.0
    reversal_break = 2.0 if z.broke_reversal else 0.0
    return IntrinsicScore(freshness, strength, time_at_zone, move_from_zone, reversal_break, move_ratio)


TIMEFRAMES = ("D", "W", "M", "Q", "H", "Y")
# Coinciding TFs: (inner TF = 1 point, higher TF = 2 points). Pine defines D and W; M+ are our extension.
COINCIDING_TFS: dict[str, tuple[str | None, str | None]] = {
    "D": ("W", "M"), "W": ("M", "Q"), "M": ("Q", "H"), "Q": ("H", "Y"), "H": ("Y", None), "Y": (None, None),
}
GRADE_THRESHOLDS = (("A+", 13.0), ("A", 11.0), ("B", 8.0))
GRADE_RANK = {"A+": 4, "A": 3, "B": 2, "C": 1}


def nearest_opposing(zones: Iterable[Zone], for_demand: bool, ref: float) -> float | None:
    """Closest FRESH opposing proximal beyond `ref` (above for demand, below for supply)."""
    levels = [z.proximal for z in zones if z.is_demand != for_demand and not z.is_tested
              and (z.proximal > ref if for_demand else z.proximal < ref)]
    if not levels:
        return None
    return min(levels) if for_demand else max(levels)


def reward_risk_points(z: Zone, pool: Iterable[Zone], intraday: bool = False) -> tuple[float, float | None]:
    """Returns (points, R:R). No opposing fresh zone = open space = 2 points."""
    near = nearest_opposing(pool, z.is_demand, z.proximal)
    if near is None:
        return 2.0, None
    height = abs(z.proximal - z.distal)
    if height == 0:
        return 0.0, None
    rr = abs(near - z.proximal) / height
    hi, lo = (2.0, 1.5) if intraday else (3.0, 2.0)
    return (3.0 if rr >= hi else 1.5 if rr >= lo else 0.0), rr


def overlaps_any(zones: Iterable[Zone], is_demand: bool, top: float, bottom: float) -> bool:
    """Any same-side zone (fresh or tested) sharing price with [bottom, top]; touching counts."""
    return any(z.is_demand == is_demand and max(bottom, z.bottom) <= min(top, z.top) for z in zones)


def coinciding_points(z: Zone, inner: Iterable[Zone], higher: Iterable[Zone]) -> float:
    if overlaps_any(higher, z.is_demand, z.top, z.bottom):
        return 2.0
    return 1.0 if overlaps_any(inner, z.is_demand, z.top, z.bottom) else 0.0


def grade_of(total: float) -> str:
    return next((g for g, minimum in GRADE_THRESHOLDS if total >= minimum), "C")


@dataclass(frozen=True, slots=True)
class GradedZone:
    zone: Zone
    timeframe: str
    intrinsic: IntrinsicScore
    rr_points: float
    rr: float | None
    coinciding: float
    total: float
    grade: str


def grade_timeframes(zones_by_tf: dict[str, list[Zone]], intraday: bool = False) -> dict[str, list[GradedZone]]:
    """Grade every TF's zones. R:R looks at the same TF and all higher TFs (Pine stops at Q; we include H/Y)."""
    out: dict[str, list[GradedZone]] = {}
    present = [tf for tf in TIMEFRAMES if tf in zones_by_tf]
    for i, tf in enumerate(present):
        pool = [z for higher in present[i:] for z in zones_by_tf[higher]]
        inner_tf, higher_tf = COINCIDING_TFS[tf]
        inner, higher = zones_by_tf.get(inner_tf, []), zones_by_tf.get(higher_tf, [])
        graded = []
        for z in zones_by_tf[tf]:
            s = intrinsic_score(z, intraday)
            rr_pts, rr = reward_risk_points(z, pool, intraday)
            coin = coinciding_points(z, inner, higher)
            total = s.total + rr_pts + coin
            graded.append(GradedZone(z, tf, s, rr_pts, rr, coin, total, grade_of(total)))
        out[tf] = graded
    return out
