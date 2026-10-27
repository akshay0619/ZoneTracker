"""Dev helper: python scripts/show_results.py [TF] [Signal] - print signals from data/results/latest.csv."""
import sys

import pandas as pd

r = pd.read_csv("data/results/latest.csv")
tf = sys.argv[1] if len(sys.argv) > 1 else "D"
sig = sys.argv[2] if len(sys.argv) > 2 else None
q = r[(r.tf == tf) & ((r.signal == sig) if sig else True)].sort_values(["signal", "kind", "score"], ascending=[True, True, False])
cols = ["kind", "symbol", "group", "signal", "side", "pattern", "grade", "score", "proximal", "distal", "close", "distance_pct", "zone_start"]
print(f"as_of {r.as_of.max()}  |  {tf} {sig or 'all'}: {len(q)} rows")
print(q[cols].to_string(index=False, max_colwidth=22))
