"""Step 15 — does hitting your target on the SPY chart mean hitting it on the option?

The claim under test: "as long as price reaches my TP on the chart, the option reaches
its TP too."

The SPY chart has one axis: price. A 0DTE option has two: price AND time. This prices
the option minute by minute with Black-Scholes and compares the two P&Ls on identical
trades.

Underlying: SPX 1-minute (SPY is SPX/10 -- identical shape, so conclusions transfer).
Implied vol: VIX at prior close. This is GENEROUS to the option: real 0DTE IV is usually
higher than 30-day VIX, which means more theta than modelled here.
"""
import numpy as np
import pandas as pd
from math import log, sqrt, exp, erf
from loader import load
from engine2 import to_5m, atr

CLOSE_MIN = 16 * 60          # options expire at the close
RNG = np.random.default_rng(3)


def ncdf(x):
    return 0.5 * (1.0 + erf(x / sqrt(2.0)))


def bs_call(S, K, T, sigma, r=0.0):
    """T in years. Returns (price, delta)."""
    if T <= 1e-9 or sigma <= 0:
        return max(S - K, 0.0), (1.0 if S > K else 0.0)
    d1 = (log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * sqrt(T))
    d2 = d1 - sigma * sqrt(T)
    return S * ncdf(d1) - K * exp(-r * T) * ncdf(d2), ncdf(d1)


def bs_put(S, K, T, sigma, r=0.0):
    if T <= 1e-9 or sigma <= 0:
        return max(K - S, 0.0), (-1.0 if S < K else 0.0)
    d1 = (log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * sqrt(T))
    d2 = d1 - sigma * sqrt(T)
    return K * exp(-r * T) * ncdf(-d2) - S * ncdf(-d1), -ncdf(-d1)


def simulate(m1, vix, tp_atr=2.0, sl_atr=1.5, n_trades=4000, opt_cost=0.01):
    """Random entries (we are testing the INSTRUMENT, not a signal).
    Exit on the UNDERLYING hitting tp/sl, then see what the option did."""
    b5 = to_5m(m1)
    b5["atr"] = atr(b5)
    b5 = b5.dropna().reset_index(drop=True)

    S = m1["close"].to_numpy(float)
    H = m1["high"].to_numpy(float)
    L = m1["low"].to_numpy(float)
    mod = m1["minute_of_day"].to_numpy(int)
    sess = pd.factorize(m1["session"])[0]
    dates = pd.Series(m1["session"].to_numpy())
    vmap = dict(zip(vix.index, vix["CLOSE"]))

    idx = np.flatnonzero((mod >= 585) & (mod <= 870))    # 09:45 - 14:30 entries
    picks = RNG.choice(idx, size=min(n_trades, len(idx)), replace=False)
    a5 = dict(zip(b5["ts"], b5["atr"]))
    med_atr = b5["atr"].median()

    rows = []
    for i in picks:
        d = dates.iat[i]
        iv = vmap.get(d)
        if iv is None:
            continue
        sigma = iv / 100.0
        a = med_atr
        entry = S[i]
        K = round(entry / 5.0) * 5.0                      # nearest 5-point strike, ~ATM
        tp, sl = entry + tp_atr * a, entry - sl_atr * a
        T0 = max((CLOSE_MIN - mod[i]) / (60 * 24 * 365.0), 1e-9)
        p0, delta0 = bs_call(entry, K, T0, sigma)
        if p0 < 0.05:
            continue

        exit_i, why = None, None
        for j in range(i + 1, len(S)):
            if sess[j] != sess[i] or mod[j] >= CLOSE_MIN - 5:
                exit_i, why = j, "flat"
                break
            if H[j] >= tp:
                exit_i, why = j, "tp"
                break
            if L[j] <= sl:
                exit_i, why = j, "sl"
                break
        if exit_i is None:
            continue

        T1 = max((CLOSE_MIN - mod[exit_i]) / (60 * 24 * 365.0), 1e-9)
        p1, _ = bs_call(S[exit_i], K, T1, sigma)
        und_pts = S[exit_i] - entry
        opt_ret = (p1 * (1 - opt_cost) - p0 * (1 + opt_cost)) / p0
        rows.append(dict(why=why, mins=exit_i - i, und_R=und_pts / (sl_atr * a),
                         opt_ret=opt_ret, prem=p0, delta=delta0, iv=iv,
                         und_pts=und_pts, theta_mins=exit_i - i))
    return pd.DataFrame(rows)


if __name__ == "__main__":
    m1 = load()
    vix = pd.read_csv("data/vix.csv", parse_dates=["DATE"]).set_index("DATE")
    vix.index = vix.index.date
    t = simulate(m1, vix)
    t.to_pickle("odte.pkl")
    print(f"simulated trades: {len(t)}   (ATM 0DTE calls, 1% round-trip option cost)\n")

    print("=" * 82)
    print("THE CLAIM: 'if the underlying hits my TP, the option hits its TP'")
    print("=" * 82)
    tp = t[t["why"] == "tp"]
    print(f"trades where the UNDERLYING hit target: {len(tp)}")
    print(f"  of those, the OPTION still lost money: {100*(tp['opt_ret']<0).mean():.1f}%")
    print(f"  median option return on a WINNING underlying trade: {100*tp['opt_ret'].median():+.1f}%")
    print(f"  worst option return on a WINNING underlying trade:  {100*tp['opt_ret'].min():+.1f}%\n")

    print("  broken down by how long the winning trade took:")
    tp2 = tp.copy()
    tp2["bucket"] = pd.cut(tp2["mins"], [0, 15, 30, 60, 120, 10000],
                           labels=["<15m", "15-30m", "30-60m", "1-2h", ">2h"])
    print(f"  {'time to TP':>12} {'n':>6} {'median opt%':>13} {'opt lost money':>16}")
    for nm, g in tp2.groupby("bucket", observed=True):
        print(f"  {str(nm):>12} {len(g):>6} {100*g['opt_ret'].median():>+12.1f}% "
              f"{100*(g['opt_ret']<0).mean():>15.1f}%")

    print("\n" + "=" * 82)
    print("OVERALL — same trades, two instruments")
    print("=" * 82)
    print(f"{'':>22} {'underlying':>14} {'0DTE option':>14}")
    print(f"{'win rate':>22} {100*(t['und_R']>0).mean():>13.1f}% {100*(t['opt_ret']>0).mean():>13.1f}%")
    print(f"{'mean outcome':>22} {t['und_R'].mean():>+13.3f}R {100*t['opt_ret'].mean():>+13.1f}%")
    print(f"{'median outcome':>22} {t['und_R'].median():>+13.3f}R {100*t['opt_ret'].median():>+13.1f}%")
    print(f"\naverage delta at entry: {t['delta'].mean():.3f}  "
          f"-> the option captures ~{100*t['delta'].mean():.0f}% of each point SPY moves")
    print(f"average premium: {t['prem'].mean():.2f} index pts")

    print("\n" + "=" * 82)
    print("WHY — the second axis")
    print("=" * 82)
    flat = t[t["why"] == "flat"]
    print(f"trades that expired without hitting tp or sl: {len(flat)} ({100*len(flat)/len(t):.0f}%)")
    print(f"  median underlying move on those: {flat['und_pts'].median():+.2f} pts (roughly nothing)")
    print(f"  median OPTION return on those:   {100*flat['opt_ret'].median():+.1f}%")
    print("\n  The underlying went nowhere. The option was destroyed by time.")
