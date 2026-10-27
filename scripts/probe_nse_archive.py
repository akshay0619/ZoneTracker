"""Dev helper: python scripts/probe_nse_archive.py DDMMYYYY [DDMMYYYY ...] [--names]"""
import io
import sys

import pandas as pd
import requests

URL = "https://nsearchives.nseindia.com/content/indices/ind_close_all_{}.csv"
s = requests.Session()
s.headers["User-Agent"] = "Mozilla/5.0"
show_names = "--names" in sys.argv
for d in [a for a in sys.argv[1:] if not a.startswith("--")]:
    r = s.get(URL.format(d), timeout=30)
    if r.status_code != 200:
        print(d, "HTTP", r.status_code)
        continue
    df = pd.read_csv(io.StringIO(r.text))
    print(d, "HTTP 200", len(df), "indices")
    if show_names:
        print("   ", " | ".join(df.iloc[:, 0].astype(str)))
