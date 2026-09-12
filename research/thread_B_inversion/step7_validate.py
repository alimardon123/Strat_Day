"""Step 7 — the real test.

One hypothesis, found by searching 282 candidates on SPX 2013-2018:

    Gap up + opening-range breakout up  ->  positive drift over the next 60 minutes.

Now confront it with data it has never seen:
  - SPX 2010-2012        (temporal holdout, same market)
  - DAX / Nikkei / EuroStoxx 2010-2018  (cross-market)

If this is a universal behavioural effect it should show up in all four.
If it was a fit to SPX 2013-2018, it will not.

Session start is detected from the data (the cash open makes a volatility spike),
so the same code works on every instrument without hand-tuning.
"""
import glob
import numpy as np
import pandas as pd
from stats_engine import block_bootstrap_p

COLS = ["ts", "open", "high", "low", "close", "vol"]
SESSION_MINUTES = 390


def load_symbol(pattern):
    fr = [pd.read_csv(f, sep=";", header=None, names=COLS) for f in sorted(glob.glob(pattern))]
    df = pd.concat(fr, ignore_index=True)
    df["ts"] = pd.to_datetime(df["ts"], format="%Y%m%d %H%M%S")
    df = df.sort_values("ts").drop_duplicates("ts").reset_index(drop=True)
    return df[df["ts"].dt.dayofweek < 5].reset_index(drop=True)


def detect_open(df):
    """Cash open = the minute-of-day where absolute returns jump the most."""
    d = df.copy()
    d["mod"] = d["ts"].dt.hour * 60 + d["ts"].dt.minute
    d["ar"] = d["close"].diff().abs()
    prof = d.groupby("mod")["ar"].mean().rolling(5, center=True).mean()
    jump = prof.diff(5)
    return int(jump.idxmax())


def to_5m_session(df, open_mod):
    d = df.copy()
    d["mod"] = d["ts"].dt.hour * 60 + d["ts"].dt.minute
    d = d[(d["mod"] >= open_mod) & (d["mod"] < open_mod + SESSION_MINUTES)]
    g = d.set_index("ts").resample("5min", label="right", closed="right")
    b = g.agg(open=("open", "first"), high=("high", "max"),
              low=("low", "min"), close=("close", "last")).dropna().reset_index()
    b["session"] = b["ts"].dt.date
    b["bar_i"] = b.groupby("session").cumcount()
    b = b[b.groupby("session")["bar_i"].transform("max") > 40]
    return b.reset_index(drop=True)


def signal_and_forward(b, horizon_bars=12):
    s = b["session"]
    daily = b.groupby(s).agg(o=("open", "first"), c=("close", "last"))
    daily["gap"] = daily["o"] - daily["c"].shift(1)
    daily["gap_z"] = daily["gap"] / daily["gap"].rolling(60).std()
    b = b.join(daily[["gap_z"]], on="session")

    first6 = b[b["bar_i"] < 6].groupby(s).agg(or_hi=("high", "max"), or_lo=("low", "min"))
    b = b.join(first6, on="session")
    b["or_up"] = (b["close"] > b["or_hi"]) & (b["bar_i"] >= 6)

    f = b["close"].shift(-horizon_bars) - b["close"]
    f[b["session"] != b["session"].shift(-horizon_bars)] = np.nan
    b["fwd"] = f
    b["atr"] = (b["high"] - b["low"]).rolling(14).mean()
    b["sig"] = (b["gap_z"] > 0.5) & b["or_up"]
    return b.dropna(subset=["fwd", "gap_z", "atr"])


def test(name, pattern):
    df = load_symbol(pattern)
    om = detect_open(df)
    b = to_5m_session(df, om)
    b = signal_and_forward(b)
    sel = b[b["sig"]]
    if len(sel) < 200:
        return None
    r = sel["fwd"].to_numpy(float)
    days = sel["session"].to_numpy()
    # normalise by ATR so instruments with different point values are comparable
    rn = (sel["fwd"] / sel["atr"]).to_numpy(float)
    p = block_bootstrap_p(rn, days, n_boot=2000)
    t = rn.mean() / (rn.std() / np.sqrt(len(rn)))
    base = b["fwd"] / b["atr"]
    return dict(market=name, open_ET=f"{om//60:02d}:{om%60:02d}", n=len(sel),
                eff_atr=rn.mean(), naive_t=t, p_boot=p / 2 if rn.mean() > 0 else 1.0,
                uncond=base.mean(), lift=rn.mean() - base.mean(),
                days=sel["session"].nunique())


if __name__ == "__main__":
    tests = [("SPX 2010-2012 (holdout)", "data/SPXHOLD_*.csv"),
             ("DAX 2010-2018", "data/GRXEUR_*.csv"),
             ("Nikkei 2010-2018", "data/JPXJPY_*.csv"),
             ("EuroStoxx 2010-2018", "data/ETXEUR_*.csv"),
             ("SPX 2013-2018 (discovery)", "data/spx_*.csv")]
    rows = [r for r in (test(n, p) for n, p in tests) if r]
    out = pd.DataFrame(rows)
    print("\nGAP-UP + OPENING-RANGE-BREAKOUT -> 60 MIN FORWARD RETURN")
    print("effect in ATR units; 'lift' = effect minus the unconditional drift of that market\n")
    print(f"{'market':>28} {'open':>6} {'days':>5} {'n':>6} {'effect':>8} {'uncond':>8} {'lift':>8} "
          f"{'naive t':>8} {'p_boot':>8}")
    for r in out.itertuples():
        print(f"{r.market:>28} {r.open_ET:>6} {r.days:>5} {r.n:>6} {r.eff_atr:>+8.4f} "
              f"{r.uncond:>+8.4f} {r.lift:>+8.4f} {r.naive_t:>+8.2f} {r.p_boot:>8.4f}")
    conf = out[out["market"] != "SPX 2013-2018 (discovery)"]
    print(f"\nindependent markets/periods confirming (p<0.05, positive): "
          f"{((conf['p_boot'] < 0.05) & (conf['eff_atr'] > 0)).sum()} of {len(conf)}")
    print(f"positive sign in: {(conf['eff_atr'] > 0).sum()} of {len(conf)}")
    out.to_csv("cross_market.csv", index=False)
