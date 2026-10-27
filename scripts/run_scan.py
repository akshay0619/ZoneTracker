"""Daily scan: every stock + index, all timeframes -> data/results/scan_<date>.csv and latest.csv.

Run after update_nse_indices.py and build_indices.py (after market close).
"""
import logging
import time
import warnings
from pathlib import Path

import pandas as pd

from zonetracker.data.nse_indices import NSEIndexProvider
from zonetracker.data.provider import YFinanceProvider
from zonetracker.data.universe import load_indices
from zonetracker.scan import scan_instrument

warnings.filterwarnings("ignore")
logging.getLogger("yfinance").setLevel(logging.CRITICAL)
OUT = Path("data/results")
t0 = time.time()

stocks = pd.read_csv("data/universe/stocks.csv")
indices = load_indices()
yahoo_syms = stocks.yahoo.tolist() + indices.loc[indices.source == "yahoo", "symbol"].tolist()
print(f"downloading {len(yahoo_syms)} Yahoo symbols ...")
yahoo = YFinanceProvider().daily_many(yahoo_syms)
nse = NSEIndexProvider()
print(f"  got {len(yahoo)} in {time.time() - t0:.0f}s")

jobs = [(yahoo.get(s.yahoo), {"kind": "Stock", "symbol": s.symbol, "name": s.company, "group": s.segment,
                              "exchange": "NSE", "industry": s.industry}) for s in stocks.itertuples()]
for i in indices.itertuples():
    daily = yahoo.get(i.symbol) if i.source == "yahoo" else nse.daily(i.symbol)
    jobs.append((daily, {"kind": "Index", "symbol": i.symbol, "name": i.name, "group": i.category,
                         "exchange": i.exchange, "industry": ""}))

rows, failed = [], []
for daily, meta in jobs:
    if daily is None or len(daily) < 2:
        failed.append(meta["symbol"])
        continue
    try:
        rows.extend(scan_instrument(daily, meta))
    except Exception as e:  # one bad instrument must not kill the scan
        failed.append(f"{meta['symbol']} ({e})")

res = pd.DataFrame(rows)
OUT.mkdir(parents=True, exist_ok=True)
as_of = res.as_of.max() if len(res) else pd.Timestamp.now().date()
res.to_csv(OUT / f"scan_{as_of}.csv", index=False)
res.to_csv(OUT / "latest.csv", index=False)
print(f"scanned {len(jobs) - len(failed)}/{len(jobs)} instruments in {time.time() - t0:.0f}s, {len(res)} signals")
if len(res):
    print(res.pivot_table(index=["kind", "signal"], columns="tf", values="symbol", aggfunc="count",
                          fill_value=0).reindex(columns=["D", "W", "M", "Q", "H", "Y"], fill_value=0).to_string())
if failed:
    print("failed:", ", ".join(failed))
