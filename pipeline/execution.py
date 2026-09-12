"""D3 — Thread B's execution model applied to hold-to-close signals (ACCEPTANCE A20).

Research form (research/thread_B_inversion/step8_execution.py): a resting limit `offset × ATR`
against the trade direction, filled only if the path touches it inside a window, unfilled
signals scored as ZERO (adverse selection counted), commission-only cost on fills; the metric is
per SIGNAL. Adapted here, unit = underlying index points:
  * ATR = 14-bar rolling mean of 5-minute (high − low) built with closed="left" (the bar that
    ends at or before the decision minute — no forward leak, unlike step8's label="right");
  * fill window = min(30 min, minutes-to-close − 5) after the entry bar;
  * both directions (puts/shorts mirrored: fill if high ≥ limit);
  * market entry pays COST_MARKET (the D1 round-trip budget); a filled limit pays COST_LIMIT.
"""
import numpy as np
import pandas as pd

from pipeline import stats

COST_MARKET = 1.0     # index points, the D1 round-trip budget (crossing the quoted spread)
COST_LIMIT = 0.10     # commission only — liquidity provided on entry (step8_execution.py:21)
OFFSETS = (0.25, 0.50, 1.00)
WINDOW_MAX = 30


def atr_at_decision(frame):
    """Per session: 5-minute ATR(14) available at each minute (from bars that already closed)."""
    d = frame.copy()
    d["bar5"] = (d["mod"] // 5) * 5
    b = d.groupby(["date", "bar5"]).agg(high=("high", "max"), low=("low", "min")).reset_index()
    b["rng"] = b["high"] - b["low"]
    b["atr"] = b.groupby("date")["rng"].transform(lambda s: s.rolling(14).mean())
    # the ATR usable at minute m is the one of the last COMPLETED 5-min bar: bar5 <= m - 5
    b["avail_from"] = b["bar5"] + 5
    return b[["date", "avail_from", "atr"]]


def limit_fills(frame, trades, offset):
    """Per-signal rows: filled flag, fill price, net points (0 if unfilled)."""
    by_date = {d: g.reset_index(drop=True) for d, g in frame.groupby("date")}
    atr_tab = atr_at_decision(frame)
    atr_by_date = {d: g for d, g in atr_tab.groupby("date")}
    rows = []
    for r in trades.itertuples(index=False):
        g = by_date.get(pd.Timestamp(r.date))
        a = atr_by_date.get(pd.Timestamp(r.date))
        if g is None or a is None:
            continue
        usable = a[a["avail_from"] <= r.decision_mod]["atr"].dropna()
        if usable.empty:
            continue
        atr = float(usable.iloc[-1])
        limit = r.entry_px - r.direction * offset * atr          # better than the market entry, against direction
        end = min(int(r.entry_mod) + WINDOW_MAX, int(r.exit_mod) - 5)
        win = g[(g["mod"] >= r.entry_mod) & (g["mod"] <= end)]
        touched = (win["low"] <= limit) if r.direction > 0 else (win["high"] >= limit)
        if touched.any():
            fill_mod = int(win.loc[touched.idxmax(), "mod"])
            net = r.direction * (r.exit_px - limit) - COST_LIMIT
            rows.append(dict(date=r.date, candidate=r.candidate, direction=r.direction, offset=offset, atr=atr,
                             filled=1, fill_mod=fill_mod, limit=limit, net_pts=net,
                             market_net_pts=r.direction * (r.exit_px - r.entry_px) - COST_MARKET))
        else:
            rows.append(dict(date=r.date, candidate=r.candidate, direction=r.direction, offset=offset, atr=atr,
                             filled=0, fill_mod=np.nan, limit=limit, net_pts=0.0,
                             market_net_pts=r.direction * (r.exit_px - r.entry_px) - COST_MARKET))
    return pd.DataFrame(rows)


def evaluate(frame, trades, offsets=OFFSETS):
    """Summary per candidate × offset, plus the market row; improvement = limit − market per signal."""
    out = []
    for name, t in trades.groupby("candidate"):
        m_net = (t["direction"] * (t["exit_px"] - t["entry_px"]) - COST_MARKET).to_numpy()
        out.append(dict(candidate=name, entry="market", fill_rate=1.0, n_signals=len(t), mean_net_per_signal=m_net.mean(),
                        mean_net_if_filled=m_net.mean(), improvement=0.0, p_improvement=np.nan,
                        p_boot_day=stats.one_sided_p(m_net, stats.day_blocks(t["date"]))))
        for off in offsets:
            f = limit_fills(frame, t, off)
            if f.empty:
                continue
            diff = (f["net_pts"] - f["market_net_pts"]).to_numpy()
            out.append(dict(candidate=name, entry=f"limit -{off:.2f} ATR", fill_rate=f["filled"].mean(), n_signals=len(f),
                            mean_net_per_signal=f["net_pts"].mean(),
                            mean_net_if_filled=f.loc[f["filled"] == 1, "net_pts"].mean() if f["filled"].any() else np.nan,
                            improvement=diff.mean(), p_improvement=stats.one_sided_p(diff, stats.day_blocks(f["date"])),
                            p_boot_day=stats.one_sided_p(f["net_pts"].to_numpy(), stats.day_blocks(f["date"]))))
    return pd.DataFrame(out)
