"""Check which universe tickers Yahoo actually serves. Writes data/universe/ticker_check.csv."""
import logging
import warnings
from pathlib import Path

import pandas as pd
import yfinance as yf

from zonetracker.data.universe import load_indices

warnings.filterwarnings("ignore")
logging.getLogger("yfinance").setLevel(logging.CRITICAL)
STOCKS = Path("data/universe/stocks.csv")
OUT = Path("data/universe/ticker_check.csv")
STALE_DAYS = 7
MIN_BARS = 250  # ~1 year; Yahoo returns a single quote bar for indices it has no history for


def check(symbol: str) -> dict:
    df = yf.download(symbol, period="max", interval="1d", progress=False, auto_adjust=False,
                     multi_level_index=False)
    df = df.dropna(subset=["Close"]) if not df.empty else df
    if df.empty:
        return dict(yahoo=symbol, ok=False, bars=0, first=None, last=None)
    last = df.index[-1]
    stale = (pd.Timestamp.now() - last).days > STALE_DAYS
    return dict(yahoo=symbol, ok=not stale and len(df) >= MIN_BARS, bars=len(df),
                first=df.index[0].date(), last=last.date())


rows = []
idx = load_indices()
for _, r in idx[idx.source == "yahoo"].iterrows():  # NSE indices come from the NSE archive
    res = check(r.symbol) | {"kind": "index", "name": r["name"]}
    rows.append(res)
    print(f"{'OK  ' if res['ok'] else 'FAIL'} {r['name']:28} {r.symbol:24} bars={res['bars']:5} {res['first']} -> {res['last']}")

stocks = pd.read_csv(STOCKS)
batch = yf.download(stocks.yahoo.tolist(), period="10d", interval="1d", progress=False,
                    auto_adjust=False, group_by="ticker", threads=True)
for sym in stocks.yahoo:
    ok = sym in batch.columns.get_level_values(0) and batch[sym]["Close"].notna().any()
    rows.append(dict(yahoo=sym, ok=bool(ok), kind="stock", name=sym))

out = pd.DataFrame(rows)
OUT.parent.mkdir(parents=True, exist_ok=True)
out.to_csv(OUT, index=False)
for kind, g in out.groupby("kind"):
    bad = g[~g.ok]
    print(f"{kind}: {g.ok.sum()}/{len(g)} OK" + (f"; failing: {', '.join(bad.yahoo)}" if len(bad) else ""))
