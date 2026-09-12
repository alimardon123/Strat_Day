"""Step 3 — does price CONTINUE after a stop-out, beyond what the session baseline gives?

For every stopped-out trade we ask two questions:
  1. Excursion: over the next N minutes, how far does price run in the continuation
     direction (MFE) vs against it (MAE), measured in ATR units?
  2. Tradeable: if we entered AT the stop price in the continuation direction with a
     bracket, what is the expectancy after costs?

Both are compared against a matched control: same session, same direction, same ATR,
a random bar >=30 minutes away. That controls for volatility, drift and time of day.
"""
import numpy as np
import pandas as pd
from loader import load
from engine2 import to_5m, atr, Path, run_trades, stats, report
from step1_baseline import build_signals, make_entries, COST_PTS

RNG = np.random.default_rng(7)
N_CONTROL = 5
HORIZONS = [15, 30, 60, 120]


def excursion(p, start, direction, horizon):
    """MFE/MAE in points from the close at `start`, within the session."""
    s0, ref = p.sess[start], p.close[start]
    end = min(start + horizon, p.n - 1)
    stop_i = end
    for i in range(start + 1, end + 1):
        if p.sess[i] != s0:
            stop_i = i - 1
            break
    if stop_i <= start:
        return np.nan, np.nan
    hi = p.high[start + 1:stop_i + 1].max()
    lo = p.low[start + 1:stop_i + 1].min()
    if direction > 0:
        return hi - ref, ref - lo
    return ref - lo, hi - ref


def session_bounds(p):
    """First/last path index of each session."""
    b = {}
    for i, s in enumerate(p.sess):
        if s not in b:
            b[s] = [i, i]
        b[s][1] = i
    return b


def control_index(p, bounds, j, rng, min_gap=30):
    lo, hi = bounds[p.sess[j]]
    span = [i for i in (lo, hi) if abs(i - j) >= min_gap]
    if hi - lo < 2 * min_gap:
        return None
    for _ in range(20):
        c = rng.integers(lo, hi + 1)
        if abs(c - j) >= min_gap:
            return int(c)
    return None


if __name__ == "__main__":
    m1 = load()
    b = to_5m(m1)
    b["atr"] = atr(b)
    b = build_signals(b)
    p = Path(m1)
    idx = {t: i for i, t in enumerate(m1["ts"])}
    entries = make_entries(b, idx)
    base = pd.read_pickle("baseline_trades.pkl")
    bounds = session_bounds(p)

    stopped = base[base["reason"] == "stop"].copy()
    stopped["stop_idx"] = stopped["path_idx"] + stopped["bars_held"]
    stopped = stopped[stopped["stop_idx"] < p.n - 130]
    print(f"stopped-out trades usable: {len(stopped)}\n")

    # ---------- 1. excursion study ----------
    rows = []
    for r in stopped.itertuples():
        d = -r.direction                     # continuation of the adverse move
        j = int(r.stop_idx)
        for h in HORIZONS:
            mfe, mae = excursion(p, j, d, h)
            rows.append(dict(kind="sweep", h=h, mfe=mfe / r.atr, mae=mae / r.atr))
        for _ in range(N_CONTROL):
            c = control_index(p, bounds, j, RNG)
            if c is None:
                continue
            for h in HORIZONS:
                mfe, mae = excursion(p, c, d, h)
                rows.append(dict(kind="control", h=h, mfe=mfe / r.atr, mae=mae / r.atr))

    ex = pd.DataFrame(rows).dropna()
    print("EXCURSION AFTER STOP-OUT vs MATCHED CONTROL (units of 5m ATR)")
    print(f"{'horiz':>6} {'set':>8} {'n':>7} {'medMFE':>8} {'medMAE':>8} {'meanMFE':>8} {'meanMAE':>8} {'MFE-MAE':>8}")
    for h in HORIZONS:
        for k in ["sweep", "control"]:
            g = ex[(ex["h"] == h) & (ex["kind"] == k)]
            print(f"{h:>6} {k:>8} {len(g):>7} {g['mfe'].median():>8.3f} {g['mae'].median():>8.3f}"
                  f" {g['mfe'].mean():>8.3f} {g['mae'].mean():>8.3f} {g['mfe'].mean()-g['mae'].mean():>8.3f}")
        s = ex[(ex["h"] == h) & (ex["kind"] == "sweep")]
        c = ex[(ex["h"] == h) & (ex["kind"] == "control")]
        edge = (s["mfe"] - s["mae"]).mean() - (c["mfe"] - c["mae"]).mean()
        se = np.sqrt((s["mfe"] - s["mae"]).var() / len(s) + (c["mfe"] - c["mae"]).var() / len(c))
        print(f"       -> sweep advantage {edge:+.4f} ATR   t = {edge/se:+.2f}\n")

    # ---------- 2. tradeable version ----------
    print("\nSWEEP ENTRY AS AN ACTUAL TRADE (enter at the stop price, continuation dir)")
    for sa, ta in [(1.0, 2.0), (1.5, 3.0), (1.0, 1.0), (2.0, 2.0)]:
        ents, ctrls = [], []
        for r in stopped.itertuples():
            d = -r.direction
            j = int(r.stop_idx)
            px = p.close[j]
            ents.append(dict(path_idx=j + 1, direction=d, entry=px, atr=r.atr,
                             stop=px - d * sa * r.atr, target=px + d * ta * r.atr))
            c = control_index(p, bounds, j, RNG)
            if c is not None and c + 1 < p.n:
                cp = p.close[c]
                ctrls.append(dict(path_idx=c + 1, direction=d, entry=cp, atr=r.atr,
                                  stop=cp - d * sa * r.atr, target=cp + d * ta * r.atr))
        t = run_trades(ents, p, COST_PTS)
        tc = run_trades(ctrls, p, COST_PTS)
        s, sc = stats(t), stats(tc)
        print(f"\n  stop {sa}ATR / target {ta}ATR")
        print(f"    sweep   : n={s['trades']:5d} win {s['win_pct']:5.1f}%  exp {s['exp_R']:+.4f}R  t {s['t']:+5.2f}  PF {s['pf']:.2f}")
        print(f"    control : n={sc['trades']:5d} win {sc['win_pct']:5.1f}%  exp {sc['exp_R']:+.4f}R  t {sc['t']:+5.2f}  PF {sc['pf']:.2f}")
        z = run_trades(ents, p, 0.0)
        print(f"    sweep @ zero cost:            exp {stats(z)['exp_R']:+.4f}R  t {stats(z)['t']:+5.2f}")
