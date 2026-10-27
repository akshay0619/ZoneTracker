"""Build data/universe/indices.csv from the NSE archive cache + BSE Yahoo list. Run after update_nse_indices.py."""
import pandas as pd

from zonetracker.data.nse_indices import NSEIndexArchive
from zonetracker.data.universe import INDICES_CSV, build_index_universe

data = NSEIndexArchive().load()
stats = data.groupby("name").date.agg(bars="count", last="max").reset_index()
out, unknown = build_index_universe(stats, as_of=pd.Timestamp(data.date.max()))

INDICES_CSV.parent.mkdir(parents=True, exist_ok=True)
out.to_csv(INDICES_CSV, index=False)
print(out.groupby(["exchange", "category"]).size().to_string())
print(f"saved {len(out)} indices -> {INDICES_CSV}")
dropped = sorted(set(stats.name) - set(out.name))
print(f"\nskipped (discontinued or too little data): {len(dropped)}")
for n in dropped:
    s = stats.set_index("name").loc[n]
    print(f"  {n:55} bars={s.bars:5}  last={s['last'].date()}")
if unknown:
    print("\nno OHLC in NSE archive (close-only, cannot scan):", unknown)
