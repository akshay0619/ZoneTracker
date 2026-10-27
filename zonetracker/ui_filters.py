"""Pure filtering / shaping of scan results for the dashboard (kept out of Streamlit so it is testable)."""
import pandas as pd

from zonetracker.links import stock_links

TF_LABELS = {"D": "Daily", "W": "Weekly", "M": "Monthly", "Q": "Quarterly", "H": "Half Yearly", "Y": "Yearly"}
STOCK_UNIVERSES = ("Nifty 500", "Midcap 150", "Smallcap 250")  # Nifty 500 = all three segments
INDEX_CATEGORIES = ("Broad", "Sectoral", "Thematic")


def filter_signals(df: pd.DataFrame, kind: str, signal: str, side: str, tf: str,
                   universe: str = "Nifty 500", categories: tuple[str, ...] = INDEX_CATEGORIES,
                   exchanges: tuple[str, ...] = ("NSE", "BSE"), search: str = "") -> pd.DataFrame:
    """kind: "Stock" | "Index"; side: "Demand" | "Supply" | "Both"."""
    q = df[(df.kind == kind) & (df.signal == signal) & (df.tf == tf)]
    if side != "Both":
        q = q[q.side == side]
    if kind == "Stock" and universe != "Nifty 500":
        q = q[q.group == universe]
    if kind == "Index":
        q = q[q.group.isin(categories) & q.exchange.isin(exchanges)]
    if search:
        s = search.strip().lower()
        q = q[q.symbol.str.lower().str.contains(s, regex=False) | q.name.str.lower().str.contains(s, regex=False)]
    # Best zones first; ties: closest to the zone first
    return q.assign(_d=q.distance_pct.abs()).sort_values(["score", "_d"], ascending=[False, True]).drop(columns="_d")


def side_counts(df: pd.DataFrame, kind: str, tf: str) -> dict[tuple[str, str], int]:
    """Signal counts per (signal, side) for the headline tiles, before side/universe filters."""
    q = df[(df.kind == kind) & (df.tf == tf)]
    return {(sig, side): int(((q.signal == sig) & (q.side == side)).sum())
            for sig in ("Approaching", "Reacting") for side in ("Demand", "Supply")}


def attach_links(df: pd.DataFrame, index_links: pd.DataFrame) -> pd.DataFrame:
    """Add `chart` (TradingView) and `fundamental` (Screener) URLs; indices use the resolved link map."""
    out = df.copy()
    stock = out.kind == "Stock"
    links = [stock_links(s) for s in out.loc[stock, "symbol"]]
    out.loc[stock, "chart"] = [c for c, _ in links]
    out.loc[stock, "fundamental"] = [f for _, f in links]
    idx = index_links.set_index("name")
    for col in ("chart", "fundamental"):
        out.loc[~stock, col] = out.loc[~stock, "name"].map(idx[col])
    out[["chart", "fundamental"]] = out[["chart", "fundamental"]].astype(object).where(
        out[["chart", "fundamental"]].notna(), None)
    return out


def score_breakdown(row: pd.Series) -> pd.DataFrame:
    """Same components and order as the Pine grade tooltip."""
    parts = [("Freshness", row.freshness, 2), ("Strength", row.strength, 2), ("Time at Zone", row.time_at_zone, 2),
             ("Move From Zone", row.move_from_zone, 2), ("Reversal Break", row.reversal_break, 2),
             ("Reward:Risk", row.reward_risk, 3), ("Coinciding", row.coinciding, 2)]
    out = pd.DataFrame(parts, columns=["Component", "Points", "Max"])
    total = pd.DataFrame([("Total", out.Points.sum(), 15)], columns=out.columns)
    return pd.concat([out, total], ignore_index=True)
