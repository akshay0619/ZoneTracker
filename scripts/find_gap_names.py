"""Dev helper: python scripts/find_gap_names.py "Nifty Midcap 100" [keyword] - names that only exist inside the series' biggest gap."""
import sys

from zonetracker.data.nse_indices import NSEIndexArchive

data = NSEIndexArchive().load()
name = sys.argv[1]
kw = sys.argv[2].lower() if len(sys.argv) > 2 else name.split()[-2].lower()
s = data[data.name == name].date.sort_values()
i = s.diff().idxmax()
gap_end, gap_start = s[i], s[s.index.get_loc(i) - 1] if False else s[s < s[i]].max()
print(f"{name}: gap {gap_start.date()} -> {gap_end.date()}")
inside = data[(data.date > gap_start) & (data.date < gap_end) & data.name.str.lower().str.contains(kw)]
print(inside.groupby("name").date.agg(["min", "max", "count"]).to_string())
