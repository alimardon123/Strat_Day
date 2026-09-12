"""Step 8 — attack the cost wall instead of the signal.

Market entry pays the spread on every trade. A resting limit order pays much less —
but you only get filled when price comes BACK to you, which means you systematically
miss the trades that ran away immediately. That is adverse selection, and it is the
thing most retail backtests silently ignore when they assume limit fills.

So we measure both halves honestly:
   fill rate, and expected return CONDITIONAL on being filled.

Metric is per SIGNAL, not per fill, so missed trades are counted as zero rather than
quietly deleted from the sample.
"""
import glob
import numpy as np
import pandas as pd
from stats_engine import block_bootstrap_p
from step7_validate import load_symbol, detect_open, to_5m_session, signal_and_forward

COST_MARKET = 0.33      # cross the spread + commission
COST_LIMIT = 0.10       # commission only; you are providing liquidity on entry
FILL_WINDOW = 6         # 5m bars allowed for the limit to fill (30 min)
HOLD = 12               # 5m bars held (60 min)


def limit_test(b, offset_atr):
    """Place a buy limit `offset_atr` below the signal close. Returns per-signal rows."""
    close = b["close"].to_numpy(float)
    low = b["low"].to_numpy(float)
    a = b["atr"].to_numpy(float)
    sess = pd.factorize(b["session"])[0]
    sig = np.flatnonzero(b["sig"].to_numpy())
    n = len(b)
    rows = []
    for i in sig:
        limit = close[i] - offset_atr * a[i]
        fill_i = -1
        for j in range(i + 1, min(i + 1 + FILL_WINDOW, n)):
            if sess[j] != sess[i]:
                break
            if low[j] <= limit:
                fill_i = j
                break
        if fill_i < 0:
            rows.append(dict(filled=0, ret_atr=0.0, sess=b["session"].iat[i]))
            continue
        k = fill_i + HOLD
        if k >= n or sess[k] != sess[i]:
            k = np.max(np.flatnonzero(sess == sess[i]))
        gross = close[k] - limit
        rows.append(dict(filled=1, ret_atr=(gross - COST_LIMIT) / a[i], sess=b["session"].iat[i]))
    return pd.DataFrame(rows)


def market_test(b):
    sig = b[b["sig"]]
    return pd.DataFrame(dict(filled=1,
                             ret_atr=(sig["fwd"] - COST_MARKET) / sig["atr"],
                             sess=sig["session"])).reset_index(drop=True)


def run(name, pattern):
    df = load_symbol(pattern)
    b = signal_and_forward(to_5m_session(df, detect_open(df))).reset_index(drop=True)
    out = []
    m = market_test(b)
    out.append(("market", 1.00, m["ret_atr"].mean(), len(m), m))
    for off in (0.25, 0.50, 1.00):
        r = limit_test(b, off)
        fr = r["filled"].mean()
        out.append((f"limit -{off:.2f}ATR", fr, r["ret_atr"].mean(), len(r), r))

    print(f"\n{name}   (signals: {len(b[b['sig']])})")
    print(f"  {'entry':>16} {'fill%':>7} {'E[r] per signal':>17} {'E[r] | filled':>15} {'boot p':>8}")
    for lbl, fr, mean_all, n, r in out:
        filled = r[r["filled"] == 1]["ret_atr"]
        p = block_bootstrap_p(r["ret_atr"].to_numpy(), r["sess"].to_numpy(), n_boot=1200)
        p = p / 2 if mean_all > 0 else 1.0
        print(f"  {lbl:>16} {100*fr:>6.1f}% {mean_all:>+17.4f} "
              f"{filled.mean() if len(filled) else np.nan:>+15.4f} {p:>8.4f}")
    return out


if __name__ == "__main__":
    print("=" * 78)
    print("LIMIT vs MARKET ENTRY — does cheaper execution rescue the edge?")
    print(f"market cost {COST_MARKET} pts | limit cost {COST_LIMIT} pts | returns in ATR units")
    print("=" * 78)
    for nm, pat in [("SPX 2013-2018 (discovery)", "data/spx_*.csv"),
                    ("SPX 2010-2012 (holdout)", "data/SPXHOLD_*.csv"),
                    ("DAX 2010-2018", "data/GRXEUR_*.csv"),
                    ("EuroStoxx 2010-2018", "data/ETXEUR_*.csv")]:
        try:
            run(nm, pat)
        except Exception as e:
            print(f"{nm}: {e}")
