"""A45 forward-sizing table (owner's rulebook, ACCEPTANCE.md amendment A45 rule 1), measured at the
extended frame's own last COMPLETE regular session -- not an assumed index level.

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

The measured level is the most recent COMPLETE session in the extended frame
(`sessions.build_extended`): `measure_level` walks back from the latest date to the most recent
session with `bars >= sessions.FULL_BARS` AND max `mod` >= `sessions.RTH_END - 5` (within the last
five minutes of the regular session, mod 959 is 15:59) -- `sessions._sessionize` itself only
requires `MIN_BARS` (300) to keep a session, so the LATEST session in the frame can be a partial
one printed by an intraday refresh of the owner's minute file (as low as 306 bars); sizing off
that session's own last-printed bar would silently understate the true close. `level_date` is
that session's date, `level_spx_pts` is the close of its highest-mod (latest) bar, and
`level_session_bars` (also written to the output CSV, for auditability) is that session's own bar
count. `level_spy_usd = level_spx_pts / XSP_SPY_DIVISOR` (A6: XSP and SPY trade at one tenth of
the SPX premium; this is a fixed instrument-scale constant, not `meta["scale"]`, which is a FEED
unit conversion applied only to the raw ext bars themselves before they ever reach this unit).
Fully deterministic: no randomness, no network, no fitted parameter.

When `data/ext` is absent (`sessions.build_extended` returns `meta is None`), or no session in the
frame is complete enough per `measure_level` above, there is no measured level to size from; this
unit writes an empty output file and returns, exiting 0 -- a deliberate silent-empty for "no ext
feed (or no complete session yet), so no current level exists", distinct from A32's failure signal
(`ACCEPTANCE.md:163`: empty output AND a `<out>.error` file AND exit code 2). This unit's step is
listed in `run_all.HOLDOUT_STEPS`, so it is skipped entirely when `data/ext` is absent; the branch
above only matters when `data/ext` is present but every session in it is incomplete. Any other,
unexpected exception is still caught by `_gh.run` (below), which DOES follow the A32 convention.
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
            "level_spy_usd", "level_session_bars", "cost_spx_usd", "cost_xsp_usd", "cost_spy_usd",
            "min_account_spx_usd", "min_account_xsp_usd", "min_account_spy_usd"]


def measure_level(frame):
    """Pure function of the session frame (no I/O): the most recent COMPLETE session, walking back
    from the latest date. Complete means `bars >= sessions.FULL_BARS` AND the session's own max
    `mod` >= `sessions.RTH_END - 5` (within the last five minutes of the 09:30-15:59 regular
    session; mod 959 is 15:59) -- guards against measuring off a session an intraday refresh of
    the owner's minute file has truncated (`sessions._sessionize` itself only enforces the lower
    `MIN_BARS` floor of 300, kept for other reasons -- half days, thin holiday trading -- that
    still belong in the frame). Returns `(level_date, level_spx_pts, level_session_bars)` for that
    session, or None if no session in the frame qualifies."""
    bars = frame.groupby("date").size()
    max_mod = frame.groupby("date")["mod"].max()
    complete = bars.index[(bars >= sessions.FULL_BARS) & (max_mod >= sessions.RTH_END - 5)]
    if not len(complete):
        return None
    level_date = complete.max()
    day = frame[frame["date"] == level_date]
    level_spx_pts = float(day.loc[day["mod"].idxmax(), "close"])
    return level_date, level_spx_pts, int(bars.loc[level_date])


def build_rows(level_date, level_spx_pts, level_spy_usd, level_session_bars):
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
                level_spy_usd=level_spy_usd, level_session_bars=level_session_bars, cost_spx_usd=cost_spx_usd,
                cost_xsp_usd=cost_xsp_usd, cost_spy_usd=cost_spy_usd, min_account_spx_usd=cost_spx_usd / (x_pct / 100),
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
    measured = measure_level(frame)
    if measured is None:
        open(out, "w").close()
        return
    level_date, level_spx_pts, level_session_bars = measured
    level_spy_usd = level_spx_pts / XSP_SPY_DIVISOR
    res = build_rows(level_date.strftime("%Y-%m-%d"), level_spx_pts, level_spy_usd, level_session_bars)
    res.to_csv(out, index=False, float_format="%.6f")
    print(res.to_string(index=False, float_format=lambda x: f"{x:.4f}"))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", default="extended")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    _gh.run(lambda: main(a.inp, a.out), a.out)
