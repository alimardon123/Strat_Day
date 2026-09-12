"""Step 12 — quadrant 4: structural flow. The only day-tradeable quadrant left.

Premise: on certain KNOWN dates, large participants must trade regardless of price.
Index funds rebalance. Options expire and dealers unwind hedges. Pensions rebalance at
month-end. These are not forecasts — the dates are on a calendar years in advance.

Why this is the right shape for day trading: ~40 event days a year instead of 250+, so
the cost toll is paid a fraction as often for the same gross edge.

Events tested:
  - monthly option expiry (3rd Friday)
  - triple witching (3rd Friday of Mar/Jun/Sep/Dec)
  - month-end / first-of-month (pension + index rebalance flows)
  - quarter-end
  - the day before and after each

Same guards as everywhere: train/test split, day-block bootstrap, Bonferroni for the
number of questions asked.
"""
import numpy as np
import pandas as pd
from stats_engine import block_bootstrap_p
from step7_validate import load_symbol, detect_open, SESSION_MINUTES

TRAIN_END = pd.Timestamp("2016-01-01")


def intraday_frame():
    """Per-session open/close plus first-hour and last-hour returns, in %."""
    df = pd.concat([load_symbol("data/SPXHOLD_*.csv"), load_symbol("data/spx_*.csv")])
    df = df.sort_values("ts").drop_duplicates("ts").reset_index(drop=True)
    om = detect_open(df)
    d = df.copy()
    d["mod"] = d["ts"].dt.hour * 60 + d["ts"].dt.minute
    d = d[(d["mod"] >= om) & (d["mod"] < om + SESSION_MINUTES)]
    d["date"] = d["ts"].dt.date
    g = d.groupby("date")
    out = pd.DataFrame({"open": g["open"].first(), "close": g["close"].last(),
                        "high": g["high"].max(), "low": g["low"].min(), "bars": g.size()})
    # first hour / last hour
    fh = d[d["mod"] < om + 60].groupby("date")["close"].last()
    lh = d[d["mod"] >= om + SESSION_MINUTES - 60].groupby("date")["open"].first()
    out["fh_close"], out["lh_open"] = fh, lh
    out = out[out["bars"] > 300].dropna()
    out["r_day"] = 100 * (out["close"] / out["open"] - 1)
    out["r_first"] = 100 * (out["fh_close"] / out["open"] - 1)
    out["r_last"] = 100 * (out["close"] / out["lh_open"] - 1)
    out["r_mid"] = 100 * (out["lh_open"] / out["fh_close"] - 1)
    out["range_pct"] = 100 * (out["high"] - out["low"]) / out["open"]
    return out


def tag_events(idx):
    d = pd.DatetimeIndex(pd.to_datetime(idx))
    df = pd.DataFrame(index=idx)
    df["dt"] = d
    df["month"] = d.month
    df["is_fri"] = d.dayofweek == 4
    # 3rd Friday = the Friday whose day-of-month is 15..21
    df["opex"] = df["is_fri"] & d.day.isin(range(15, 22))
    df["triple"] = df["opex"] & d.month.isin([3, 6, 9, 12])
    # month boundaries within the actual trading calendar
    per = d.to_period("M")
    df["last_of_month"] = per != pd.Series(per).shift(-1).values
    df["first_of_month"] = per != pd.Series(per).shift(1).values
    q = d.to_period("Q")
    df["last_of_quarter"] = q != pd.Series(q).shift(-1).values
    df["opex_minus1"] = df["opex"].shift(-1).fillna(False).astype(bool)
    df["opex_plus1"] = df["opex"].shift(1).fillna(False).astype(bool)
    return df


def score(name, series, cost_pct, n_tests):
    s = series.dropna()
    if len(s) < 40:
        return None
    tr = s[pd.to_datetime(s.index) < TRAIN_END]
    te = s[pd.to_datetime(s.index) >= TRAIN_END]
    if len(tr) < 20 or len(te) < 15:
        return None
    d = 1 if tr.mean() >= 0 else -1              # direction locked on train
    r = (s * d)
    p = block_bootstrap_p(r.to_numpy(), np.arange(len(r)), 2000)
    net = r.mean() - cost_pct
    return dict(test=name, n=len(s), dir=d, train=tr.mean() * d, test_=te.mean() * d,
                all_mean=r.mean(), net=net, p=p / 2 if r.mean() > 0 else 1.0,
                bonf=p / 2 < 0.05 / n_tests if r.mean() > 0 else False)


if __name__ == "__main__":
    b = intraday_frame()
    ev = tag_events(b.index)
    print(f"sessions: {len(b)}  {b.index.min()} -> {b.index.max()}")
    print(f"opex days {ev['opex'].sum()} | triple {ev['triple'].sum()} | "
          f"month-end {ev['last_of_month'].sum()} | quarter-end {ev['last_of_quarter'].sum()}\n")

    COST = 100 * 0.33 / 2100     # one round trip, % of price
    print(f"round-trip cost: {COST:.4f}% of price\n")

    conds = {"opex": ev["opex"], "triple_witch": ev["triple"],
             "opex_minus1": ev["opex_minus1"], "opex_plus1": ev["opex_plus1"],
             "month_end": ev["last_of_month"], "month_first": ev["first_of_month"],
             "quarter_end": ev["last_of_quarter"],
             "normal_day": ~(ev["opex"] | ev["last_of_month"] | ev["first_of_month"])}
    legs = ["r_day", "r_first", "r_last", "r_mid"]
    N = len(conds) * len(legs)
    print(f"TOTAL TESTS: {N}   Bonferroni floor p < {0.05/N:.5f}\n")

    rows = []
    for cn, mask in conds.items():
        for leg in legs:
            r = score(f"{cn} / {leg}", b.loc[mask.values, leg], COST, N)
            if r:
                rows.append(r)

    res = pd.DataFrame(rows).sort_values("net", ascending=False)
    print(f"{'test':>26} {'n':>5} {'dir':>4} {'train%':>8} {'test%':>8} {'all%':>8} {'net%':>8} {'p':>8}")
    for r in res.itertuples():
        star = " ***" if r.bonf and r.net > 0 else (" *" if r.p < 0.05 and r.net > 0 else "")
        print(f"{r.test:>26} {r.n:>5} {r.dir:>+4d} {r.train:>+8.4f} {r.test_:>+8.4f} "
              f"{r.all_mean:>+8.4f} {r.net:>+8.4f} {r.p:>8.4f}{star}")

    print("\nvolatility check — is the range genuinely different on event days?")
    for cn, mask in conds.items():
        print(f"  {cn:>14}: mean range {b.loc[mask.values,'range_pct'].mean():.3f}%  n={mask.sum()}")

    ok = res[(res["bonf"]) & (res["net"] > 0) &
             (np.sign(res["train"]) == np.sign(res["test_"]))]
    print(f"\nBonferroni-significant, net-positive, sign consistent train->test: {len(ok)}")
    for r in ok.itertuples():
        print(f"   {r.test}: net {r.net:+.4f}%/trade, n={r.n}, p={r.p:.5f}")
    res.to_csv("flow_tests.csv", index=False)
