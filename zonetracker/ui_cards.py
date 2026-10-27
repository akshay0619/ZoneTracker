"""HTML for the dashboard's zone tiles and counters (pure functions, so they are testable)."""
from html import escape

import pandas as pd

from zonetracker.ui_filters import score_breakdown

SIDE_MARK = {"Demand": "▲", "Supply": "▼"}
GRADE_CLASS = {"A+": "g-ap", "A": "g-a", "B": "g-b", "C": "g-c"}


def gauge(proximal: float, distal: float, close: float, pad: float = 0.18) -> tuple[float, float, float]:
    """(zone left %, zone width %, close position %) on a strip spanning zone and close, padded each side."""
    lo, hi = min(proximal, distal, close), max(proximal, distal, close)
    span = (hi - lo) or abs(close) * 0.01 or 1.0
    lo, hi = lo - span * pad, hi + span * pad
    pct = lambda v: (v - lo) / (hi - lo) * 100
    z0, z1 = sorted((pct(proximal), pct(distal)))
    return round(z0, 2), round(max(z1 - z0, 0.8), 2), round(pct(close), 2)


def gauge_tooltip(row: pd.Series) -> str:
    """Hover text on the gauge: the numbers the tile no longer prints."""
    lo, hi = sorted((row.proximal, row.distal))
    where = ("inside the zone" if row.signal == "Reacting"
             else f"{row.distance_pct:.2f}% {'above' if row.side == 'Demand' else 'below'} the zone")
    return f"Zone {lo:,.2f} – {hi:,.2f}, close {row.close:,.2f}, {where}"


def _link(url, label: str, kind: str) -> str:
    if not isinstance(url, str) or not url:
        return f'<span class="zt-btn {kind} is-off" title="Not available for this instrument">{label}</span>'
    return f'<a class="zt-btn {kind}" href="{escape(url)}" target="_blank" rel="noopener">{label}</a>'


def _breakdown(row: pd.Series) -> str:
    b = score_breakdown(row)
    body = "".join(f"<tr><td>{escape(c)}</td><td>{p:g}</td><td>{m}</td></tr>" for c, p, m in b.iloc[:-1].itertuples(index=False))
    return (f'<details class="zt-more"><summary>Score {b.Points.iloc[-1]:g}/15</summary><table>'
            f'<thead><tr><th>Component</th><th>Points</th><th>Max</th></tr></thead><tbody>{body}</tbody>'
            f'<tfoot><tr><td>Total</td><td>{b.Points.iloc[-1]:g}</td><td>15</td></tr></tfoot></table></details>')


def card_html(row: pd.Series) -> str:
    is_index = row.kind == "Index"
    title = row["name"] if is_index else row.symbol
    subtitle = f"{row.group} index, {row.exchange}" if is_index else f"{row['name']}"
    z_left, z_width, c_pos = gauge(row.proximal, row.distal, row.close)
    tip = escape(gauge_tooltip(row))
    group_chip = "" if is_index else f'<span class="zt-chip is-group">{escape(str(row.group))}</span>'
    return f"""<article class="zt-card is-{row.side.lower()}">
  <div class="zt-head">
    <h3 class="zt-title">{escape(str(title))}</h3>
    <span class="zt-grade {GRADE_CLASS.get(row.grade, 'g-c')}" title="Grade {row.grade}, {row.score:g} of 15">{row.grade}</span>
  </div>
  <p class="zt-sub">{escape(str(subtitle))}</p>
  <p class="zt-tags"><span class="zt-chip is-side">{SIDE_MARK[row.side]} {row.side}</span>
    <span class="zt-chip is-pattern">{row.pattern}</span>{group_chip}</p>
  <div class="zt-gauge" role="img" aria-label="{tip}" title="{tip}">
    <span class="zt-band" style="left:{z_left}%;width:{z_width}%"></span>
    <span class="zt-close" style="left:{c_pos}%"></span>
  </div>
  <div class="zt-actions">{_link(row.chart, "Chart", "is-primary")}{_link(row.fundamental, "Fundamental", "is-secondary")}</div>
  {_breakdown(row)}
</article>"""


def cards_html(rows: pd.DataFrame) -> str:
    return '<section class="zt-grid">' + "".join(card_html(r) for _, r in rows.iterrows()) + "</section>"


def counters_html(counts: dict[tuple[str, str], int]) -> str:
    def group(sig: str) -> str:
        d, s = counts[(sig, "Demand")], counts[(sig, "Supply")]
        return (f'<span class="zt-count"><span class="zt-count-label">{sig}</span>'
                f'<span class="is-demand" title="{d} demand zones">▲ {d}</span>'
                f'<span class="is-supply" title="{s} supply zones">▼ {s}</span></span>')
    return f'<div class="zt-counts">{group("Approaching")}{group("Reacting")}</div>'
