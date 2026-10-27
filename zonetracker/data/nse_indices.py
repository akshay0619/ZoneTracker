"""NSE index OHLC from the free daily archive ind_close_all_DDMMYYYY.csv (available from mid-2012).

Downloaded days are cached in one long-format file, so updates only fetch new dates.
Weekends are not fetched, so rare weekend sessions (Muhurat, Budget Saturdays) are skipped.
"""
import io
import re
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import requests

ARCHIVE_URL = "https://nsearchives.nseindia.com/content/indices/ind_close_all_{:%d%m%Y}.csv"
ARCHIVE_START = date(2012, 1, 1)
RECENT_DAYS = 3
COLUMNS = ["name", "date", "open", "high", "low", "close", "volume"]
# Non-equity or derived series that make no sense for zones
EXCLUDE = re.compile(r"g-sec|bond|rate index|vix|inverse|leverage|\btr\b|futures|arbitrage|usd|dividend points", re.I)
# Old CNX-era names (lowercase) -> current names
ALIASES = {
    "s&p cnx nifty": "Nifty 50", "cnx nifty": "Nifty 50", "cnx nifty junior": "Nifty Next 50",
    "s&p cnx 500": "Nifty 500", "cnx midcap": "Nifty Midcap 100", "cnx smallcap": "Nifty Smallcap 100",
    "cnx finance": "Nifty Financial Services", "cnx consumption": "Nifty India Consumption",
    "cnx service sector": "Nifty Services Sector", "cpse": "Nifty CPSE",
    "nifty healthcare index": "Nifty Healthcare",
    # 2016-07 .. 2018-03 names
    "nifty free float midcap 100": "Nifty Midcap 100", "nifty free float smallcap 100": "Nifty Smallcap 100",
    "nifty quality 30": "NIFTY100 Quality 30",
    # 2015 short codes -> 2016 names
    "lix 15": "Nifty100 Liquid 15", "lix15 midcap": "Nifty Midcap Liquid 15", "nv 20": "Nifty50 Value 20",
    "ni15": "Nifty Growth Sectors 15", "cnx shariah25": "Nifty Shariah 25",
    "cnx dividend opportunities": "Nifty Dividend Opportunities 50",
    # 2024 corporate-group renames
    "nifty tata group": "Nifty India Corporate Group Index - Tata Group",
    "nifty tata group 25% cap": "Nifty India Corporate Group Index - Tata Group 25% Cap",
    "nifty aditya birla group": "Nifty India Corporate Group Index - Aditya Birla Group",
    "nifty mahindra group": "Nifty India Corporate Group Index - Mahindra Group",
}


def canonical_name(raw: str) -> str:
    name = " ".join(str(raw).split())
    key = name.lower()
    if key in ALIASES:
        return ALIASES[key]
    if key.startswith("cnx "):
        name = "Nifty " + name[4:]
    # NSE mixes "NIFTY Midcap 100" and "Nifty Midcap 100": normalise the leading word only
    name = re.sub(r"^nifty\b", "Nifty", name, flags=re.I)
    # Cached rows already went through the CNX -> Nifty step, so look the aliases up again
    return ALIASES.get(f"cnx {name[6:].lower()}", name) if name.startswith("Nifty ") else name


def parse_index_file(text: str, day: date | None = None) -> pd.DataFrame:
    """`day` (the archive file's date) overrides the in-file date, whose format varies by year."""
    raw = pd.read_csv(io.StringIO(text))
    dates = (pd.Series(pd.Timestamp(day), index=raw.index) if day else
             pd.to_datetime(raw["Index Date"], format="mixed", dayfirst=True))
    df = pd.DataFrame({
        "name": raw["Index Name"].map(canonical_name),
        "date": dates,
        "open": raw["Open Index Value"], "high": raw["High Index Value"],
        "low": raw["Low Index Value"], "close": raw["Closing Index Value"], "volume": raw["Volume"],
    })
    cols = ["open", "high", "low", "close", "volume"]
    df[cols] = df[cols].apply(pd.to_numeric, errors="coerce")
    df[["open", "high", "low", "close"]] = df[["open", "high", "low", "close"]].where(lambda x: x > 0)
    return df[~df["name"].str.contains(EXCLUDE)].dropna(subset=["open", "high", "low", "close"])


def weekdays(start: date, end: date) -> list[date]:
    days = (start + timedelta(n) for n in range((end - start).days + 1))
    return [d for d in days if d.weekday() < 5]


class NSEIndexArchive:
    """Local cache: `ohlc.csv.gz` (long format) + `missing.txt` (dates that returned 404 = holidays)."""

    def __init__(self, root: Path = Path("data/nse_indices")):
        self.root = root
        # One file per month, so a daily update rewrites only the current month (small git commits)
        self.month_dir, self.missing_file = root / "ohlc", root / "missing.txt"
        self._legacy = root / "ohlc.csv.gz"  # pre-split single-file cache; migrated by update()
        self._session = requests.Session()
        self._session.headers["User-Agent"] = "Mozilla/5.0"

    def _read_raw(self) -> pd.DataFrame:
        files = sorted(self.month_dir.glob("*.csv.gz")) + ([self._legacy] if self._legacy.exists() else [])
        if not files:
            return pd.DataFrame(columns=COLUMNS).astype({"date": "datetime64[ns]"})
        return pd.concat([pd.read_csv(f, parse_dates=["date"]) for f in files], ignore_index=True)

    def load(self) -> pd.DataFrame:
        data = self._read_raw()
        # Re-apply aliases so new rename rules fix the cache without re-downloading
        names = {n: canonical_name(n) for n in data["name"].unique()}
        data["name"] = data["name"].map(names)
        return data.drop_duplicates(["name", "date"], keep="last").sort_values(["name", "date"], ignore_index=True)

    def _missing(self) -> set[date]:
        if not self.missing_file.exists():
            return set()
        return {date.fromisoformat(s) for s in self.missing_file.read_text().split()}

    def _fetch(self, d: date) -> pd.DataFrame | None:
        for attempt in range(3):
            try:
                r = self._session.get(ARCHIVE_URL.format(d), timeout=30)
                if r.status_code == 404:
                    return None
                r.raise_for_status()
                return parse_index_file(r.text, d)
            except requests.RequestException:
                time.sleep(2 * (attempt + 1))
        raise RuntimeError(f"NSE archive unreachable for {d}")

    def update(self, start: date = ARCHIVE_START, end: date | None = None,
               workers: int = 4, save_every: int = 100) -> tuple[int, int]:
        """Fetch every weekday not yet cached. Returns (days added, holidays found). Resumable."""
        end = end or date.today()
        if self._legacy.exists():
            self._save([self._read_raw()], self._missing())
            self._legacy.unlink()
        data, missing = self.load(), self._missing()
        have = set(pd.to_datetime(data["date"]).dt.date) | missing
        todo = [d for d in weekdays(start, end) if d not in have]
        new, added, holidays = [], 0, 0
        recent = date.today() - timedelta(days=RECENT_DAYS)
        with ThreadPoolExecutor(workers) as pool:
            for i, (d, df) in enumerate(zip(todo, pool.map(self._fetch, todo)), 1):
                if df is None:
                    if d < recent:  # a recent 404 may just be "not published yet": retry next run
                        missing.add(d)
                    holidays += 1
                else:
                    new.append(df)
                    added += 1
                if i % save_every == 0 or i == len(todo):
                    self._save(new, missing)
                    new = []
        return added, holidays

    def _save(self, frames: list[pd.DataFrame], missing: set[date]) -> None:
        """Merge `frames` into their month files; untouched months are not rewritten."""
        self.month_dir.mkdir(parents=True, exist_ok=True)
        frames = [f for f in frames if len(f)]
        if frames:
            rows = pd.concat(frames, ignore_index=True)
            for month, part in rows.groupby(rows["date"].dt.strftime("%Y-%m")):
                path = self.month_dir / f"{month}.csv.gz"
                if path.exists():
                    part = pd.concat([pd.read_csv(path, parse_dates=["date"]), part], ignore_index=True)
                part = part.drop_duplicates(["name", "date"], keep="last").sort_values(["name", "date"])
                # mtime=0: identical data gives an identical file, so git sees no change
                part.to_csv(path, index=False, compression={"method": "gzip", "mtime": 0})
        self.missing_file.write_text("\n".join(sorted(d.isoformat() for d in missing)))


class NSEIndexProvider:
    """DataProvider over the local archive; `symbol` is the canonical NSE index name."""

    def __init__(self, archive: NSEIndexArchive | None = None):
        self._data = (archive or NSEIndexArchive()).load()

    def names(self) -> list[str]:
        return sorted(self._data["name"].unique())

    def daily(self, symbol: str) -> pd.DataFrame:
        df = self._data[self._data["name"] == symbol]
        if df.empty:
            raise ValueError(f"No NSE archive data for {symbol}")
        df = df.set_index(pd.DatetimeIndex(df["date"], name="date"))
        return df[["open", "high", "low", "close", "volume"]].fillna({"volume": 0}).astype(float)
