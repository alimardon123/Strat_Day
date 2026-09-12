"""Step 2 — the two things people mean by 'trade the opposite'.

A) Mirror inversion : flip direction, levels swap (old target distance becomes the stop).
B) Symmetric inversion: flip direction, keep the SAME stop/target distances.
   (B is not really an inversion — it is a new strategy firing on the same bars.)
"""
import numpy as np
import pandas as pd
from loader import load
from engine2 import to_5m, atr, Path, run_trades, report
from step1_baseline import build_signals, make_entries, COST_PTS, STOP_ATR, TARG_ATR


def invert(entries, mode):
    out = []
    for e in entries:
        d = -e["direction"]
        px, a = e["entry"], e["atr"]
        if mode == "mirror":       # levels swap with the direction
            stop_a, targ_a = TARG_ATR, STOP_ATR
        else:                      # keep original geometry
            stop_a, targ_a = STOP_ATR, TARG_ATR
        out.append({**e, "direction": d,
                    "stop": px - d * stop_a * a,
                    "target": px + d * targ_a * a})
    return out


if __name__ == "__main__":
    m1 = load()
    b = to_5m(m1)
    b["atr"] = atr(b)
    b = build_signals(b)
    p = Path(m1)
    idx = {t: i for i, t in enumerate(m1["ts"])}
    entries = make_entries(b, idx)

    base = pd.read_pickle("baseline_trades.pkl")
    print(report(base, "A0. ORIGINAL (loses)"))

    for mode, name in [("mirror", "A1. MIRROR inversion  (flip dir, swap levels)"),
                       ("symmetric", "A2. SYMMETRIC inversion (flip dir, same 1.5/3.0)")]:
        t = run_trades(invert(entries, mode), p, COST_PTS)
        print()
        print(report(t, name))
        print(report(t.assign(R=t["gross_pts"] / t["risk_pts"]), "     └─ same, zero cost"))
        t.to_pickle(f"inv_{mode}.pkl")

    # cost sensitivity: at what spread would the symmetric inversion break even?
    print("\ncost sensitivity — expectancy (R) of symmetric inversion vs round-trip cost")
    t = run_trades(invert(entries, "symmetric"), p, 0.0)
    for c in [0.0, 0.1, 0.2, 0.3, 0.5, 0.8]:
        R = (t["gross_pts"] - c) / t["risk_pts"]
        print(f"   cost {c:.2f} pts -> {R.mean():+.4f}R   (win {100*(R>0).mean():.1f}%)")
