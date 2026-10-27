import pandas as pd

from zonetracker.links import name_key, pick_match, stock_links
from zonetracker.ui_filters import attach_links, filter_signals, score_breakdown, side_counts

COLS = ["kind", "symbol", "name", "group", "exchange", "tf", "signal", "side", "score", "distance_pct"]
ROWS = [
    ("Stock", "RELIANCE", "Reliance Industries", "Nifty 100", "NSE", "D", "Approaching", "Demand", 12, 2.5),
    ("Stock", "CUMMINSIND", "Cummins India", "Midcap 150", "NSE", "D", "Approaching", "Demand", 13, 1.0),
    ("Stock", "IEX", "Indian Energy Exchange", "Smallcap 250", "NSE", "D", "Approaching", "Supply", 11, 0.5),
    ("Stock", "M&M", "Mahindra & Mahindra", "Nifty 100", "NSE", "D", "Reacting", "Demand", 9, -1.0),
    ("Stock", "TCS", "Tata Consultancy", "Nifty 100", "NSE", "W", "Approaching", "Demand", 12, 2.0),
    ("Index", "Nifty Bank", "Nifty Bank", "Sectoral", "NSE", "D", "Approaching", "Supply", 12, 1.5),
    ("Index", "^BSESN", "BSE Sensex", "Broad", "BSE", "D", "Approaching", "Supply", 11, 2.0),
]
DF = pd.DataFrame(ROWS, columns=COLS)


def syms(df: pd.DataFrame) -> list[str]:
    return df.symbol.tolist()


def test_kind_signal_tf_and_best_score_first():
    assert syms(filter_signals(DF, "Stock", "Approaching", "Both", "D")) == ["CUMMINSIND", "RELIANCE", "IEX"]


def test_score_ties_break_on_closest_zone():
    tie = DF.assign(score=12)
    assert syms(filter_signals(tie, "Stock", "Approaching", "Both", "D")) == ["IEX", "CUMMINSIND", "RELIANCE"]


def test_side_and_universe():
    assert syms(filter_signals(DF, "Stock", "Approaching", "Demand", "D")) == ["CUMMINSIND", "RELIANCE"]
    assert syms(filter_signals(DF, "Stock", "Approaching", "Both", "D", universe="Midcap 150")) == ["CUMMINSIND"]


def test_index_category_and_exchange():
    assert syms(filter_signals(DF, "Index", "Approaching", "Both", "D", categories=("Sectoral",))) == ["Nifty Bank"]
    assert syms(filter_signals(DF, "Index", "Approaching", "Both", "D", exchanges=("BSE",))) == ["^BSESN"]


def test_search_matches_symbol_or_name_literally():
    assert syms(filter_signals(DF, "Stock", "Reacting", "Both", "D", search="m&m")) == ["M&M"]
    assert syms(filter_signals(DF, "Stock", "Approaching", "Both", "D", search="energy")) == ["IEX"]


def test_side_counts_for_tiles():
    c = side_counts(DF, "Stock", "D")
    assert (c[("Approaching", "Demand")], c[("Approaching", "Supply")], c[("Reacting", "Demand")]) == (2, 1, 1)


def test_stock_links_are_url_encoded():
    chart, fundamental = stock_links("M&M")
    assert chart == "https://www.tradingview.com/chart/?symbol=NSE%3AM%26M"
    assert fundamental == "https://www.screener.in/company/M%26M/"


def test_attach_links_uses_index_map_and_leaves_unknown_blank():
    links = pd.DataFrame({"name": ["Nifty Bank", "BSE Sensex"],
                          "chart": ["https://tv/BANKNIFTY", "https://tv/SENSEX"],
                          "fundamental": ["https://scr/BANKNIFTY", None]})
    out = attach_links(DF, links).set_index("symbol")
    assert out.loc["RELIANCE", "fundamental"] == "https://www.screener.in/company/RELIANCE/"
    assert out.loc["Nifty Bank", "chart"] == "https://tv/BANKNIFTY"
    assert out.loc["^BSESN", "fundamental"] is None


def test_index_name_matching_is_exact_after_normalising():
    assert name_key("NIFTY100 Quality 30") == name_key("Nifty 100 Quality 30 Index")
    hits = [("NSE:NIFTY500_HEALTH", "Nifty 500 Healthcare Index"), ("NSE:NIFTY_HEALTHCARE", "Nifty Healthcare Index")]
    assert pick_match("Nifty Healthcare", hits) == "NSE:NIFTY_HEALTHCARE"
    assert pick_match("Nifty Hospitals", hits) is None


def test_score_breakdown_totals():
    row = pd.Series(dict(freshness=2, strength=2, time_at_zone=2, move_from_zone=0, reversal_break=0,
                         reward_risk=3, coinciding=2))
    b = score_breakdown(row)
    assert b.Component.tolist()[-1] == "Total" and b.Points.iloc[-1] == 11 and b.Max.iloc[-1] == 15
