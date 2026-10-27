"""Dev smoke test: python scripts/smoke_zones.py RELIANCE.NS"""
import sys
import warnings

from zonetracker.data.provider import YFinanceProvider
from zonetracker.data.resample import resample
from zonetracker.engine.engine import ZoneEngine
from zonetracker.engine.grading import TIMEFRAMES, grade_timeframes

warnings.filterwarnings("ignore")
symbol = sys.argv[1] if len(sys.argv) > 1 else "RELIANCE.NS"
d = YFinanceProvider().daily(symbol)
print(f"{symbol} daily bars: {len(d)}  {d.index[0].date()} -> {d.index[-1].date()}  last close {d.close.iloc[-1]}")

zones = {}
for tf in TIMEFRAMES:
    df = resample(d, tf)
    eng = ZoneEngine()
    for t, r in df.iterrows():
        eng.update(t, r.open, r.high, r.low, r.close)
    zones[tf] = eng.demand_zones + eng.supply_zones
    print(f"{tf}: {len(df):5d} candles, {len(eng.demand_zones)} demand / {len(eng.supply_zones)} supply active")

for tf, graded in grade_timeframes(zones).items():
    for g in graded:
        z = g.zone
        print(f"  {tf} {'DEM' if z.is_demand else 'SUP'} {z.pattern} {z.bottom:9.2f} - {z.top:9.2f}  "
              f"start {z.start_time.date()}  {'tested' if z.is_tested else 'FRESH '}  {g.grade:2} ({g.total})")
