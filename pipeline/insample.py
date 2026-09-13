"""D2/D3/D4 on the two pre-registered signals over a window (COUPLED — single owner).

Usage: python -m pipeline.insample <start> <end> <label> [out_prefix]
A window starting 2020-06-01 or later is the HOLDOUT (D2): per-year rows, pooled and two-half
p-values with month blocks, both controls, and the survival-rule verdict per signal. Any other
window is labelled IN-SAMPLE. The pre-registered winner is read from out/reconcile_decision.md.
"""
import re
import sys

import numpy as np
import pandas as pd

from pipeline import execution, playbook, sessions, signals, stats

COST_PTS = 1.0
HOLDOUT_START = pd.Timestamp("2020-06-01")


def winner_from_decision(path="out/reconcile_decision.md"):
    m = re.search(r"Winner: \*\*(.+?)\*\*", open(path).read())
    return m.group(1) if m else None


def parse_label(lbl):
    hm, direction, gate = lbl.split("|")
    h, mi = hm.split(":")
    return int(h) * 60 + int(mi), direction, gate


def holdout_tables(sel, day, frame, td, start, end, out_prefix):
    """D2: per-year rows, pooled + halves, controls, survival-rule verdict per signal."""
    rows, years = [], []
    mid = pd.Timestamp(start) + (pd.Timestamp(end) - pd.Timestamp(start)) / 2
    for name, t in sel.items():
        if t.empty:
            rows.append(dict(signal=name, n=0, label="NO TRADES"))
            continue
        net_pct = t["ret_pct"] - 100 * COST_PTS / t["entry_px"]
        net_pts = t["pts"] - COST_PTS
        e, d, g = (parse_label(name) if "gap" not in name else (780, "both", "gap"))
        base = "prev_close" if g != "mag" else "open"
        ctrl = signals.day_selection_control(day.loc[start:end], t, e, d if g != "gap" else "both", base=base)
        ctrl_net = ctrl - 100 * COST_PTS / t["entry_px"].mean()
        excess = net_pct.mean() - ctrl_net.mean() if len(ctrl) else np.nan
        p_month = stats.one_sided_p(net_pct.to_numpy(), stats.month_blocks(t["date"]))
        h1, h2 = t[t["date"] < mid], t[t["date"] >= mid]
        psr = stats.deflated_sharpe(net_pct.to_numpy(), n=1)[0]
        conds = dict(net_positive=bool(net_pts.mean() > 0), p_month_lt_005=bool(p_month < 0.05) if p_month == p_month else False,
                     excess_over_control=bool(excess > 0) if excess == excess else False, psr_gt_095=bool(psr > 0.95) if psr == psr else False,
                     n_ge_200=bool(len(t) >= 200))
        # survival rule 3 (family-wide BH-FDR) is applied afterwards by pipeline/trials.py, which finalises the label
        label = "SURVIVES (pending FDR)" if all(conds.values()) else ("UNDERPOWERED" if not conds["n_ge_200"] and conds["net_positive"] else "FAILED")
        rows.append(dict(signal=name, n=len(t), win=100 * (t["pts"] > 0).mean(), net_pts=net_pts.mean(), net_pct=net_pct.mean(),
                         worst_trade_pts=net_pts.min(), p_month=p_month, p_day=stats.one_sided_p(net_pct.to_numpy(), stats.day_blocks(t["date"])),
                         p_half1_month=stats.one_sided_p((h1["ret_pct"] - 100 * COST_PTS / h1["entry_px"]).to_numpy(), stats.month_blocks(h1["date"])) if len(h1) else np.nan,
                         p_half2_month=stats.one_sided_p((h2["ret_pct"] - 100 * COST_PTS / h2["entry_px"]).to_numpy(), stats.month_blocks(h2["date"])) if len(h2) else np.nan,
                         control_mean_pct=ctrl_net.mean() if len(ctrl) else np.nan, excess_over_control_pct=excess,
                         psr=psr, sharpe_calday=stats.calendar_day_sharpe(net_pct.to_numpy(), t["date"], [x for x in td if pd.Timestamp(start) <= x <= pd.Timestamp(end)]),
                         **conds, label=label, note="FDR across the family is in out/trials.csv"))
        for y, g_ in t.groupby(pd.to_datetime(t["date"]).dt.year):
            npct = g_["ret_pct"] - 100 * COST_PTS / g_["entry_px"]
            years.append(dict(signal=name, year=int(y), n=len(g_), win=100 * (g_["pts"] > 0).mean(), net_pts=(g_["pts"] - COST_PTS).mean(),
                              net_pct=npct.mean(), worst_trade_pts=(g_["pts"] - COST_PTS).min(),
                              p_day=stats.one_sided_p(npct.to_numpy(), stats.day_blocks(g_["date"]))))
    summ = pd.DataFrame(rows)
    summ.to_csv(f"{out_prefix}_summary.csv", index=False, float_format="%.6f")
    summ.to_csv(f"{out_prefix}_pooled.csv", index=False, float_format="%.6f")          # ACCEPTANCE D2's named evidence file
    pd.DataFrame(years).to_csv(f"{out_prefix}_by_year.csv", index=False, float_format="%.6f")
    print("\nD2 holdout verdicts:")
    print(pd.DataFrame(rows).to_string(index=False, float_format=lambda x: f"{x:.4f}"))


def main(start, end, label, out_prefix="out/playbook", winner=None):
    vix = pd.read_parquet("data/raw/vix_daily.parquet")
    td = sessions.trading_days_from_vix()
    frame, _, meta = sessions.build_extended(trading_days=td)
    day = signals.day_table(frame, vix, dividends=meta["dividends"] if meta else None, trading_days=td,
                            roll_dates=meta["roll_dates"] if meta else ())
    fixed = {e: signals.fixed_thresholds(day, e) for e in (900, 930)}
    winner = winner or winner_from_decision()
    e, d, g = parse_label(winner)
    win_trades = signals.candidate(day, e, d, g, fixed=fixed.get(e), name=winner)
    gap = signals.gap_up_call(day)
    sel = {winner: win_trades, "13:00|call|gap>0.3%": gap}
    sel = {k: v[(v["date"] >= start) & (v["date"] <= end)].reset_index(drop=True) for k, v in sel.items()}
    fr = frame[(frame["date"] >= start) & (frame["date"] <= end)]
    is_holdout = pd.Timestamp(start) >= HOLDOUT_START
    print(f"window {start}..{end} ({label}; {'HOLDOUT' if is_holdout else 'IN-SAMPLE'}; ext feed: {meta['instrument'] if meta else 'absent'}): "
          + ", ".join(f"{k}: {len(v)} trades" for k, v in sel.items()))
    if is_holdout:
        holdout_tables(sel, day, frame, td, start, end, "out/holdout")     # D2 tables: fixed names (out/holdout_summary|by_year|pooled.csv)
        out_prefix = "out/holdout_d4"                                        # D3/D4 tables for the holdout window
    ex = execution.evaluate(fr, pd.concat(sel.values(), ignore_index=True))
    ex.insert(0, "window", label)
    print("\nD3 execution model (underlying points per signal, net; improvement split into cost assumption and price effect):")
    print(ex.to_string(index=False, float_format=lambda x: f"{x:.4f}"))
    ex.to_csv(f"{out_prefix}_execution.csv", index=False, float_format="%.6f")
    grid = "SPX"
    summary, sz = playbook.build(fr, day.loc[start:end], sel, label, grid=grid, out_prefix=out_prefix)
    print("\nD4 pricing summary (% of premium):")
    cols = ["signal", "spread", "settle", "k", "n", "win", "mean", "median", "worst_trade", "worst_day", "mae_worst", "full_loss_trades", "premium_mean"]
    print(summary[cols].to_string(index=False, float_format=lambda x: f"{x:.3f}"))
    print("\nD4 sizing (% of account):")
    print(sz.to_string(index=False, float_format=lambda x: f"{x:.3f}"))


if __name__ == "__main__":
    a = sys.argv[1:]
    main(a[0], a[1], a[2], a[3] if len(a) > 3 else "out/playbook")
