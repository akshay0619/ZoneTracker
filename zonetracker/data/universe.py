"""Stock and index universes. Nifty 500 = Nifty 100 + Midcap 150 + Smallcap 250."""
import io
from pathlib import Path

import pandas as pd
import requests

NIFTY_URL = "https://niftyindices.com/IndexConstituent/{}.csv"
NIFTY_LISTS = {
    "Nifty 500": "ind_nifty500list",
    "Midcap 150": "ind_niftymidcap150list",
    "Smallcap 250": "ind_niftysmallcap250list",
}
INDICES_CSV = Path("data/universe/indices.csv")
MIN_INDEX_BARS = 100  # ~5 months of daily candles

# Names as they appear in the NSE archive (after canonical_name). Anything else live is Thematic.
NSE_BROAD = [
    "Nifty 50", "Nifty Next 50", "Nifty 100", "Nifty 200", "Nifty 500", "Nifty Total Market",
    "Nifty Midcap 50", "Nifty Midcap 100", "Nifty Midcap 150", "Nifty Midcap Select",
    "Nifty Smallcap 50", "Nifty Smallcap 100", "Nifty Smallcap 250", "Nifty Smallcap 500",
    "Nifty Microcap 250", "Nifty LargeMidcap 250", "Nifty MidSmallcap 400", "Nifty500 Multicap 50:25:25",
]
NSE_SECTORAL = [
    "Nifty Auto", "Nifty Bank", "Nifty Private Bank", "Nifty PSU Bank", "Nifty Financial Services",
    "Nifty Financial Services 25/50", "Nifty Financial Services Ex-Bank", "Nifty FMCG", "Nifty IT",
    "Nifty Media", "Nifty Metal", "Nifty Pharma", "Nifty Healthcare", "Nifty Realty", "Nifty Energy",
    "Nifty Oil & Gas", "Nifty Consumer Durables", "Nifty Chemicals", "Nifty Cement", "Nifty Construction",
    # NSE publishes close-only (no O/H/L) for these as of 2026-10; they appear automatically once OHLC exists
    "Nifty Capital Goods", "Nifty Power", "Nifty Telecommunications", "Nifty Insurance", "Nifty NBFC",
    "Nifty Housing Finance", "Nifty Hospitals", "Nifty Retail",
]
# BSE indices Yahoo has usable history for (checked 2026-10-26); BSE sectorals have no free source yet
BSE_YAHOO = {"BSE Sensex": "^BSESN", "BSE 100": "BSE-100.BO", "BSE 200": "BSE-200.BO", "BSE 500": "BSE-500.BO"}


def yahoo_symbol(nse_symbol: str) -> str:
    return f"{nse_symbol.strip()}.NS"


def parse_constituents(csv_text: str) -> pd.DataFrame:
    df = pd.read_csv(io.StringIO(csv_text))
    df = df.rename(columns={"Company Name": "company", "Industry": "industry",
                            "Symbol": "symbol", "ISIN Code": "isin"})
    df["symbol"] = df["symbol"].str.strip()
    return df[["symbol", "company", "industry", "isin"]].drop_duplicates("symbol")


def fetch_constituents(list_name: str) -> pd.DataFrame:
    r = requests.get(NIFTY_URL.format(NIFTY_LISTS[list_name]), headers={"User-Agent": "Mozilla/5.0"}, timeout=30)
    r.raise_for_status()
    return parse_constituents(r.text)


def build_stock_universe(nifty500: pd.DataFrame, midcap150: pd.DataFrame, smallcap250: pd.DataFrame) -> pd.DataFrame:
    """One row per Nifty 500 stock, with a `segment` tag for the Stocks filter."""
    df = nifty500.copy()
    mid, small = set(midcap150["symbol"]), set(smallcap250["symbol"])
    df["segment"] = ["Midcap 150" if s in mid else "Smallcap 250" if s in small else "Nifty 100"
                     for s in df["symbol"]]
    df["yahoo"] = df["symbol"].map(yahoo_symbol)
    return df.sort_values("symbol").reset_index(drop=True)


def build_index_universe(nse_stats: pd.DataFrame, as_of: pd.Timestamp,
                         min_bars: int = MIN_INDEX_BARS, max_stale_days: int = 30) -> tuple[pd.DataFrame, list[str]]:
    """Index list for the Indices filter: live NSE archive series + the BSE indices Yahoo serves.

    `nse_stats` has one row per NSE index: name, bars, last (date). Uncategorised NSE indices
    (thematic, strategy, factor) default to Thematic. Returns (list, curated names with no OHLC in the archive).
    """
    live = nse_stats[(nse_stats.bars >= min_bars) & (nse_stats["last"] >= as_of - pd.Timedelta(days=max_stale_days))]
    category = {n: "Broad" for n in NSE_BROAD} | {n: "Sectoral" for n in NSE_SECTORAL}
    nse = pd.DataFrame({"name": live["name"], "exchange": "NSE",
                        "category": live["name"].map(category).fillna("Thematic"),
                        "source": "nse", "symbol": live["name"]})
    bse = pd.DataFrame([(n, "BSE", "Broad", "yahoo", y) for n, y in BSE_YAHOO.items()], columns=nse.columns)
    unknown = sorted(set(category) - set(nse_stats["name"]))
    order = {"Broad": 0, "Sectoral": 1, "Thematic": 2}
    out = pd.concat([nse, bse], ignore_index=True)
    out = out.sort_values(["exchange", "category", "name"], key=lambda s: s.map(order) if s.name == "category" else s)
    return out.reset_index(drop=True), unknown


def load_indices() -> pd.DataFrame:
    """Index list built by scripts/build_indices.py: name, exchange, category, source (nse|yahoo), symbol."""
    return pd.read_csv(INDICES_CSV)
