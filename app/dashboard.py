"""Zone Tracker dashboard. Run: streamlit run app/dashboard.py"""
import os
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

# Streamlit Cloud runs this file without installing the package; data paths are relative to the root
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

from zonetracker.links import load_index_links  # noqa: E402
from zonetracker.ui_cards import cards_html, counters_html  # noqa: E402
from zonetracker.ui_filters import (INDEX_CATEGORIES, STOCK_UNIVERSES, TF_LABELS, attach_links,  # noqa: E402
                                    filter_signals, side_counts)

RESULTS = ROOT / "data" / "results" / "latest.csv"
PAGE = 36  # tiles per "Show more"
CRITERIA_HELP = ("Approaching: fresh zone, close within 3% of the proximal line. "
                 "Reacting: close inside the zone, never breached. "
                 "Daily and Weekly show grade A and above for Approaching, B and above for Reacting.")

st.set_page_config(page_title="Zone Tracker", page_icon="▦", layout="wide")
st.html(f"<style>{(ROOT / 'app' / 'style.css').read_text(encoding='utf-8')}</style>")


@st.cache_data
def load(path: str, mtime: float) -> pd.DataFrame:  # mtime busts the cache when a new scan lands
    with_links = attach_links(pd.read_csv(path), load_index_links())
    return with_links


if not RESULTS.exists():
    st.html('<div class="zt-empty">No scan results yet. Run <code>python scripts/run_scan.py</code> after market close.</div>')
    st.stop()
df = load(str(RESULTS), RESULTS.stat().st_mtime)
as_of = pd.Timestamp(df.as_of.max()).strftime("%d %b %Y")
st.html(f'<div class="zt-mast"><h1>Zone Tracker</h1><p>Zones at the close of <strong>{as_of}</strong></p></div>')

market = st.segmented_control("Market", ["Stocks", "Indices"], default="Stocks", label_visibility="collapsed") or "Stocks"
kind = "Index" if market == "Indices" else "Stock"

c1, c2 = st.columns([1, 1])
signal = c1.segmented_control("Criteria", ["Approaching", "Reacting"], default="Approaching", help=CRITERIA_HELP) or "Approaching"
side = c2.segmented_control("Zone type", ["Demand", "Supply", "Both"], default="Both") or "Both"
tf = st.segmented_control("Timeframe", list(TF_LABELS), default="D", format_func=TF_LABELS.get) or "D"

c4, c5 = st.columns([1, 1])
universe, categories = "Nifty 500", INDEX_CATEGORIES
if kind == "Stock":
    universe = c4.segmented_control("Universe", STOCK_UNIVERSES, default="Nifty 500") or "Nifty 500"
else:
    categories = tuple(c4.pills("Category", INDEX_CATEGORIES, default=list(INDEX_CATEGORIES), selection_mode="multi"))
search = c5.text_input("Search", placeholder="Symbol or name", label_visibility="visible")

st.html(counters_html(side_counts(df, kind, tf)))

view = filter_signals(df, kind, signal, side, tf, universe, categories or INDEX_CATEGORIES, ("NSE", "BSE"), search)
filters_key = (kind, signal, side, tf, universe, categories, search)
if st.session_state.get("filters_key") != filters_key:  # new filters: start from the first page
    st.session_state.filters_key, st.session_state.shown = filters_key, PAGE

if view.empty:
    st.html(f'<div class="zt-empty">No {side.lower() if side != "Both" else ""} zones are {signal.lower()} on the '
            f'{TF_LABELS[tf].lower()} timeframe. Try another timeframe or zone type.</div>')
else:
    st.html(cards_html(view.head(st.session_state.shown)))
    if len(view) > st.session_state.shown:
        left = len(view) - st.session_state.shown
        if st.button(f"Show {min(left, PAGE)} more of {left}", width="stretch"):
            st.session_state.shown += PAGE
            st.rerun()
