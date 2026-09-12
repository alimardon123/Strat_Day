"""Step 4 — conditional polarity.

The signal has zero UNCONDITIONAL edge. Does it have edge inside a regime?
If some bucket is reliably negative, that is where inversion is justified.

Discipline: buckets are chosen on 2013-2016 only, then applied untouched to 2017-2018.
"""
import numpy as np
import pandas as pd
from loader import load
from engine2 import to_5m, atr, Path, run_trades, stats
from step1_baseline import build_signals, make_entries, COST_PTS

TRAIN_END = pd.Timestamp("2017-01-01")


def regimes(b):
    c = b["close"]
    delta = c.diff().abs()
    b["er"] = (c - c.shift(20)).abs() / delta.rolling(20).sum()     # efficiency ratio
    b["atr_ratio"] = b["atr"] / b["atr"].rolling(100).mean()
    b["day_pos"] = (c - c.groupby(b["session"]).transform("first")) / b["atr"]
    return b


def bucket_table(t, col, edges, labels):
    t = t.copy()
    t["bucket"] = pd.cut(t[col], edges, labels=labels)
    rows = []
    for name, g in t.groupby("bucket", observed=True):
        tr = g[g["ts"] < TRAIN_END]
        te = g[g["ts"] >= TRAIN_END]
        if len(tr) < 80 or len(te) < 40:
            continue
        st, se = stats(tr), stats(te)
        rows.append(dict(bucket=name, n_tr=st["trades"], exp_tr=st["exp_R"], t_tr=st["t"],
                         n_te=se["trades"], exp_te=se["exp_R"], t_te=se["t"]))
    return pd.DataFrame(rows)


if __name__ == "__main__":
    m1 = load()
    b = to_5m(m1)
    b["atr"] = atr(b)
    b = regimes(build_signals(b))
    p = Path(m1)
    idx = {t: i for i, t in enumerate(m1["ts"])}
    entries = make_entries(b, idx)

    # attach regime features to each trade
    feats = b.set_index("ts")[["er", "atr_ratio", "day_pos", "minute_of_day"]]
    t = run_trades(entries, p, COST_PTS)
    t = t.join(feats, on="ts")
    t_gross = t.assign(R=t["gross_pts"] / t["risk_pts"])   # cost-free view isolates signal info

    print("Trades:", len(t), "| train", (t['ts'] < TRAIN_END).sum(), "| test", (t['ts'] >= TRAIN_END).sum())
    print("\nGROSS (zero-cost) expectancy by regime bucket — is the SIGNAL informative at all?")
    print("Positive => trade with it. Negative => inversion candidate. Need BOTH train and test to agree.\n")

    specs = [
        ("er", [0, .15, .25, .40, 1.01], ["chop", "weak", "mod", "trend"]),
        ("atr_ratio", [0, .8, 1.1, 1.5, 99], ["quiet", "normal", "active", "wild"]),
        ("minute_of_day", [569, 600, 720, 840, 961], ["open30", "morning", "midday", "close"]),
        ("day_pos", [-99, -2, 0, 2, 99], ["far_below", "below", "above", "far_above"]),
    ]
    for col, edges, labels in specs:
        tb = bucket_table(t_gross, col, edges, labels)
        if tb.empty:
            continue
        print(f"--- {col} ---")
        print(f"{'bucket':>10} {'n_tr':>6} {'exp_tr':>9} {'t_tr':>6} | {'n_te':>6} {'exp_te':>9} {'t_te':>6}  agree?")
        for r in tb.itertuples():
            agree = "YES" if np.sign(r.exp_tr) == np.sign(r.exp_te) and abs(r.t_tr) > 1.5 else ""
            print(f"{str(r.bucket):>10} {r.n_tr:>6} {r.exp_tr:>+9.4f} {r.t_tr:>+6.2f} |"
                  f" {r.n_te:>6} {r.exp_te:>+9.4f} {r.t_te:>+6.2f}   {agree}")
        print()

    # 2-D: the interaction people actually expect (trend strength x direction)
    print("--- efficiency ratio x direction (gross) ---")
    t2 = t_gross.copy()
    t2["er_b"] = pd.cut(t2["er"], [0, .2, .35, 1.01], labels=["chop", "mid", "trend"])
    print(f"{'er':>8} {'dir':>6} {'n_tr':>6} {'exp_tr':>9} {'t_tr':>6} | {'n_te':>6} {'exp_te':>9} {'t_te':>6}")
    for (eb, d), g in t2.groupby(["er_b", "direction"], observed=True):
        tr, te = g[g["ts"] < TRAIN_END], g[g["ts"] >= TRAIN_END]
        if len(tr) < 60 or len(te) < 30:
            continue
        st, se = stats(tr), stats(te)
        print(f"{str(eb):>8} {'long' if d>0 else 'short':>6} {st['trades']:>6} {st['exp_R']:>+9.4f}"
              f" {st['t']:>+6.2f} | {se['trades']:>6} {se['exp_R']:>+9.4f} {se['t']:>+6.2f}")
