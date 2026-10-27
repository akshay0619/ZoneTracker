"""Dev helper: print the header and first rows of a remote CSV. python scripts/peek_csv.py URL"""
import io
import sys

import pandas as pd
import requests

r = requests.get(sys.argv[1], headers={"User-Agent": "Mozilla/5.0"}, timeout=30)
print("HTTP", r.status_code, len(r.content), "bytes")
df = pd.read_csv(io.StringIO(r.text))
print(df.columns.tolist(), len(df), "rows")
print(df.head(3).to_string())
