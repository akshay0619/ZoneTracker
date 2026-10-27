"""Resolve TradingView + Screener links for indices -> data/universe/index_links.csv.

Incremental: only indices missing from the file are looked up. Pass --all to re-resolve everything.
"""
import sys
import time

import pandas as pd
import requests

from zonetracker.data.universe import load_indices
from zonetracker.links import BSE_TV, INDEX_LINKS_CSV, TV_CHART, load_index_links, screener_index_url, tv_index_code

existing = pd.DataFrame(columns=["name", "chart", "fundamental"]) if "--all" in sys.argv else load_index_links()
indices = load_indices()
todo = indices[~indices.name.isin(existing.name)]
s = requests.Session()
rows = []
for i in todo.itertuples():
    if i.exchange == "BSE":
        tv, scr = BSE_TV.get(i.name), None
    else:
        tv, scr = tv_index_code(i.name, s), screener_index_url(i.name, s)
        time.sleep(0.3)  # be polite to both sites
    rows.append({"name": i.name, "chart": TV_CHART.format(tv) if tv else None, "fundamental": scr})

out = pd.concat([existing[existing.name.isin(indices.name)], pd.DataFrame(rows)], ignore_index=True)
out.to_csv(INDEX_LINKS_CSV, index=False)
print(f"looked up {len(todo)} new indices; {len(out)} total: chart {out.chart.notna().sum()}, "
      f"fundamental {out.fundamental.notna().sum()}")
