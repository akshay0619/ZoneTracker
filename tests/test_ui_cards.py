import pandas as pd

from zonetracker.ui_cards import card_html, counters_html, gauge, gauge_tooltip

ROW = pd.Series(dict(
    kind="Stock", symbol="M&M", name="Mahindra & Mahindra Ltd.", group="Nifty 100", exchange="NSE", tf="D",
    signal="Approaching", side="Demand", pattern="DBR", grade="A+", score=13.0, proximal=101.0, distal=97.0,
    close=103.0, distance_pct=1.98, chart="https://tv/x?a=1&b=2", fundamental=None,
    freshness=2, strength=2, time_at_zone=2, move_from_zone=2, reversal_break=0, reward_risk=3, coinciding=2))


def test_gauge_places_zone_and_close_inside_strip():
    z_left, z_width, c_pos = gauge(101, 97, 103)
    assert 0 < z_left < z_left + z_width < c_pos < 100   # demand zone left of the close


def test_gauge_close_inside_zone_and_zero_height():
    z_left, z_width, c_pos = gauge(101, 97, 99)
    assert z_left < c_pos < z_left + z_width
    assert gauge(100, 100, 100)[1] > 0  # degenerate zone still visible


def test_gauge_tooltip_carries_the_numbers():
    assert gauge_tooltip(ROW) == "Zone 97.00 – 101.00, close 103.00, 1.98% above the zone"
    assert gauge_tooltip(pd.Series({**ROW, "signal": "Reacting"})).endswith("inside the zone")
    assert gauge_tooltip(pd.Series({**ROW, "side": "Supply"})).endswith("1.98% below the zone")


def test_card_escapes_text_and_links_and_disables_missing():
    html = card_html(ROW)
    assert "M&amp;M" in html and "Mahindra &amp; Mahindra" in html
    assert 'class="zt-btn is-primary" href="https://tv/x?a=1&amp;b=2"' in html
    assert 'class="zt-btn is-secondary is-off"' in html and ">Fundamental<" in html  # no Screener link
    assert "is-demand" in html and ">A+<" in html and "Score 13/15" in html
    assert "<tfoot><tr><td>Total</td><td>13</td>" in html


def test_card_has_no_zone_close_distance_rows():
    html = card_html(ROW)
    assert "zt-figs" not in html and "<dt>" not in html
    assert 'class="zt-chip is-pattern">DBR<' in html and 'class="zt-chip is-group">Nifty 100<' in html


def test_index_card_uses_name_as_title():
    html = card_html(pd.Series({**ROW, "kind": "Index", "symbol": "^BSESN", "name": "BSE Sensex", "group": "Broad",
                                "exchange": "BSE"}))
    assert '<h3 class="zt-title">BSE Sensex</h3>' in html and "Broad index, BSE" in html


def test_counters():
    counts = {("Approaching", "Demand"): 16, ("Approaching", "Supply"): 4,
              ("Reacting", "Demand"): 25, ("Reacting", "Supply"): 1}
    html = counters_html(counts)
    assert "▲ 16" in html and "▼ 4" in html and "▲ 25" in html and "▼ 1" in html
