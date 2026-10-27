import pandas as pd

from zonetracker.data.universe import build_index_universe, build_stock_universe, parse_constituents, yahoo_symbol

HEADER = "Company Name,Industry,Symbol,Series,ISIN Code\n"


def csv(*symbols: str) -> str:
    return HEADER + "".join(f"{s} Ltd.,Industry,{s},EQ,INE{i:09d}\n" for i, s in enumerate(symbols))


def test_parse_constituents_columns_and_strip():
    df = parse_constituents(HEADER + "Mahindra & Mahindra Ltd.,Automobile, M&M ,EQ,INE101A01026\n")
    assert list(df.columns) == ["symbol", "company", "industry", "isin"]
    assert df.symbol.iloc[0] == "M&M"


def test_yahoo_symbol():
    assert yahoo_symbol("BAJAJ-AUTO") == "BAJAJ-AUTO.NS"


def test_segments_tagged_from_sub_lists():
    n500 = parse_constituents(csv("RELIANCE", "TCS", "CUMMINSIND", "IEX"))
    mid = parse_constituents(csv("CUMMINSIND"))
    small = parse_constituents(csv("IEX"))
    u = build_stock_universe(n500, mid, small).set_index("symbol")
    assert u.loc["RELIANCE", "segment"] == "Nifty 100"
    assert u.loc["CUMMINSIND", "segment"] == "Midcap 150"
    assert u.loc["IEX", "segment"] == "Smallcap 250"
    assert u.loc["TCS", "yahoo"] == "TCS.NS"


AS_OF = pd.Timestamp("2026-10-26")


def stats(*rows: tuple[str, int, str]) -> pd.DataFrame:
    return pd.DataFrame([(n, b, pd.Timestamp(d)) for n, b, d in rows], columns=["name", "bars", "last"])


def test_index_universe_categories_filters_and_bse():
    s = stats(("Nifty 50", 3600, "2026-10-26"), ("Nifty Bank", 3600, "2026-10-26"),
              ("Nifty Alpha 50", 2000, "2026-10-26"),   # uncurated -> Thematic
              ("LIX 15", 563, "2015-11-06"),             # discontinued
              ("Nifty Brand New", 40, "2026-10-26"))     # too little data
    out, unknown = build_index_universe(s, AS_OF)
    cat = out.set_index("name").category
    assert (cat["Nifty 50"], cat["Nifty Bank"], cat["Nifty Alpha 50"]) == ("Broad", "Sectoral", "Thematic")
    assert "LIX 15" not in cat and "Nifty Brand New" not in cat
    bse = out[out.exchange == "BSE"]
    assert set(bse.source) == {"yahoo"} and "^BSESN" in set(bse.symbol)
    assert out.iloc[0].exchange == "BSE"  # BSE block sorts before NSE
    assert "Nifty Power" in unknown  # curated but no OHLC in this archive snapshot


def test_index_universe_ordering_within_exchange():
    s = stats(("Nifty Alpha 50", 2000, "2026-10-26"), ("Nifty Bank", 3600, "2026-10-26"),
              ("Nifty 50", 3600, "2026-10-26"))
    nse = build_index_universe(s, AS_OF)[0].query("exchange == 'NSE'")
    assert nse.category.tolist() == ["Broad", "Sectoral", "Thematic"]
