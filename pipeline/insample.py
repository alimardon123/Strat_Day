"""D3 and D4 on the two pre-registered signals over a window (COUPLED — single owner).

Usage: python -m pipeline.insample <start> <end> <label> [out_prefix]
The D4 headline is the holdout run; any other window is labelled IN-SAMPLE. The pre-registered
signals are read from out/reconcile_decision.md's winner (or given explicitly) plus Thread A's
gap-up call.
"""
import re
import sys

import pandas as pd

from pipeline import execution, playbook, sessions, signals


def winner_from_decision(path="out/reconcile_decision.md"):
    txt = open(path).read()
    m = re.search(r"Winner: \*\*(.+?)\*\*", txt)
    return m.group(1) if m else None


def parse_label(lbl):
    hm, direction, gate = lbl.split("|")
    h, mi = hm.split(":")
    return int(h) * 60 + int(mi), direction, gate


def main(start, end, label, out_prefix="out/playbook", winner=None):
    vix = pd.read_parquet("data/raw/vix_daily.parquet")
    frame, _ = sessions.build("oanda", "data/raw/oanda_SPX500_USD.parquet", sessions.trading_days_from_vix())
    day = signals.day_table(frame, vix)
    fixed = {e: signals.fixed_thresholds(day, e) for e in (900, 930)}
    winner = winner or winner_from_decision()
    e, d, g = parse_label(winner)
    win_trades = signals.candidate(day, e, d, g, fixed=fixed.get(e), name=winner)
    gap = signals.gap_up_call(day)
    sel = {winner: win_trades, "13:00|call|gap>0.3%": gap}
    sel = {k: v[(v["date"] >= start) & (v["date"] <= end)].reset_index(drop=True) for k, v in sel.items()}
    fr = frame[(frame["date"] >= start) & (frame["date"] <= end)]
    print(f"window {start}..{end} ({label}): " + ", ".join(f"{k}: {len(v)} trades" for k, v in sel.items()))
    ex = execution.evaluate(fr, pd.concat(sel.values(), ignore_index=True))
    ex.insert(0, "window", label)
    print("\nD3 execution model (underlying points per signal, net):")
    print(ex.to_string(index=False, float_format=lambda x: f"{x:.4f}"))
    ex.to_csv(f"{out_prefix}_execution.csv", index=False, float_format="%.6f")
    summary, sz = playbook.build(fr, day.loc[start:end], sel, label, grid="SPX", out_prefix=out_prefix)
    print("\nD4 pricing summary (% of premium):")
    cols = ["signal", "spread", "settle", "k", "n", "win", "mean", "median", "worst_trade", "worst_day", "mae_worst", "premium_mean"]
    print(summary[cols].to_string(index=False, float_format=lambda x: f"{x:.3f}"))
    print("\nD4 sizing (% of account):")
    print(sz.to_string(index=False, float_format=lambda x: f"{x:.3f}"))


if __name__ == "__main__":
    a = sys.argv[1:]
    main(a[0], a[1], a[2], a[3] if len(a) > 3 else "out/playbook")
