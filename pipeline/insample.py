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

from pipeline import execution, options, playbook, sessions, signals, stats

COST_PTS = 1.0
HOLDOUT_START = pd.Timestamp("2020-06-01")
HOLDOUT_HALF = pd.Timestamp("2023-07-01")   # ACCEPTANCE D2's two named halves (2020-06->2023-06 / 2023-07->2026-09),
                                             # not the arithmetic midpoint of the window passed in


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
    frame_window = frame[(frame["date"] >= start) & (frame["date"] <= end)]
    data_first = frame_window["date"].min() if len(frame_window) else pd.NaT
    data_last = frame_window["date"].max() if len(frame_window) else pd.NaT
    data_first_date = data_first.strftime("%Y-%m-%d") if pd.notna(data_first) else None
    data_last_date = data_last.strftime("%Y-%m-%d") if pd.notna(data_last) else None
    sessions_in_window = int(frame_window["date"].nunique())
    # honesty check: the ext feed can start well after `start` (e.g. the Oanda->ext gap, DATA.md);
    # 5 trading days tolerates ordinary warm-up/reporting lag without flagging every holdout run
    start_ts = pd.Timestamp(start)
    gap_note = None
    if pd.notna(data_first) and data_first > start_ts:
        n_gap_td = sum(1 for x in td if start_ts <= x < data_first)
        if n_gap_td > 5:
            gap_note = f"data starts {data_first_date}"
    for name, t in sel.items():
        if t.empty:
            r = dict(signal=name, n=0, label="NO TRADES", data_first_date=data_first_date,
                     data_last_date=data_last_date, sessions_in_window=sessions_in_window)
            if gap_note:
                r["note"] = gap_note
            rows.append(r)
            continue
        net_pct = t["ret_pct"] - 100 * COST_PTS / t["entry_px"]
        net_pts = t["pts"] - COST_PTS
        e, d, g = (parse_label(name) if "gap" not in name else (780, "both", "gap"))
        base = "prev_close" if g != "mag" else "open"
        ctrl = signals.day_selection_control(day.loc[start:end], t, e, d if g != "gap" else "both", base=base)
        ctrl_net = ctrl - 100 * COST_PTS / t["entry_px"].mean()
        excess = net_pct.mean() - ctrl_net.mean() if len(ctrl) else np.nan
        p_month = stats.one_sided_p(net_pct.to_numpy(), stats.month_blocks(t["date"]))
        h1, h2 = t[t["date"] < HOLDOUT_HALF], t[t["date"] >= HOLDOUT_HALF]
        psr = stats.deflated_sharpe(net_pct.to_numpy(), n=1)[0]
        # A16 timing control (reported only, survival rule 4): same call convention as reconcile.py::window_stats
        tim = signals.timing_control(frame_window, t, n_seeds=50)
        timing_control_pct = np.nanmean(tim) - 100 * COST_PTS / t["entry_px"].mean()
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
                         timing_control_pct=timing_control_pct,
                         psr=psr, sharpe_calday=stats.calendar_day_sharpe(net_pct.to_numpy(), t["date"], [x for x in td if pd.Timestamp(start) <= x <= pd.Timestamp(end)]),
                         **conds, label=label,
                         note="FDR across the family is in out/trials.csv" + (f"; {gap_note}" if gap_note else ""),
                         data_first_date=data_first_date, data_last_date=data_last_date, sessions_in_window=sessions_in_window))
        for y, g_ in t.groupby(pd.to_datetime(t["date"]).dt.year):
            npct = g_["ret_pct"] - 100 * COST_PTS / g_["entry_px"]
            net_pts_y = g_["pts"] - COST_PTS
            year_days = frame_window.loc[pd.to_datetime(frame_window["date"]).dt.year == y, "date"]
            y_first_date = year_days.min().strftime("%Y-%m-%d") if len(year_days) else None
            y_last_date = year_days.max().strftime("%Y-%m-%d") if len(year_days) else None
            # D4 pricing conventions (playbook.build): settle="cash", grid SPX, k=1.0 for the 15:00/15:30 legs,
            # k=1.3 for the 13:00 gap-up leg (A7); % of premium mean at each quoted spread, and mae_worst at spread 1.0
            k = 1.3 if int(g_["decision_mod"].iloc[0]) == 780 else 1.0
            t_y = g_.copy()
            t_y["mae_pts"] = playbook.mae(frame, t_y)
            opt_means, mae_worst_pct = {}, np.nan
            for spread in playbook.SPREADS:
                o = playbook.price_table(t_y, spread, "cash", k, options.GRID["SPX"])
                if o.empty:
                    opt_means[spread] = np.nan
                    continue
                o["mae_pts"] = t_y.set_index("date").loc[o["date"], "mae_pts"].to_numpy()
                s = playbook.summarise(o, years_span=1.0)   # years_span only feeds trades_per_year, unused here
                opt_means[spread] = s["mean"]
                if spread == 1.0:
                    mae_worst_pct = s["mae_worst"]
            years.append(dict(signal=name, year=int(y), n=len(g_), win=100 * (g_["pts"] > 0).mean(), net_pts=net_pts_y.mean(),
                              net_pct=npct.mean(), worst_trade_pts=net_pts_y.min(),
                              p_day=stats.one_sided_p(npct.to_numpy(), stats.day_blocks(g_["date"])),
                              opt_mean_s1=opt_means[1.0], opt_mean_s2=opt_means[2.0], opt_mean_s3=opt_means[3.0],
                              worst_day_pts=net_pts_y.groupby(g_["date"]).sum().min(), mae_worst_pct=mae_worst_pct,
                              data_first_date=y_first_date, data_last_date=y_last_date))
    summ = pd.DataFrame(rows)
    # pandas orders columns by first appearance across `rows`; the NO-TRADES branch can introduce
    # data_first_date/data_last_date/sessions_in_window/note before the full row does, so force
    # them to the end and leave every other column's order untouched
    tail = [c for c in ("note", "data_first_date", "data_last_date", "sessions_in_window") if c in summ.columns]
    summ = summ[[c for c in summ.columns if c not in tail] + tail]
    summ.to_csv(f"{out_prefix}_summary.csv", index=False, float_format="%.6f")
    summ.to_csv(f"{out_prefix}_pooled.csv", index=False, float_format="%.6f")          # ACCEPTANCE D2's named evidence file
    pd.DataFrame(years).to_csv(f"{out_prefix}_by_year.csv", index=False, float_format="%.6f")
    print("\nD2 holdout verdicts:")
    print(summ.to_string(index=False, float_format=lambda x: f"{x:.4f}"))


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
    ext_span = (f"; ext data {meta['ext_first_date'].date()}..{meta['ext_last_date'].date()}"
                if meta and pd.notna(meta.get("ext_first_date")) else "")
    print(f"window {start}..{end} ({label}; {'HOLDOUT' if is_holdout else 'IN-SAMPLE'}; ext feed: {meta['instrument'] if meta else 'absent'}{ext_span}): "
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
