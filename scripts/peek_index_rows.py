"""Dev helper: python scripts/peek_index_rows.py DDMMYYYY "Name 1" "Name 2" ... - raw archive rows."""
import io
import sys

import pandas as pd
import requests

r = requests.get(f"https://nsearchives.nseindia.com/content/indices/ind_close_all_{sys.argv[1]}.csv",
                 headers={"User-Agent": "Mozilla/5.0"}, timeout=30)
df = pd.read_csv(io.StringIO(r.text))
print(df[df["Index Name"].isin(sys.argv[2:])].iloc[:, :6].to_string())
