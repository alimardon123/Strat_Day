"""A45 forward-sizing table (owner's rulebook, ACCEPTANCE.md amendment A45 rule 1), measured at the
extended frame's own last regular-session close -- not an assumed index level.

    python -m pipeline.units.sizing --in extended --out out/sizing_forward.csv

One row per (convention, daily_limit_pct): convention `pre_A45` is the prior numeric-budget
convention (position size = daily limit / worst-trade loss, floor 100%, i.e. x_pct = the daily
limit itself and N = 1 full-loss attempt per day); convention `A45` is the rulebook's amended
convention (x_pct = 1% of account equity per trade always, N = floor(daily_limit_pct / 1%)
attempts per day -- N=3/4/5 at the 3/4/5% limits). Costs are the same 2%-ITM approximation
`pipeline/report.py` section 6 already uses (2% x S x 100), read here from the measured level
rather than an assumed S; XSP and SPY are one tenth of the SPX premium (A6 scale). Per A45, the
sizing table already published under the prior convention (playbook section 4, TRACK_C.md A43)
is NOT restated here or anywhere by this unit -- this file is the forward-trading convention only.

The measured level is the extended frame's (`sessions.build_extended`) own last regular session:
`level_date` = the max date in the frame, `level_spx_pts` = the close of that date's highest-mod
(latest) bar, `level_spy_usd` = level_spx_pts / meta["scale"] (10.0 for the SPY-scaled ext feed,
1.0 otherwise, A6). Fully deterministic: no randomness, no network, no fitted parameter.

When `data/ext` is absent (`sessions.build_extended` returns `meta is None`), there is no
measured level to size from; this unit writes an empty output file and returns (not an error --
the fleet contract's empty-output convention, `pipeline.units._gh.run`, reused here for the same
"never blocks the run" reason). On any other exception `_gh.run` (below) does the same.
"""
import argparse

import pandas as pd

from pipeline import sessions
from pipeline.units import _gh

CONVENTIONS = ["pre_A45", "A45"]
DAILY_LIMITS_PCT = [3.0, 4.0, 5.0]
ITM_PCT = 0.02          # 2% ITM (same approximation as report.py section 6)
CONTRACT_MULT = 100     # SPX/XSP/SPY option contract multiplier
XSP_SPY_DIVISOR = 10    # XSP/SPY premium is one tenth of SPX's (A6 scale)
OUT_COLS = ["convention", "daily_limit_pct", "x_pct", "attempts_per_day", "level_date", "level_spx_pts",
            "level_spy_usd", "cost_spx_usd", "cost_xsp_usd", "cost_spy_usd", "min_account_spx_usd",
            "min_account_xsp_usd", "min_account_spy_usd"]


def build_rows(level_date, level_spx_pts, level_spy_usd):
    """One row per (convention, daily_limit_pct), pure function of the measured level (no I/O),
    so it is directly testable without mocking the data loader. `level_date` is written as-is
    (the caller passes the YYYY-MM-DD string)."""
    cost_spx_usd = ITM_PCT * level_spx_pts * CONTRACT_MULT
    cost_xsp_usd = cost_spx_usd / XSP_SPY_DIVISOR
    cost_spy_usd = cost_spx_usd / XSP_SPY_DIVISOR
    rows = []
    for convention in CONVENTIONS:
        for daily_limit_pct in DAILY_LIMITS_PCT:
            if convention == "pre_A45":
                x_pct = daily_limit_pct         # size = daily limit / a 100% worst-trade loss
                attempts_per_day = 1
            else:
                x_pct = 1.0                      # A45 rule 1: 1% of account equity per trade
                attempts_per_day = int(daily_limit_pct // 1.0)
            rows.append(dict(
                convention=convention, daily_limit_pct=daily_limit_pct, x_pct=x_pct,
                attempts_per_day=attempts_per_day, level_date=level_date, level_spx_pts=level_spx_pts,
                level_spy_usd=level_spy_usd, cost_spx_usd=cost_spx_usd, cost_xsp_usd=cost_xsp_usd,
                cost_spy_usd=cost_spy_usd, min_account_spx_usd=cost_spx_usd / (x_pct / 100),
                min_account_xsp_usd=cost_xsp_usd / (x_pct / 100), min_account_spy_usd=cost_spy_usd / (x_pct / 100)))
    return pd.DataFrame(rows)[OUT_COLS]


def main(inp, out):
    if inp != "extended":
        raise ValueError(f"pipeline.units.sizing only supports --in extended (got {inp!r})")
    td = sessions.trading_days_from_vix()
    frame, _dropped, meta = sessions.build_extended(trading_days=td)
    if meta is None:
        open(out, "w").close()
        return
    level_date = frame["date"].max()
    day = frame[frame["date"] == level_date]
    level_spx_pts = float(day.loc[day["mod"].idxmax(), "close"])
    level_spy_usd = level_spx_pts / meta["scale"]
    res = build_rows(level_date.strftime("%Y-%m-%d"), level_spx_pts, level_spy_usd)
    res.to_csv(out, index=False, float_format="%.6f")
    print(res.to_string(index=False, float_format=lambda x: f"{x:.4f}"))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", default="extended")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    _gh.run(lambda: main(a.inp, a.out), a.out)
