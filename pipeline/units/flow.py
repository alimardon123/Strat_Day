"""PLAN rank 9 — "flows with a deadline" last-hour candidates, pre-registered on the in-sample
window so the holdout can test them untouched. Three trials (counted in SCORECARD.md):

  month_end   last trading day of the month, 15:00 decision: trade AGAINST the month-to-date
              move (pension/target-date rebalancing into the close)
  opex        third Friday of the month (options expiry; quarterly index rebalances fall on the
              same day in Mar/Jun/Sep/Dec): continue the open → 15:00 move into the close (pin unwind)
  russell     Russell reconstitution day (last Friday of June): long 15:00 → close (index buying)

    python -m pipeline.units.flow --in data/raw/oanda_SPX500_USD.parquet --out out/flow_candidates.csv
"""
import argparse

import numpy as np
import pandas as pd

from pipeline import sessions, signals, stats
from pipeline.units import _gh

COST_PTS = 1.0


def month_end_days(idx):
    s = pd.Series(idx, index=idx)
    return s.groupby(idx.to_period("M")).max().values


def third_fridays(idx):
    return [d for d in idx if d.dayofweek == 4 and 15 <= d.day <= 21]


def last_friday_june(idx):
    s = pd.Series(idx, index=idx)
    j = s[(idx.month == 6) & (idx.dayofweek == 4)]
    return j.groupby(j.index.year).max().values


def evaluate(day, dates, direction, name):
    t = day.loc[day.index.isin(dates)].dropna(subset=["ent_900", "close", "dec_900"]).copy()
    dirn = direction(t)
    t = t[dirn != 0]
    dirn = dirn[dirn != 0]
    ret = dirn * (t["close"] / t["ent_900"] - 1) * 100
    pts = dirn * (t["close"] - t["ent_900"]) - COST_PTS
    net_pct = ret - 100 * COST_PTS / t["ent_900"]
    # day-selection control: same count of random sessions, same direction rule applied to them
    pool = day.dropna(subset=["ent_900", "close", "dec_900"])
    rng = np.random.default_rng(0)
    ctrl = []
    for _ in range(200):
        pick = pool.iloc[rng.choice(len(pool), len(t), replace=False)]
        dp = direction(pick)
        ctrl.append((dp * (pick["close"] / pick["ent_900"] - 1) * 100 - 100 * COST_PTS / pick["ent_900"]).mean())
    return dict(candidate=name, n=len(t), win=100 * (pts > 0).mean(), net_pts=pts.mean(), net_pct=net_pct.mean(),
                p_boot_day=stats.one_sided_p(net_pct.to_numpy(), stats.day_blocks(t.index)),
                control_mean_pct=float(np.mean(ctrl)), excess_over_control_pct=net_pct.mean() - float(np.mean(ctrl)),
                frac_seeds_beaten=float((net_pct.mean() > np.array(ctrl)).mean()))


def main(path, out):
    vix = pd.read_parquet("data/raw/vix_daily.parquet")
    frame, _ = sessions.build("oanda", path, sessions.trading_days_from_vix())
    day = signals.day_table(frame, vix)
    day = day.loc["2005-01-01":"2020-05-13"]
    no930 = set(signals.sessions_without_open_bar(day))
    print(f"A52.3: opex days without a 09:30 bar (the only flow candidate that reads the open; must be 0): "
          f"{len(no930 & set(third_fridays(day.index)))}")
    mtd_base = day["close"].groupby(day.index.to_period("M")).transform("first")
    day["mtd"] = day["prev_close"] / mtd_base.shift(1).fillna(mtd_base) - 1
    rows = [
        evaluate(day, month_end_days(day.index), lambda t: -np.sign(t["mtd"]), "month_end: against MTD move, 15:00→close"),
        evaluate(day, third_fridays(day.index), lambda t: np.sign(t["dec_900"] / t["open"] - 1), "opex: continue open→15:00 move"),
        evaluate(day, last_friday_june(day.index), lambda t: pd.Series(1.0, index=t.index), "russell recon day: long 15:00→close"),
    ]
    res = pd.DataFrame(rows)
    res.to_csv(out, index=False, float_format="%.6f")
    print(res.to_string(index=False, float_format=lambda x: f"{x:.4f}"))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", default="data/raw/oanda_SPX500_USD.parquet")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    _gh.run(lambda: main(a.inp, a.out), a.out)
