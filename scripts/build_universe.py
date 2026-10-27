"""Download Nifty 500 / Midcap 150 / Smallcap 250 lists and save data/universe/stocks.csv."""
from pathlib import Path

from zonetracker.data.universe import build_stock_universe, fetch_constituents

OUT = Path("data/universe/stocks.csv")

lists = {name: fetch_constituents(name) for name in ("Nifty 500", "Midcap 150", "Smallcap 250")}
for name, df in lists.items():
    print(f"{name}: {len(df)} stocks")
u = build_stock_universe(lists["Nifty 500"], lists["Midcap 150"], lists["Smallcap 250"])
OUT.parent.mkdir(parents=True, exist_ok=True)
u.to_csv(OUT, index=False)
print(u["segment"].value_counts().to_string())
print(f"saved {len(u)} rows -> {OUT}")
