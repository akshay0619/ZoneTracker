# Zone Tracker

Demand / supply zone scanner for NSE stocks (Nifty 500) and NSE/BSE indices, ported from the
*Zone Indicator* Pine Script. Every weekday after the close it scans six timeframes (D, W, M, Q, H, Y)
and shows zones that price is **approaching** (fresh, within 3%) or **reacting** from (inside, never breached).

- Data: stocks and BSE indices from Yahoo Finance, NSE indices from NSE's daily archive (`ind_close_all`).
- Dashboard: `app/dashboard.py` (Streamlit). Daily job: `scripts/run_daily.py`.

## Run locally

```powershell
py -3.12 -m venv --prompt ZoneTracker .venv            # shows as (ZoneTracker) when active
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pip install -e . --no-deps
.\.venv\Scripts\python.exe scripts\run_daily.py        # after 19:00 IST
.\.venv\Scripts\streamlit.exe run app/dashboard.py
.\.venv\Scripts\python.exe -m pytest -q
```

## Deploy (free): GitHub Actions + Streamlit Community Cloud

The daily job runs on GitHub Actions at 19:00 IST (Mon-Fri) and commits the refreshed `data/` folder;
Streamlit Community Cloud redeploys the dashboard on every push.

1. **Install Git** (once): `winget install --id Git.Git -e`, then reopen the terminal.
2. **Create an empty GitHub repository** (Private is fine; the app can still be public). Don't add a README.
3. **Push this folder** (replace `<you>/<repo>`):
   ```powershell
   git init -b main
   git add .
   git commit -m "Zone Tracker"
   git remote add origin https://github.com/<you>/<repo>.git
   git push -u origin main
   ```
4. **Test the daily job**: GitHub → *Actions* → *Daily scan* → *Run workflow*. When it finishes,
   the log ends with the signal table and a new "Daily scan" commit appears.
5. **Deploy the dashboard**: [share.streamlit.io](https://share.streamlit.io) → *Create app* → pick the repo,
   branch `main`, main file `app/dashboard.py`; *Advanced settings* → Python **3.12** → *Deploy*.
   In the app's *Settings → Sharing*, set **Who can view this app** to *This app is public*.

### Operating notes

- GitHub's scheduler can start a job 5-30 minutes late at busy times; the dashboard shows the close date it is using.
- Scheduled workflows pause after 60 days without repository activity. The daily data commits keep it active.
- If NSE or Yahoo blocks GitHub's servers, the job fails and GitHub emails you. The dashboard keeps the last good data.
- After NSE launches new indices, they appear automatically once they have about 5 months of history.
