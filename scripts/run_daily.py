"""The whole after-close routine, in order. Schedule this once a day (~19:00 IST, Mon-Fri).

1. Refresh the stock universe if it is older than 30 days (NSE rebalances twice a year)
2. Fetch new NSE index archive days
3. Rebuild the index list (new indices appear automatically)
4. Resolve chart/fundamental links for any new index
5. Scan everything -> data/results/latest.csv

Exits non-zero if any step fails, so the scheduler can alert.
"""
import os
import runpy
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
STOCKS = ROOT / "data" / "universe" / "stocks.csv"
UNIVERSE_MAX_AGE_DAYS = 30


def step(name: str, script: str) -> None:
    t0 = time.time()
    print(f"\n== {name} ==", flush=True)
    sys.argv = [script]
    runpy.run_path(str(SCRIPTS / script), run_name="__main__")
    print(f"-- {name}: done in {time.time() - t0:.0f}s", flush=True)


def main() -> int:
    os.chdir(ROOT)  # scripts use paths relative to the project root
    print(f"Daily run started {datetime.now():%Y-%m-%d %H:%M:%S}")
    stale = not STOCKS.exists() or (time.time() - STOCKS.stat().st_mtime) / 86400 > UNIVERSE_MAX_AGE_DAYS
    steps = ([("Stock universe", "build_universe.py")] if stale else []) + [
        ("NSE index archive", "update_nse_indices.py"),
        ("Index list", "build_indices.py"),
        ("Index links", "build_index_links.py"),
        ("Scan", "run_scan.py"),
    ]
    for name, script in steps:
        try:
            step(name, script)
        except Exception as e:  # stop: a later step would run on stale or partial data
            print(f"!! {name} FAILED: {e!r}", flush=True)
            return 1
    print(f"\nDaily run finished {datetime.now():%Y-%m-%d %H:%M:%S}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
