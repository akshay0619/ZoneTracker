"""Dev helper: python scripts/debug_symbol.py LTFOODS.NS - full traceback + suspicious rows."""
import traceback
import warnings

import sys

from zonetracker.data.provider import YFinanceProvider
from zonetracker.scan import scan_instrument

warnings.filterwarnings("ignore")
d = YFinanceProvider().daily(sys.argv[1])
bad = d[(d[["open", "high", "low", "close"]] <= 0).any(axis=1) | (d.high < d.low)
        | (d.high < d[["open", "close"]].max(axis=1)) | (d.low > d[["open", "close"]].min(axis=1))]
print(f"{len(d)} bars, {len(bad)} suspicious rows")
print(bad.head(10).to_string())
try:
    scan_instrument(d, {"symbol": sys.argv[1]})
    print("scan OK")
except Exception:
    traceback.print_exc()
