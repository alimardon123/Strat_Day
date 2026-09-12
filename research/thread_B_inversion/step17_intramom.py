"""Step 17 — Market intraday momentum (Gao et al. JFE 2018; Baltussen et al. JFE 2021).

The claim: the return from the prior close up to the last 30 minutes predicts the return
in the last 30 minutes. Mechanism: option market makers and leveraged ETFs are short
gamma and must hedge in the direction of the day's move before the close.

Why this is the best candidate the project has seen:
  - peer-reviewed twice in the top finance journal
  - a structural mechanism (forced hedging), not a pattern
  - one trade per day, 30-minute hold -> frequency the cost law says is viable
  - a 2024 study says it survives only in high-vol regimes, and VIX already
    forecasts the regime (Part 7, R2 = 0.54)

Test structure:
  discovery   SPX 2010-2018 (histdata)          -- paper published May 2018
  holdout     SPX 2019-2020 (oanda, different feed) -- fully post-publication
"""
import glob
import numpy as np
import pandas as pd
from stats_engine import block_bootstrap_p
from step7_validate import load_symbol, detect_open, SESSION_MINUTES

COST_PCT = 100 * 0.33 / 2100        # ES round trip


def half_hours_histdata():
    df = pd.concat([load_symbol("data/SPXHOLD_*.csv"), load_symbol("data/spx_*.csv")])
    df = df.sort_values("ts").drop_duplicates("ts").reset_index(drop=True)
    return _half_hours(df, detect_open(df))


def half_hours_oanda():
    fs = sorted(glob.glob("data/x/SPX500_USD_2019_*.csv") + glob.glob("data/x/SPX500_USD_2020_*.csv"))
    fr = [pd.read_csv(f, usecols=["time", "open", "high", "low", "close", "volume"]) for f in fs]
    df = pd.concat(fr, ignore_index=True)
    df["ts"] = pd.to_datetime(df["time"])
    df = df.drop(columns="time").sort_values("ts").drop_duplicates("ts").reset_index(drop=True)
    d = df.copy()
    d["mod"] = d["ts"].dt.hour * 60 + d["ts"].dt.minute
    om = int(d.groupby("mod")["volume"].mean().rolling(5, center=True).mean().diff(5).idxmax())
    return _half_hours(df, om)


def _half_hours(df, om):
    d = df.copy()
    d["mod"] = d["ts"].dt.hour * 60 + d["ts"].dt.minute
    d["date"] = d["ts"].dt.date
    d = d[(d["mod"] >= om) & (d["mod"] < om + SESSION_MINUTES)]

    def px_at(m):
        s = d[(d["mod"] <= m) & (d["mod"] >= m - 5)].groupby("date")["close"].last()
        return s
    out = pd.DataFrame({
        "prev_close": d.groupby("date")["close"].last().shift(1),
        "open": d.groupby("date")["open"].first(),
        "p_1030": px_at(om + 30),
        "p_1500": px_at(om + 330),
        "p_1530": px_at(om + 360),
        "close": d.groupby("date")["close"].last(),
        "bars": d.groupby("date").size(),
    })
    out = out[out["bars"] > 300].dropna()
    out["r1"] = 100 * (out["p_1030"] / out["prev_close"] - 1)      # first half-hour incl. gap
    out["r12"] = 100 * (out["p_1530"] / out["p_1500"] - 1)         # 15:00-15:30
    out["r_rest"] = 100 * (out["p_1530"] / out["prev_close"] - 1)  # prev close -> 15:30
    out["r13"] = 100 * (out["close"] / out["p_1530"] - 1)          # TARGET: last 30 min
    return out


def evaluate(df, sig, label, cost=COST_PCT):
    s = df.dropna(subset=[sig, "r13"])
    r = np.sign(s[sig]) * s["r13"]
    net = r - cost
    p = block_bootstrap_p(r.to_numpy(), pd.PeriodIndex(pd.to_datetime(s.index), freq="M").astype(str), 2000)
    corr = np.corrcoef(s[sig], s["r13"])[0, 1]
    sr = net.mean() / net.std() * np.sqrt(252)
    return dict(label=label, n=len(s), corr=corr, r2=corr ** 2, gross=r.mean(), net=net.mean(),
                win=100 * (r > 0).mean(), sharpe_net=sr, p=p / 2 if r.mean() > 0 else 1.0)


def show(rows):
    print(f"{'':>34} {'n':>5} {'corr':>7} {'R2%':>6} {'gross%':>8} {'net%':>8} {'win%':>6} "
          f"{'net SR':>7} {'boot p':>8}")
    for r in rows:
        print(f"{r['label']:>34} {r['n']:>5} {r['corr']:>+7.3f} {100*r['r2']:>6.2f} "
              f"{r['gross']:>+8.4f} {r['net']:>+8.4f} {r['win']:>6.1f} {r['sharpe_net']:>+7.2f} "
              f"{r['p']:>8.4f}")


if __name__ == "__main__":
    A = half_hours_histdata()
    B = half_hours_oanda()
    vix = pd.read_csv("data/vix.csv", parse_dates=["DATE"]).set_index("DATE")
    vix.index = vix.index.date
    for X in (A, B):
        X["vix"] = vix["CLOSE"].reindex(X.index).shift(1)   # prior close, known before open
    print(f"discovery 2010-2018: {len(A)} sessions | holdout 2019-2020: {len(B)} sessions")
    print(f"last-half-hour return std: {A['r13'].std():.4f}%  (cost is {COST_PCT:.4f}%)\n")

    print("=" * 96)
    print("REPLICATION, 2010-2018 — sign of predictor -> trade the last 30 minutes")
    print("=" * 96)
    show([evaluate(A, "r1", "Gao: first half-hour (r1)"),
          evaluate(A, "r12", "Gao: 15:00-15:30 (r12)"),
          evaluate(A, "r_rest", "Baltussen: prev close -> 15:30")])

    print("\n" + "=" * 96)
    print("POST-PUBLICATION HOLDOUT, 2019-2020 — different data feed, paper already public")
    print("=" * 96)
    show([evaluate(B, "r1", "Gao: first half-hour (r1)"),
          evaluate(B, "r12", "Gao: 15:00-15:30 (r12)"),
          evaluate(B, "r_rest", "Baltussen: prev close -> 15:30")])

    print("\n" + "=" * 96)
    print("CONDITIONED ON VIX (prior close) — is the effect a high-vol phenomenon?")
    print("=" * 96)
    for nm, X in [("2010-2018", A), ("2019-2020", B)]:
        X = X.dropna(subset=["vix"])
        q = pd.qcut(X["vix"], 3, labels=["low VIX", "mid VIX", "high VIX"])
        rows = [evaluate(X[q == k], "r_rest", f"{nm} | {k} | prev close->15:30") for k in q.cat.categories]
        show(rows)
        print()

    print("=" * 96)
    print("SIGNAL STRENGTH — does a bigger move predict better? (|r_rest| terciles, 2010-2018)")
    print("=" * 96)
    q = pd.qcut(A["r_rest"].abs(), 3, labels=["small", "medium", "large"])
    show([evaluate(A[q == k], "r_rest", f"|move| {k}") for k in q.cat.categories])
    pd.concat([A.assign(set="disc"), B.assign(set="hold")]).to_pickle("intramom.pkl")
