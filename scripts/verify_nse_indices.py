"""Sanity-check the NSE index cache: continuity of renamed series, name collisions, Yahoo agreement."""
import logging
import warnings

import pandas as pd

from zonetracker.data.nse_indices import NSEIndexProvider
from zonetracker.data.provider import YFinanceProvider

warnings.filterwarnings("ignore")
logging.getLogger("yfinance").setLevel(logging.CRITICAL)
p = NSEIndexProvider()
names = p.names()

lower = pd.Series(names).str.lower()
dupes = pd.Series(names)[lower.duplicated(keep=False)]
print("case-only duplicates:", dupes.tolist() or "none")

gappy = []
for n in names:
    d = p.daily(n).index.to_series()
    g = d.diff().dt.days
    if len(d) > 1 and g.max() > 10 and d.iloc[-1] > pd.Timestamp.now() - pd.Timedelta(days=30):
        gappy.append(f"{n} ({g.max():.0f}d before {g.idxmax().date()})")
print("live series with gaps > 10 days:", gappy or "none")

print("\nSeries (first -> last, bars, longest gap in calendar days):")
for n in ["Nifty 50", "Nifty Next 50", "Nifty Midcap 100", "Nifty Smallcap 100", "Nifty Bank",
          "Nifty Financial Services", "Nifty Private Bank", "Nifty Healthcare", "Nifty CPSE", "Nifty India Defence"]:
    d = p.daily(n)
    gap = d.index.to_series().diff().dt.days.max()
    print(f"  {n:26} {d.index[0].date()} -> {d.index[-1].date()}  {len(d):5}  max gap {gap:.0f}")

print("\nClose vs Yahoo (overlapping dates):")
for n, y in [("Nifty 50", "^NSEI"), ("Nifty Bank", "^NSEBANK"), ("Nifty IT", "^CNXIT")]:
    a, b = p.daily(n).close, YFinanceProvider().daily(y).close
    j = pd.concat([a, b], axis=1, keys=["nse", "yahoo"]).dropna()
    diff = (j.nse / j.yahoo - 1).abs()
    print(f"  {n:12} {len(j)} days, median diff {diff.median():.5%}, max {diff.max():.3%} on {diff.idxmax().date()}, "
          f"days > 0.5%: {(diff > 0.005).sum()}")
