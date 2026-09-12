"""Step 16 — the signal hunt, with data that is NOT SPX price history.

Sixteen studies concluded the same thing: price history alone does not produce direction.
So this uses information from outside it — gold, oil, US 2y and 10y bonds, and the
Nikkei, all of which trade overnight and are fully closed/observable before the US opens.

Mechanism (why this could be real rather than a pattern): overnight risk sentiment gets
expressed in assets that trade while US equities are shut. If the US open does not fully
price that information, the residual shows up as intraday drift.

OBSERVABILITY IS ENFORCED: the signal window ends 15 minutes BEFORE the US open, and the
target starts AT the US open. No overlap. (This is the exact bug from step 9, inverted.)
"""
import glob
import numpy as np
import pandas as pd
from stats_engine import block_bootstrap_p

TRAIN_END = pd.Timestamp("2017-01-01")
ASSETS = ["XAU_USD", "WTICO_USD", "USB10Y_USD", "JP225_USD"]


def load_oanda(sym):
    fs = sorted(glob.glob(f"data/x/{sym}_*.csv"))
    fr = []
    for f in fs:
        try:
            d = pd.read_csv(f, usecols=["time", "close", "volume"])
            fr.append(d)
        except Exception:
            pass
    df = pd.concat(fr, ignore_index=True)
    df["ts"] = pd.to_datetime(df["time"])
    return df.drop(columns="time").sort_values("ts").drop_duplicates("ts").reset_index(drop=True)


def detect_us_session(spx):
    """Find the US equity session in whatever timezone this file uses."""
    d = spx.copy()
    d["mod"] = d["ts"].dt.hour * 60 + d["ts"].dt.minute
    prof = d.groupby("mod")["volume"].mean().rolling(5, center=True).mean()
    return int(prof.diff(5).idxmax())


def at_minute(df, target_mod, tol=8):
    """Last observed close at or just before target_mod, per date."""
    d = df.copy()
    d["mod"] = d["ts"].dt.hour * 60 + d["ts"].dt.minute
    d["date"] = d["ts"].dt.date
    d = d[(d["mod"] <= target_mod) & (d["mod"] >= target_mod - tol)]
    return d.groupby("date")["close"].last()


if __name__ == "__main__":
    spx = load_oanda("SPX500_USD")
    OPEN = detect_us_session(spx)
    CLOSE = OPEN + 390
    print(f"US session detected: {OPEN//60:02d}:{OPEN%60:02d} -> {CLOSE//60:02d}:{CLOSE%60:02d} "
          f"(file timezone)\nsignal window ends {(OPEN-15)//60:02d}:{(OPEN-15)%60:02d} — "
          f"15 min before the open, no overlap\n")

    spx_open = at_minute(spx, OPEN + 2)
    spx_close = at_minute(spx, CLOSE)
    tgt = (100 * (spx_close / spx_open - 1)).rename("target").dropna()

    feats = {}
    for s in ASSETS:
        df = load_oanda(s)
        pre = at_minute(df, OPEN - 15)          # observable before US open
        prev = at_minute(df, CLOSE)             # yesterday's US-close-time print
        overnight = 100 * (pre / prev.shift(1) - 1)
        feats[s] = overnight.dropna()
        print(f"{s:>12}: {len(feats[s])} overnight observations")

    X = pd.DataFrame(feats).join(tgt, how="inner").dropna()
    X = X[(X["target"].abs() < 6)]              # drop obvious data errors
    print(f"\naligned sessions: {len(X)}  train {(pd.to_datetime(X.index)<TRAIN_END).sum()} "
          f"test {(pd.to_datetime(X.index)>=TRAIN_END).sum()}\n")

    tr = X[pd.to_datetime(X.index) < TRAIN_END]
    te = X[pd.to_datetime(X.index) >= TRAIN_END]

    print("=" * 88)
    print("CROSS-ASSET OVERNIGHT MOVE -> US SESSION RETURN")
    print("=" * 88)
    print(f"{'asset':>12} {'corr(tr)':>9} {'corr(te)':>9} {'tr mean%':>9} {'TE mean%':>9} "
          f"{'TE t':>7} {'boot p':>8}")
    rows = []
    N = len(ASSETS) * 2
    for s in ASSETS:
        for thr_lbl, mask_fn in [("all", lambda v: np.abs(v) > 0),
                                 ("|z|>1", lambda v: np.abs(v) > v.std())]:
            d = 1 if np.corrcoef(tr[s], tr["target"])[0, 1] >= 0 else -1   # locked on train
            m_tr, m_te = mask_fn(tr[s]), mask_fn(te[s])
            r_tr = (d * np.sign(tr[s]) * tr["target"])[m_tr]
            r_te = (d * np.sign(te[s]) * te["target"])[m_te]
            if len(r_te) < 60:
                continue
            p = block_bootstrap_p(r_te.to_numpy(), np.arange(len(r_te)), 2000)
            t = r_te.mean() / (r_te.std() / np.sqrt(len(r_te)))
            rows.append(dict(asset=f"{s} {thr_lbl}", tr=r_tr.mean(), te=r_te.mean(),
                             t=t, p=p / 2 if r_te.mean() > 0 else 1.0, n=len(r_te)))
            print(f"{s+' '+thr_lbl:>12} "
                  f"{np.corrcoef(tr[s],tr['target'])[0,1]:>9.4f} "
                  f"{np.corrcoef(te[s],te['target'])[0,1]:>9.4f} "
                  f"{r_tr.mean():>+9.4f} {r_te.mean():>+9.4f} {t:>+7.2f} {rows[-1]['p']:>8.4f}")

    res = pd.DataFrame(rows)
    print(f"\nBonferroni floor for {len(res)} tests: p < {0.05/len(res):.5f}")
    surv = res[(res["p"] < 0.05 / len(res)) & (np.sign(res["tr"]) == np.sign(res["te"]))]
    print(f"survivors: {len(surv)}")
    for r in surv.itertuples():
        print(f"   {r.asset}: test mean {r.te:+.4f}%/day, t={r.t:+.2f}, p={r.p:.5f}, n={r.n}")
    res.to_csv("crossasset.csv", index=False)
