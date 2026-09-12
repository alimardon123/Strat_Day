"""Step 9 — change the AXIS, not the signal.

Everything so far searched the same dimension: intraday timing, one index, price history.
Three structurally different places an edge can live:

  A. HOLDING PERIOD  — overnight vs intraday return decomposition.
     One round trip per day means cost is amortised over a much larger move.

  B. TIME ZONE       — information transfer between non-overlapping sessions.
     Europe cannot trade while the US is open. Does it fully price the US move by its
     own open, or only partially?

  C. CROSS-SECTION   — DAX vs EuroStoxx relative value. Same session, ~90% correlated,
     different constituents. Divergence is a bet on the SPREAD, not on the market.

Same guards throughout: day-block bootstrap, and a Bonferroni floor for the number of
questions asked here.
"""
import numpy as np
import pandas as pd
from stats_engine import block_bootstrap_p
from step7_validate import load_symbol, detect_open, SESSION_MINUTES

SYMS = {"SPX": "data/spx_*.csv", "DAX": "data/GRXEUR_*.csv",
        "STOXX": "data/ETXEUR_*.csv", "NIKKEI": "data/JPXJPY_*.csv"}
COST_PCT = {"SPX": 0.33 / 2100, "DAX": 1.0 / 11000, "STOXX": 1.0 / 3200,
            "NIKKEI": 10.0 / 20000}   # round-trip cost as fraction of price


def daily_frame(pattern):
    """Session open/close per day, plus overnight and intraday returns in %."""
    df = load_symbol(pattern)
    om = detect_open(df)
    d = df.copy()
    d["mod"] = d["ts"].dt.hour * 60 + d["ts"].dt.minute
    d = d[(d["mod"] >= om) & (d["mod"] < om + SESSION_MINUTES)]
    d["date"] = d["ts"].dt.date
    g = d.groupby("date")
    out = pd.DataFrame({"open": g["open"].first(), "close": g["close"].last(),
                        "high": g["high"].max(), "low": g["low"].min(),
                        "bars": g.size()})
    out = out[out["bars"] > 100]
    out["prev_close"] = out["close"].shift(1)
    out["overnight"] = 100 * (out["open"] / out["prev_close"] - 1)
    out["intraday"] = 100 * (out["close"] / out["open"] - 1)
    out["total"] = 100 * (out["close"] / out["prev_close"] - 1)
    return out.dropna()


def score(name, r, days, cost_pct, n_tests):
    r = np.asarray(r, float)
    if len(r) < 100:
        return None
    ann = 252 / 1  # one trade per day
    sharpe = r.mean() / r.std() * np.sqrt(252) if r.std() > 0 else 0
    net = r - 100 * cost_pct
    sharpe_net = net.mean() / net.std() * np.sqrt(252) if net.std() > 0 else 0
    p = block_bootstrap_p(r, days, n_boot=2000)
    return dict(test=name, n=len(r), mean_pct=r.mean(), sharpe=sharpe,
                net_mean=net.mean(), net_sharpe=sharpe_net, p=p,
                bonf_pass=p < 0.05 / n_tests)


if __name__ == "__main__":
    D = {k: daily_frame(v) for k, v in SYMS.items()}
    for k, v in D.items():
        print(f"{k}: {len(v)} sessions, {v.index.min()} -> {v.index.max()}")

    rows, N_TESTS = [], 14

    # ---------- A. holding period ----------
    print("\n" + "=" * 92)
    print("A. OVERNIGHT vs INTRADAY — where does the equity return actually accrue?")
    print("=" * 92)
    for k, v in D.items():
        for leg in ["overnight", "intraday", "total"]:
            r = score(f"{k} {leg}", v[leg].to_numpy(), v.index.to_numpy(),
                      COST_PCT[k] if leg != "total" else 0, N_TESTS)
            if r:
                rows.append(r)
    print(f"{'test':>18} {'n':>6} {'mean%/day':>11} {'gross SR':>9} {'net mean%':>10} {'net SR':>8} {'boot p':>8}")
    for r in rows:
        print(f"{r['test']:>18} {r['n']:>6} {r['mean_pct']:>+11.4f} {r['sharpe']:>+9.2f} "
              f"{r['net_mean']:>+10.4f} {r['net_sharpe']:>+8.2f} {r['p']:>8.4f}")

    # ---------- B. time zone / information transfer ----------
    print("\n" + "=" * 92)
    print("B. TIME-ZONE SPILLOVER — does Europe fully price the prior US session?")
    print("=" * 92)
    spx = D["SPX"]
    tz_rows = []
    for eu in ["DAX", "STOXX"]:
        e = D[eu].copy()
        # US session ends ~16:00 ET; Europe's NEXT session opens the following morning
        e["us_prev"] = spx["intraday"].reindex(e.index).shift(1)
        e = e.dropna(subset=["us_prev"])
        sig = np.sign(e["us_prev"])
        for target, lbl in [("overnight", "EU gap"), ("intraday", "EU session")]:
            r = (sig * e[target]).to_numpy()
            s = score(f"{eu} {lbl} | US", r, e.index.to_numpy(), COST_PCT[eu], N_TESTS)
            if s:
                s["corr"] = np.corrcoef(e["us_prev"], e[target])[0, 1]
                tz_rows.append(s)
    print(f"{'test':>22} {'n':>6} {'mean%/day':>11} {'gross SR':>9} {'net mean%':>10} {'net SR':>8} {'boot p':>8} {'corr':>7}")
    for r in tz_rows:
        print(f"{r['test']:>22} {r['n']:>6} {r['mean_pct']:>+11.4f} {r['sharpe']:>+9.2f} "
              f"{r['net_mean']:>+10.4f} {r['net_sharpe']:>+8.2f} {r['p']:>8.4f} {r['corr']:>+7.3f}")
    rows += tz_rows

    # ---------- C. cross-section ----------
    print("\n" + "=" * 92)
    print("C. CROSS-SECTIONAL RELATIVE VALUE — DAX vs EuroStoxx spread reversion")
    print("=" * 92)
    a, b = D["DAX"], D["STOXX"]
    idx = a.index.intersection(b.index)
    x = pd.DataFrame({"a": a.loc[idx, "intraday"], "b": b.loc[idx, "intraday"],
                      "ao": a.loc[idx, "overnight"], "bo": b.loc[idx, "overnight"]})
    x["spread_prev"] = (x["a"] - x["b"]).shift(1)
    x["z"] = x["spread_prev"] / x["spread_prev"].rolling(60).std()
    x = x.dropna()
    print(f"daily return correlation DAX/STOXX: {np.corrcoef(x['a'], x['b'])[0,1]:.3f}")
    cost2 = COST_PCT["DAX"] + COST_PCT["STOXX"]   # two legs
    for thr in [0.0, 1.0, 1.5]:
        m = x["z"].abs() > thr
        sig = -np.sign(x.loc[m, "spread_prev"])          # fade yesterday's divergence
        r = (sig * (x.loc[m, "a"] - x.loc[m, "b"])).to_numpy()
        s = score(f"fade spread |z|>{thr}", r, x.index[m].to_numpy(), cost2, N_TESTS)
        if s:
            rows.append(s)
            print(f"{s['test']:>22} {s['n']:>6} {s['mean_pct']:>+11.4f} {s['sharpe']:>+9.2f} "
                  f"{s['net_mean']:>+10.4f} {s['net_sharpe']:>+8.2f} {s['p']:>8.4f}")

    res = pd.DataFrame(rows)
    res.to_csv("axis_tests.csv", index=False)
    print("\n" + "=" * 92)
    print(f"Bonferroni floor for {N_TESTS} tests: p < {0.05/N_TESTS:.4f}")
    surv = res[(res["p"] < 0.05 / N_TESTS) & (res["net_mean"] > 0)]
    print(f"survive AND positive after cost: {len(surv)}")
    for r in surv.itertuples():
        print(f"   {r.test}: net {r.net_mean:+.4f}%/day, net Sharpe {r.net_sharpe:+.2f}, p={r.p:.5f}")
