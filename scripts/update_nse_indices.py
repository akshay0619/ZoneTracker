"""Backfill / update the NSE index archive cache. Safe to re-run: only missing dates are fetched."""
import time

from zonetracker.data.nse_indices import NSEIndexArchive

t0 = time.time()
arc = NSEIndexArchive()
added, holidays = arc.update()
data = arc.load()
print(f"added {added} trading days, {holidays} holidays/unpublished, in {time.time() - t0:.0f}s")
print(f"cache: {len(data)} rows, {data['name'].nunique()} indices, "
      f"{data['date'].min().date()} -> {data['date'].max().date()}")
