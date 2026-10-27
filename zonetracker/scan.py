"""Run one instrument's daily candles through every timeframe and emit Approaching / Reacting rows."""
import pandas as pd

from zonetracker.data.resample import period_start, resample
from zonetracker.engine.engine import EngineConfig, ZoneEngine
from zonetracker.engine.grading import TIMEFRAMES, grade_timeframes
from zonetracker.engine.zones import Zone
from zonetracker.signals import GRADED_TFS, classify, distance_pct, live_status


def run_engine(df: pd.DataFrame, cfg: EngineConfig = EngineConfig()) -> list[Zone]:
    eng = ZoneEngine(cfg)
    for t, o, h, l, c in df[["open", "high", "low", "close"]].itertuples():
        eng.update(t, o, h, l, c)
    return eng.demand_zones + eng.supply_zones


def forming_bars(daily: pd.DataFrame, tf: str, htf: pd.DataFrame) -> pd.DataFrame:
    """Daily bars after the last closed HTF candle (empty for D)."""
    if tf == "D" or htf.empty:
        return daily.iloc[0:0]
    return daily[period_start(daily.index, tf) > htf.index[-1]]


def scan_instrument(daily: pd.DataFrame, meta: dict, cfg: EngineConfig = EngineConfig(),
                    graded_tfs: tuple[str, ...] = GRADED_TFS) -> list[dict]:
    price, as_of = round(float(daily.close.iloc[-1]), 2), daily.index[-1]  # Yahoo floats: 1139.900024
    frames = {tf: resample(daily, tf) for tf in TIMEFRAMES}
    zones = {tf: run_engine(df, cfg) for tf, df in frames.items() if len(df)}
    rows = []
    for tf, graded in grade_timeframes(zones).items():
        forming = forming_bars(daily, tf, frames[tf])
        for g in graded:
            z = g.zone
            signal = classify(g, price, live_status(z, forming), graded_tfs)
            if signal is None:
                continue
            s = g.intrinsic
            rows.append(meta | {
                "tf": tf, "signal": signal, "side": "Demand" if z.is_demand else "Supply",
                "pattern": z.pattern, "grade": g.grade, "score": g.total,
                "proximal": round(z.proximal, 2), "distal": round(z.distal, 2),
                "close": price, "distance_pct": round(distance_pct(z, price), 2),
                "zone_start": z.start_time.date(), "as_of": as_of.date(),
                "freshness": s.freshness, "strength": s.strength, "time_at_zone": s.time_at_zone,
                "move_from_zone": s.move_from_zone, "reversal_break": s.reversal_break,
                "reward_risk": g.rr_points, "coinciding": g.coinciding,
            })
    return rows
