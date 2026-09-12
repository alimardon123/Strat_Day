"""Step 14 — can yesterday's VIX prepare you for today's session?

Three separate questions, which people constantly conflate:

  Q1  Does VIX predict today's RANGE?      (how big will the day be)
  Q2  Does VIX predict today's DIRECTION?  (which way will it go)
  Q3  Does VIX predict today's CHARACTER?  (trending vs chopping)

Q1 and Q3 are about volatility and structure. Q2 is about return. These have wildly
different predictability and conflating them is how people lose money "using the VIX".

VIX is taken at the PRIOR close — known before today's open, so everything here is
executable.
"""
import numpy as np
import pandas as pd
from stats_engine import block_bootstrap_p
from step7_validate import load_symbol, detect_open, SESSION_MINUTES

TRAIN_END = pd.Timestamp("2016-01-01")


def sessions():
    df = pd.concat([load_symbol("data/SPXHOLD_*.csv"), load_symbol("data/spx_*.csv")])
    df = df.sort_values("ts").drop_duplicates("ts").reset_index(drop=True)
    om = detect_open(df)
    d = df.copy()
    d["mod"] = d["ts"].dt.hour * 60 + d["ts"].dt.minute
    d = d[(d["mod"] >= om) & (d["mod"] < om + SESSION_MINUTES)]
    d["date"] = d["ts"].dt.date
    d["absmove"] = d["close"].diff().abs()
    g = d.groupby("date")
    out = pd.DataFrame({"open": g["open"].first(), "close": g["close"].last(),
                        "high": g["high"].max(), "low": g["low"].min(),
                        "path": g["absmove"].sum(), "bars": g.size()})
    out = out[out["bars"] > 300]
    out["range_pct"] = 100 * (out["high"] - out["low"]) / out["open"]
    out["ret_pct"] = 100 * (out["close"] / out["open"] - 1)
    # efficiency ratio: how much of the path travelled ended up as net movement
    out["eff"] = (out["close"] - out["open"]).abs() / out["path"]
    return out


def build():
    s = sessions()
    vix = pd.read_csv("data/vix.csv", parse_dates=["DATE"]).set_index("DATE")
    vix.index = vix.index.date
    df = s.join(vix[["CLOSE"]].rename(columns={"CLOSE": "vix"}), how="inner")
    df["vix_prev"] = df["vix"].shift(1)                    # known before today's open
    df["vix_chg"] = df["vix"].shift(1) - df["vix"].shift(2)
    df["vix_ma20"] = df["vix"].shift(1).rolling(20).mean()
    df["vix_stress"] = df["vix_prev"] / df["vix_ma20"]     # term-structure proxy
    return df.dropna()


def r2(x, y):
    x, y = np.asarray(x, float), np.asarray(y, float)
    return np.corrcoef(x, y)[0, 1] ** 2


if __name__ == "__main__":
    df = build()
    tr, te = df[pd.to_datetime(df.index) < TRAIN_END], df[pd.to_datetime(df.index) >= TRAIN_END]
    print(f"sessions {len(df)}  train {len(tr)}  test {len(te)}\n")

    print("=" * 76)
    print("Q1. DOES VIX PREDICT TODAY'S RANGE?   (volatility)")
    print("=" * 76)
    for lbl, d in [("train", tr), ("TEST", te)]:
        print(f"  {lbl:>6}  R2(vix_prev -> range)      = {r2(d['vix_prev'], d['range_pct']):.4f}")
        print(f"          R2(vix_prev -> |return|)   = {r2(d['vix_prev'], d['ret_pct'].abs()):.4f}")
    q = pd.qcut(df["vix_prev"], 5, labels=["v.low", "low", "mid", "high", "v.high"])
    print("\n  by VIX quintile (whole sample):")
    print(f"  {'quintile':>10} {'mean VIX':>9} {'mean range%':>12} {'mean |ret|%':>12} {'ratio hi/lo':>12}")
    g = df.groupby(q, observed=True)
    tab = g.agg(v=("vix_prev", "mean"), rng=("range_pct", "mean"), ar=("ret_pct", lambda x: x.abs().mean()))
    for name, r in tab.iterrows():
        print(f"  {str(name):>10} {r['v']:>9.2f} {r['rng']:>12.3f} {r['ar']:>12.3f}")
    print(f"  -> highest quintile range is {tab['rng'].iloc[-1]/tab['rng'].iloc[0]:.2f}x the lowest")

    print("\n" + "=" * 76)
    print("Q2. DOES VIX PREDICT TODAY'S DIRECTION?   (return)")
    print("=" * 76)
    for lbl, d in [("train", tr), ("TEST", te)]:
        print(f"  {lbl:>6}  R2(vix_prev -> return)     = {r2(d['vix_prev'], d['ret_pct']):.5f}")
        print(f"          R2(vix_chg  -> return)     = {r2(d['vix_chg'], d['ret_pct']):.5f}")
    print(f"\n  {'quintile':>10} {'mean ret%':>11} {'win%':>8} {'boot p':>9}")
    for name, gg in df.groupby(q, observed=True):
        p = block_bootstrap_p(gg["ret_pct"].to_numpy(), np.arange(len(gg)), 1500)
        print(f"  {str(name):>10} {gg['ret_pct'].mean():>+11.4f} {100*(gg['ret_pct']>0).mean():>7.1f}% {p:>9.4f}")

    print("\n" + "=" * 76)
    print("Q3. DOES VIX PREDICT TODAY'S CHARACTER?   (trend vs chop)")
    print("=" * 76)
    print(f"  {'quintile':>10} {'efficiency':>11} {'interpretation':>26}")
    for name, gg in df.groupby(q, observed=True):
        e = gg["eff"].mean()
        print(f"  {str(name):>10} {e:>11.4f}")
    print(f"\n  R2(vix_prev -> efficiency) train {r2(tr['vix_prev'], tr['eff']):.4f} | "
          f"TEST {r2(te['vix_prev'], te['eff']):.4f}")

    print("\n" + "=" * 76)
    print("THE PRACTICAL PAYOFF — constant-risk sizing")
    print("=" * 76)
    # fixed size vs VIX-scaled size, on the same trades
    target = df["range_pct"].mean()
    fixed = df["ret_pct"]
    scaled = df["ret_pct"] * (target / (0.0 + df["vix_prev"] * df["range_pct"].mean() / df["vix_prev"].mean()))
    # simpler + honest: size inversely to predicted range, predicted from vix only
    pred = np.polyval(np.polyfit(tr["vix_prev"], tr["range_pct"], 1), df["vix_prev"])
    size = target / pred
    scaled = df["ret_pct"] * size
    for lbl, x in [("fixed size", fixed), ("VIX-scaled size", scaled)]:
        print(f"  {lbl:>18}: daily vol {x.std():.4f}%  |  vol-of-vol "
              f"{x.abs().rolling(21).std().std():.4f}  |  worst day {x.min():+.3f}%")
    print(f"\n  R2 of range prediction on TEST: {r2(pred[-len(te):], te['range_pct']):.4f}")
