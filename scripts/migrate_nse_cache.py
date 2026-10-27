"""One-off: split data/nse_indices/ohlc.csv.gz into monthly files and prove nothing changed."""
import pandas as pd

from zonetracker.data.nse_indices import NSEIndexArchive

arc = NSEIndexArchive()
before = arc.load()
arc.update()  # migrates the legacy file first, then fetches any new days
after = arc.load()
common = after[after.date <= before.date.max()].reset_index(drop=True)
same = common.equals(before.reset_index(drop=True))
files = sorted(arc.month_dir.glob("*.csv.gz"))
size = sum(f.stat().st_size for f in files)
print(f"rows before {len(before)}, after {len(after)} (identical history: {same})")
print(f"{len(files)} month files, {size / 1e6:.1f} MB total, largest {max(f.stat().st_size for f in files) / 1e3:.0f} KB, "
      f"legacy file gone: {not arc._legacy.exists()}")
