"""Dev helper: check which TradingView symbol pages / Screener pages exist (HTTP status)."""
import sys

import requests

s = requests.Session()
s.headers["User-Agent"] = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/130 Safari/537.36"
for url in sys.argv[1:]:
    try:
        r = s.get(url, timeout=20, allow_redirects=True)
        title = r.text.split("<title>")[1].split("</title>")[0].strip()[:70] if "<title>" in r.text else ""
        print(r.status_code, url, "->", r.url if r.url != url else "", "|", title)
    except requests.RequestException as e:
        print("ERR", url, e)
