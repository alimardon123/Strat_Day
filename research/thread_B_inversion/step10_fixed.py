"""Step 10 — the same time-zone test, with observability enforced.

THE BUG (step 9): to capture the DAX overnight gap for date D you must be positioned at
the DAX close on D-1, which is 08:32 ET on D-1. The US session on D-1 does not open
until 09:32 ET. So the signal was not merely unavailable — the US session it used sits
entirely INSIDE the DAX overnight window being predicted. Sharpe 7.2 was the US session
being counted as both cause and effect.

THE FIX: every signal must be fully closed before the position is opened. Enforced here
by an explicit clock check rather than a shift() the reader has to trust.
"""
import numpy as np
import pandas as pd
from stats_engine import block_bootstrap_p
from step9_axes import daily_frame, COST_PCT

# session clocks in ET, from detect_open
CLOCK = {"SPX": (9 * 60 + 32, 16 * 60 + 2), "DAX": (2 * 60 + 2, 8 * 60 + 32),
         "STOXX": (2 * 60 + 2, 8 * 60 + 32)}
MIN_IN_DAY = 24 * 60


def observable(sig_end_day, sig_end_mod, pos_open_day, pos_open_mod):
    """True if the signal window closes strictly before the position opens."""
    return (sig_end_day * MIN_IN_DAY + sig_end_mod) < (pos_open_day * MIN_IN_DAY + pos_open_mod)


def run(eu):
    spx, e = daily_frame("data/spx_*.csv"), daily_frame(
        "data/GRXEUR_*.csv" if eu == "DAX" else "data/ETXEUR_*.csv")
    idx = e.index.intersection(spx.index)
    e, spx = e.loc[idx], spx.loc[idx]
    _, spx_end = CLOCK["SPX"]
    eu_open, eu_close = CLOCK[eu]
    out = []

    for lag, target, pos_open_mod, pos_open_off in [
            (1, "overnight", eu_close, -1),   # gap trade: enter at EU close on D-1
            (2, "overnight", eu_close, -1),
            (1, "intraday", eu_open, 0),      # session trade: enter at EU open on D
            (2, "intraday", eu_open, 0)]:
        # signal = SPX session on day D-lag, closing at spx_end
        ok = observable(-lag, spx_end, pos_open_off, pos_open_mod)
        sig = np.sign(spx["intraday"].shift(lag))
        r = (sig * e[target]).dropna()
        if len(r) < 200:
            continue
        cost = 100 * COST_PCT[eu]
        net = r.to_numpy() - cost
        p = block_bootstrap_p(r.to_numpy(), r.index.to_numpy(), n_boot=2000)
        out.append(dict(market=eu, target=target, lag=lag, executable=ok, n=len(r),
                        mean=r.mean(), net_mean=net.mean(),
                        net_sr=net.mean() / net.std() * np.sqrt(252), p=p))
    return out


if __name__ == "__main__":
    rows = run("DAX") + run("STOXX")
    print("TIME-ZONE SPILLOVER, OBSERVABILITY ENFORCED")
    print("'executable' = signal window closes before the position is opened\n")
    print(f"{'market':>7} {'target':>10} {'lag':>4} {'exec':>6} {'n':>6} {'mean%':>9} "
          f"{'net%':>9} {'net SR':>8} {'boot p':>9}")
    for r in rows:
        flag = "OK" if r["executable"] else "LOOKAHEAD"
        print(f"{r['market']:>7} {r['target']:>10} {r['lag']:>4} {flag:>9} {r['n']:>6} "
              f"{r['mean']:>+9.4f} {r['net_mean']:>+9.4f} {r['net_sr']:>+8.2f} {r['p']:>9.5f}")

    good = [r for r in rows if r["executable"] and r["net_mean"] > 0 and r["p"] < 0.05 / len(rows)]
    print(f"\nexecutable AND profitable after cost AND Bonferroni-significant: {len(good)}")
    for r in good:
        print(f"   {r['market']} {r['target']} lag{r['lag']}: net {r['net_mean']:+.4f}%/day SR {r['net_sr']:+.2f}")
