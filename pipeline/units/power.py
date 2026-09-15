"""A47 detectability floor -- an ANALYSIS of measurements already published, not a trial. It adds
ZERO trials, computes no new signal, opens no window, fits no parameter and can promote nothing;
the family stays at 45 (ACCEPTANCE.md amendment A47).

    python -m pipeline.units.power --in out --out out/power_analysis.csv

Every result in this programme is judged against the six-condition survival rule, whose condition
6 is a floor of n >= 200 holdout trades. This unit checks that floor against the per-trade
dispersion actually observed, for every candidate that already has a published per-trade series --
nothing is re-fitted, nothing is re-run. Per (source, window, candidate) group of >= 2 trades it
computes n/mean/sd/se/t of net index points per trade (A47 point 1), the minimum detectable effect
at the observed n and at the n=200 floor (A47 point 2), the n required to detect a 1.0- and
2.0-point edge -- the two cost levels every result in this programme is already reported at
(ACCEPTANCE.md:104-106) -- at the same one-sided alpha=0.05/80%-power normal approximation (A47
point 3), signals per year on the group's own published window and hence years to reach each n
above (A47 point 4), and the MDE and mean as a percentage of the 2%-ITM premium at the measured
level in `out/sizing_forward.csv` (A47 point 5). IID per-trade returns and the normal
approximation are the amendment's own stated assumptions; every MDE here is therefore a LOWER
bound (the programme's own p-values use a day-block bootstrap precisely because trades cluster by
day). No multiplicity adjustment -- these are per-candidate detectability figures, not test
statistics.

STEP A's inventory (which per-trade series exist, read here without re-deriving any of them):
  `out/flatten_candidates_trades.csv`   (A46/A46a, 3 trials x 3 windows): `net_pts_cost1`, grouped
      by (window, trial).
  `out/gapliq_candidates_trades.csv`    (A39, 3 trials x 3 windows): `net_pts_cost1`, grouped by
      (window, trial).
  `out/letf_candidates_trades.csv`      (A38): `net_pts_cost1`, grouped by (window, trial) --
      EMPTY on a checkout without `data/ext/letf_aum_2006_2026.csv` (the unit's own [SKIP]
      convention), in which case this file contributes no rows here, not a fabricated one.
  `out/reconcile_trades_selection.csv`  (D1, all 17 SELECTION-window candidates incl. the two
      pre-registered signals): `net_pts`, grouped by `candidate` (this file carries no `window`
      column of its own -- it is written only for the SELECTION window, 2013-01-01..2020-05-13, by
      `pipeline.reconcile`'s `mode="insample"` path, so `window` is set to the literal constant
      "SELECTION" here, not invented).
  The two pre-registered signals' HOLDOUT per-trade series (searched for per the amendment; not
      one of the four files above): `pipeline.insample`'s own D4 per-trade pricing tables,
      `out/holdout_d4_<candidate>_s1_cash_k<k>.csv` (`pipeline.playbook.build`), spread=1 (the
      "cost1" convention) and settle="cash" (the headline convention, not the SPY-only "exit"
      alternative); `k` does not affect the underlying `pts` column at all (only the option-leg
      columns downstream of it), so k=1.0 is read for both signals without loss -- verified
      `pts` is byte-identical across k in this file family before relying on it. `net_pts_cost1`
      is not a column of this file; it is `pts - COST1` (COST1=1.0, the same constant this whole
      programme uses for "cost1"), NOT a value read from any summary. Window is the literal
      constant "HOLDOUT" (`pipeline.insample`'s own D2 holdout window, 2020-06-01..2026-09-11).
  No candidate anywhere in this run is known to exist (from a summary row) but missing its
  trade-level series; the letf case above is "zero candidates produced", not "a known candidate
  with an unavailable series" -- there is nothing to attach a `note` to. `note` is kept as the last
  output column per the pre-registration and is populated only if a future run hits that case.

Fully deterministic: no clock, no randomness, no fitted parameter -- every number above is a
closed-form statistic of an already-published series. On failure (an unexpected exception) this
unit follows `pipeline.units._gh.run` exactly as sizing.py/flatten.py do: an empty (zero-byte)
output file, exit code 2 (A32); on the ordinary path of "no group had >= 2 trades" it writes a
header-only CSV (this unit's own convention, distinct from A32's failure signal), same as the
sibling fleet units' own no-candidate branch (letf.py, eventvol.py, sellvol.py).
"""
import argparse
import math
import os

import numpy as np
import pandas as pd
from scipy.stats import norm

from pipeline.units import _gh

Z_ALPHA = norm.ppf(0.95)   # one-sided alpha = 0.05
Z_BETA = norm.ppf(0.80)    # 80% power
Z_SUM = Z_ALPHA + Z_BETA   # (A47 point 2/3: MDE = z_sum * sd / sqrt(n); n_req = ceil((z_sum*sd/delta)^2))
COST1, COST2 = 1.0, 2.0    # SPX points round trip -- same convention as flatten.py/gapliq.py/insample.py
ITM_PCT = 0.02             # 2% ITM (sizing.py / report.py section 6 convention)
N_FLOOR = 200               # ACCEPTANCE's own survival-rule condition 6

# The two pre-registered signals' HOLDOUT per-trade files (spread=1 "cost1", settle="cash", k=1.0
# -- `pts` is identical across k and settle="cash" within a signal, see module docstring).
HOLDOUT_SIGNAL_FILES = [
    "out/holdout_d4_1300_call_gapgt0.3pct_s1_cash_k1.0.csv",
    "out/holdout_d4_1500_both_vixmove_exp_s1_cash_k1.0.csv",
]
# (path, window column name, candidate column name, net-points-per-trade column name)
GROUPED_TRADE_FILES = [
    ("out/flatten_candidates_trades.csv", "window", "trial", "net_pts_cost1"),
    ("out/gapliq_candidates_trades.csv", "window", "trial", "net_pts_cost1"),
    ("out/letf_candidates_trades.csv", "window", "trial", "net_pts_cost1"),
]
OUT_COLS = ["source", "window", "candidate", "n", "mean_net_pts", "sd_net_pts", "se_net_pts", "t",
            "mde_at_n", "mde_at_200", "n_req_1pt", "n_req_2pt", "span_years", "signals_per_year",
            "years_to_200", "years_to_n_req_1pt", "years_to_n_req_2pt", "premium_pts",
            "mde_at_200_pct_of_premium", "mean_pct_of_premium", "note"]


def _read_csv_or_empty(path):
    """`path` as a DataFrame, or an empty DataFrame when there is no usable row: file missing,
    zero bytes, an unparsable CSV (`pd.errors.EmptyDataError`) -- the same guard
    `pipeline.report._csv_rows_or_none` uses, restated here as a unit-local helper (pipeline.units
    modules do not import pipeline.report)."""
    if not os.path.exists(path) or os.path.getsize(path) == 0:
        return pd.DataFrame()
    try:
        return pd.read_csv(path)
    except pd.errors.EmptyDataError:
        return pd.DataFrame()


def _read_premium_pts():
    """The 2%-ITM contract cost in index points at the measured level (`out/sizing_forward.csv`,
    A45/`pipeline.units.sizing`); returns NaN (never a hardcoded level) when the file is missing,
    empty, unparsable or has no usable row -- the premium-relative output columns are then left
    empty by `group_row` below."""
    sf = _read_csv_or_empty("out/sizing_forward.csv")
    if not len(sf) or "level_spx_pts" not in sf:
        return np.nan
    return ITM_PCT * float(sf["level_spx_pts"].iloc[0])


def _long_rows():
    """The full inventory (module docstring) collapsed to one long table: source, window,
    candidate, net_pts (already the net-of-cost1 points-per-trade series in every case), date.
    A source that is missing, empty or unparsable simply contributes no rows -- STEP A's "do not
    guess" rule: a candidate this unit cannot see is a candidate it does not report on."""
    frames = []
    for path, wcol, ccol, vcol in GROUPED_TRADE_FILES:
        df = _read_csv_or_empty(path)
        if not len(df):
            continue
        frames.append(pd.DataFrame({"source": path, "window": df[wcol], "candidate": df[ccol],
                                     "net_pts": df[vcol], "date": df["date"]}))
    rec = _read_csv_or_empty("out/reconcile_trades_selection.csv")
    if len(rec):
        frames.append(pd.DataFrame({"source": "out/reconcile_trades_selection.csv", "window": "SELECTION",
                                     "candidate": rec["candidate"], "net_pts": rec["net_pts"], "date": rec["date"]}))
    for path in HOLDOUT_SIGNAL_FILES:
        df = _read_csv_or_empty(path)
        if not len(df):
            continue
        frames.append(pd.DataFrame({"source": path, "window": "HOLDOUT", "candidate": df["candidate"],
                                     "net_pts": df["pts"] - COST1, "date": df["date"]}))
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=["source", "window", "candidate", "net_pts", "date"])


def mde(sd, n):
    """Minimum detectable effect, one-sided alpha=0.05, 80% power, normal approximation
    (A47 point 2): (z_0.95 + z_0.80) * sd / sqrt(n). Pure function of (sd, n)."""
    return Z_SUM * sd / math.sqrt(n)


def n_req(sd, delta):
    """Trades required to detect a `delta`-point edge at the same alpha/power (A47 point 3),
    ceil'd since a fractional trade cannot be run. Pure function of (sd, delta)."""
    return math.ceil((Z_SUM * sd / delta) ** 2)


def group_row(source, window, candidate, net_pts, dates, premium_pts):
    """One output row for a (source, window, candidate) group of net-points-per-trade
    observations, or None if the group has fewer than 2 trades (a sample sd needs n >= 2 -- a
    1-trade group is SKIPPED, never emitted with a NaN sd). Pure function of its arguments (no
    I/O), so it is directly testable on synthetic series without a data loader."""
    net_pts = np.asarray(net_pts, dtype=float)
    n = len(net_pts)
    if n < 2:
        return None
    mean = float(net_pts.mean())
    sd = float(net_pts.std(ddof=1))
    se = sd / math.sqrt(n)
    t = mean / se if se > 0 else np.nan
    mde_n = mde(sd, n)
    mde_200 = mde(sd, N_FLOOR)
    n1, n2 = n_req(sd, COST1), n_req(sd, COST2)
    d = pd.to_datetime(pd.Series(dates))
    span_years = float((d.max() - d.min()).days) / 365.25
    signals_per_year = n / span_years if span_years > 0 else np.nan
    have_rate = pd.notna(signals_per_year) and signals_per_year > 0
    years_200 = N_FLOOR / signals_per_year if have_rate else np.nan
    years_1pt = n1 / signals_per_year if have_rate else np.nan
    years_2pt = n2 / signals_per_year if have_rate else np.nan
    have_premium = pd.notna(premium_pts) and premium_pts > 0
    mde_pct = 100 * mde_200 / premium_pts if have_premium else np.nan
    mean_pct = 100 * mean / premium_pts if have_premium else np.nan
    return dict(source=source, window=window, candidate=candidate, n=n, mean_net_pts=mean, sd_net_pts=sd,
                se_net_pts=se, t=t, mde_at_n=mde_n, mde_at_200=mde_200, n_req_1pt=n1, n_req_2pt=n2,
                span_years=span_years, signals_per_year=signals_per_year, years_to_200=years_200,
                years_to_n_req_1pt=years_1pt, years_to_n_req_2pt=years_2pt,
                premium_pts=premium_pts if pd.notna(premium_pts) else np.nan,
                mde_at_200_pct_of_premium=mde_pct, mean_pct_of_premium=mean_pct, note="")


def main(inp, out):
    if inp != "out":
        raise ValueError(f"pipeline.units.power only supports --in out (got {inp!r})")
    long = _long_rows()
    premium_pts = _read_premium_pts()
    rows = []
    if len(long):
        for (source, window, candidate), g in long.groupby(["source", "window", "candidate"], sort=False):
            row = group_row(source, window, candidate, g["net_pts"].to_numpy(), g["date"].to_numpy(), premium_pts)
            if row is not None:
                rows.append(row)
    res = pd.DataFrame(rows, columns=OUT_COLS)
    res = res.sort_values(["source", "window", "candidate"]).reset_index(drop=True) if len(res) else res
    res.to_csv(out, index=False, float_format="%.6f")
    print(res.to_string(index=False, float_format=lambda x: f"{x:.4f}"))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", default="out")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    _gh.run(lambda: main(a.inp, a.out), a.out)
