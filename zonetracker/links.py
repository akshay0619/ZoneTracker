"""Chart (TradingView) and Fundamental (Screener) links for stocks and indices."""
import re
from pathlib import Path
from urllib.parse import quote

import pandas as pd
import requests

INDEX_LINKS_CSV = Path("data/universe/index_links.csv")
TV_CHART = "https://www.tradingview.com/chart/?symbol={}"
SCREENER = "https://www.screener.in"
TV_SEARCH = "https://symbol-search.tradingview.com/symbol_search/v3/"
TV_HEADERS = {"User-Agent": "Mozilla/5.0", "Origin": "https://www.tradingview.com",
              "Referer": "https://www.tradingview.com/"}
# BSE indices: TradingView codes (checked 2026-10-27); Screener has no BSE index pages
BSE_TV = {"BSE Sensex": "BSE:SENSEX", "BSE 100": "BSE:BSE100", "BSE 200": "BSE:BSE200", "BSE 500": "BSE:BSE500"}


def stock_links(symbol: str) -> tuple[str, str]:
    """(chart, fundamental) for an NSE stock symbol."""
    return TV_CHART.format(quote(f"NSE:{symbol}")), f"{SCREENER}/company/{quote(symbol, safe='')}/"


def name_key(name: str) -> str:
    """'Nifty Healthcare Index' and 'NIFTY Healthcare' -> 'niftyhealthcare'."""
    return re.sub(r"[^a-z0-9]", "", re.sub(r"\bindex\b", "", str(name).lower()))


def pick_match(name: str, candidates: list[tuple[str, str]]) -> str | None:
    """candidates = [(code, description)]; exact key match only, never a guess."""
    key = name_key(name)
    return next((code for code, desc in candidates if name_key(desc) == key), None)


def tv_index_code(name: str, session: requests.Session) -> str | None:
    r = session.get(TV_SEARCH, params={"text": name, "exchange": "NSE", "search_type": "index"},
                    headers=TV_HEADERS, timeout=20)
    r.raise_for_status()
    hits = [(f"NSE:{s['symbol']}", s.get("description", "")) for s in r.json().get("symbols", [])]
    return pick_match(name, hits)


def screener_index_url(name: str, session: requests.Session) -> str | None:
    r = session.get(f"{SCREENER}/api/company/search/", params={"q": name},
                    headers={"User-Agent": "Mozilla/5.0"}, timeout=20)
    r.raise_for_status()
    hits = [(SCREENER + h["url"], h["name"]) for h in r.json() if not h["url"].startswith("/company/id/")]
    return pick_match(name, hits)


def load_index_links() -> pd.DataFrame:
    if not INDEX_LINKS_CSV.exists():
        return pd.DataFrame(columns=["name", "chart", "fundamental"])
    return pd.read_csv(INDEX_LINKS_CSV)
