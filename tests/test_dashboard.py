"""Headless smoke test of the Streamlit page against the real latest.csv (skipped if no scan yet)."""
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "app" / "dashboard.py"
pytestmark = pytest.mark.skipif(not (ROOT / "data" / "results" / "latest.csv").exists(), reason="no scan results")
MARKET, CRITERIA, SIDE, TIMEFRAME = range(4)  # button_group order on the page


@pytest.mark.parametrize("market", ["Stocks", "Indices"])
@pytest.mark.parametrize("criteria", ["Approaching", "Reacting"])
def test_every_timeframe_renders(market, criteria):
    at = AppTest.from_file(str(APP), default_timeout=30).run()
    at.button_group[MARKET].set_value(market).run()
    at.button_group[CRITERIA].set_value(criteria).run()
    for tf in ["D", "W", "M", "Q", "H", "Y"]:
        at.button_group[TIMEFRAME].set_value(tf).run()
        assert not at.exception, at.exception


def test_search_with_no_match_shows_empty_state():
    at = AppTest.from_file(str(APP), default_timeout=30).run()
    at.text_input[0].set_value("zzzz-no-such-symbol").run()
    assert not at.exception
    assert not at.button  # no "Show more" on an empty result
