from datetime import date

import pandas as pd
import pytest

from zonetracker.data.nse_indices import (NSEIndexArchive, NSEIndexProvider, canonical_name,
                                          parse_index_file, weekdays)

HEADER = ("Index Name,Index Date,Open Index Value,High Index Value,Low Index Value,Closing Index Value,"
          "Points Change,Change(%),Volume,Turnover (Rs. Cr.),P/E,P/B,Div Yield\n")


def file_text(day: str, rows: list[tuple]) -> str:
    return HEADER + "".join(f"{n},{day},{o},{h},{l},{c},0,0,{v},0,0,0,0\n" for n, o, h, l, c, v in rows)


@pytest.mark.parametrize("raw, name", [
    ("S&P CNX Nifty", "Nifty 50"), ("CNX Nifty", "Nifty 50"), ("CNX Nifty Junior", "Nifty Next 50"),
    ("CNX Midcap", "Nifty Midcap 100"), ("CNX Bank", "Nifty Bank"), ("CNX 100", "Nifty 100"),
    ("NIFTY Midcap 100", "Nifty Midcap 100"), ("Nifty Healthcare Index", "Nifty Healthcare"),
    ("CPSE", "Nifty CPSE"), ("Nifty Free Float Midcap 100", "Nifty Midcap 100"),
    ("CNX Dividend Opportunities", "Nifty Dividend Opportunities 50"),
    ("Nifty Dividend Opportunities", "Nifty Dividend Opportunities 50"),  # already-converted cache name
    ("Nifty Finance", "Nifty Financial Services"), ("  Nifty   Bank ", "Nifty Bank"), ("Nifty Oil & Gas", "Nifty Oil & Gas"),
])
def test_canonical_name(raw, name):
    assert canonical_name(raw) == name


def test_parse_filters_non_equity_and_bad_rows():
    text = file_text("23-10-2026", [
        ("Nifty 50", 100, 110, 95, 105, 1000),
        ("India VIX", 12, 13, 11, 12.5, "-"),
        ("Nifty 10 yr Benchmark G-Sec", 2000, 2001, 1999, 2000, "-"),
        ("Nifty50 TR 2x Leverage", 1, 2, 1, 2, "-"),
        ("Nifty Bank", "-", "-", "-", 500, "-"),   # close only -> dropped
        ("Nifty IT", 0, 0, 0, 300, 5),            # zero OHLC -> dropped
    ])
    df = parse_index_file(text)
    assert df["name"].tolist() == ["Nifty 50"]
    row = df.iloc[0]
    assert row.date == pd.Timestamp("2026-10-23") and (row.open, row.close, row.volume) == (100, 105, 1000)


def test_slash_dates_and_file_date_override():
    text = file_text("09/06/2014", [("CNX Nifty", 1, 3, 0.5, 2, 10)])
    assert parse_index_file(text).date.iloc[0] == pd.Timestamp("2014-06-09")  # day-first
    assert parse_index_file(text, date(2014, 6, 9)).date.iloc[0] == pd.Timestamp("2014-06-09")


def test_weekdays_skips_weekends():
    assert weekdays(date(2026, 10, 23), date(2026, 10, 27)) == [date(2026, 10, 23), date(2026, 10, 26), date(2026, 10, 27)]


class FakeArchive(NSEIndexArchive):
    """Serves canned files instead of hitting NSE."""

    def __init__(self, root, files: dict[date, str]):
        super().__init__(root)
        self.files, self.calls = files, []

    def _fetch(self, d):
        self.calls.append(d)
        return parse_index_file(self.files[d]) if d in self.files else None


def test_update_caches_resumes_and_feeds_provider(tmp_path):
    files = {date(2020, 1, 1): file_text("01-01-2020", [("CNX Nifty", 1, 3, 0.5, 2, 10)]),
             date(2020, 1, 3): file_text("03-01-2020", [("Nifty 50", 2, 4, 1.5, 3, 20)])}
    arc = FakeArchive(tmp_path, files)
    assert arc.update(date(2020, 1, 1), date(2020, 1, 3), workers=1) == (2, 1)  # 2 Jan = 404
    again = FakeArchive(tmp_path, files)
    assert again.update(date(2020, 1, 1), date(2020, 1, 3), workers=1) == (0, 0)
    assert again.calls == []  # old 404 remembered as a holiday
    d = NSEIndexProvider(again).daily("Nifty 50")
    assert d.index.tolist() == [pd.Timestamp("2020-01-01"), pd.Timestamp("2020-01-03")]
    assert d.close.tolist() == [2, 3]  # renamed CNX Nifty joins the same series
    assert [p.name for p in (tmp_path / "ohlc").iterdir()] == ["2020-01.csv.gz"]


def test_update_rewrites_only_the_touched_month(tmp_path):
    files = {date(2020, 1, 31): file_text("31-01-2020", [("Nifty 50", 1, 3, 0.5, 2, 10)]),
             date(2020, 2, 3): file_text("03-02-2020", [("Nifty 50", 2, 4, 1.5, 3, 20)])}
    FakeArchive(tmp_path, files).update(date(2020, 1, 31), date(2020, 1, 31), workers=1)
    jan = tmp_path / "ohlc" / "2020-01.csv.gz"
    before = jan.read_bytes()
    FakeArchive(tmp_path, files).update(date(2020, 1, 31), date(2020, 2, 3), workers=1)
    assert jan.read_bytes() == before  # January untouched
    assert (tmp_path / "ohlc" / "2020-02.csv.gz").exists()


def test_legacy_single_file_is_migrated_to_months(tmp_path):
    legacy = parse_index_file(file_text("02-01-2020", [("Nifty 50", 1, 3, 0.5, 2, 10)]))
    legacy.to_csv(tmp_path / "ohlc.csv.gz", index=False, compression="gzip")
    arc = FakeArchive(tmp_path, {})
    assert len(arc.load()) == 1  # readable before migration
    arc.update(date(2020, 1, 2), date(2020, 1, 2), workers=1)
    assert not (tmp_path / "ohlc.csv.gz").exists()
    assert NSEIndexProvider(arc).daily("Nifty 50").close.tolist() == [2]
