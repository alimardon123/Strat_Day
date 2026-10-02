"""A50 positive control -- can this pipeline RECOVER an edge that is definitely there? A
VALIDATION, not a candidate (pre-registered 2026-09-16, before any code; ACCEPTANCE.md amendment
A50). It adds ZERO trials, computes no new signal on real data, opens no window, fits no
parameter and can promote nothing; the family stays at 48. Every number below is about the
PIPELINE, never about the market, and may not be cited as evidence for or against any strategy.

    python -m pipeline.units.poscontrol --in extended --out out/poscontrol.csv

**Scope, enumerated by A50, not asserted (the A49a guard): exactly four already-registered
candidates, one per family with a per-trade series and a HOLDOUT window** -- `gapliq` T1,
`flatten` U1, the D1 winner `15:00|both|vixmove_exp`, and `fvg` `short|R1|bos_off` (the family
A47 found best-powered, included precisely because it should detect the smallest delta).
HOLDOUT window only, each candidate's OWN window (gapliq/flatten/fvg: 2020-07-27..2026-09-11;
the D1 winner: 2020-06-01..2026-09-11, `pipeline.insample`'s own D2 window) -- never harmonised
to a single constant, per A50's "own signal days and own scoring path, unchanged".

**Method.** For each candidate, the REAL per-trade series is built by calling that candidate's
OWN, unmodified functions (`pipeline.units.gapliq.build_day_table`/`build_trades`,
`pipeline.units.flatten`'s equivalents, `pipeline.units.fvg.build_bars`/`detect_side`/`simulate`,
`pipeline.signals.day_table`/`candidate` for the D1 winner) on the real extended frame -- nothing
here re-derives a signal, a threshold or a trade. On an in-memory COPY of that candidate's own
trade table, a synthetic drift of exactly delta SPX index points is added to the realised
entry->exit move on that candidate's signal days ONLY (`inject_delta` below): `pts += delta` and
`ret_pct += 100*delta/entry_px`. These are not two independent injections -- they are the ONE
underlying price shift (exit_px -> exit_px + direction*delta) expressed in both units this
codebase already carries per trade, so the points and percent series stay mutually consistent
exactly as they would for a real trade, while every other column (date, entry_px, kind, stop_px,
...) and every OTHER session (all non-signal days, and every sibling trial's own signal days) is
left bit-for-bit untouched. A50 registered the drift "on a COPY of the underlying frame"
(ACCEPTANCE.md:882-884); the per-trade injection is used instead because it is the one that keeps
A50's other requirement -- "leaving all other sessions, all thresholds and the entire gate
untouched" -- which a drift added to the frame would break through the expanding percentile pools
(A52.1; an earlier version of this docstring attributed to A50 a sentence A50 does not contain).
Because the injection is additive on the scored series, `recovered_minus_delta` is zero by
arithmetic: it checks that the scoring path averages the same rows, not that an edge is recovered.
What does test the pipeline is the delta=0 rebuild from raw data and the survival floor (A50a).

Each candidate's COMPLETE scoring path is then re-run on the injected series by IMPORTING AND
CALLING the existing helpers -- never reimplementing a statistic: `pipeline.stats.one_sided_p`
(day-block AND month-block, n_boot 2000, seed 11 -- `pipeline.stats`'s own module defaults),
`pipeline.stats.calendar_day_sharpe`, `pipeline.stats.deflated_sharpe`, and each family's own
day-selection control and timing control (`gapliq.day_selection_control`/`timing_control`,
`flatten`'s equivalents, `fvg.random_entry_control`, `signals.day_selection_control`/
`timing_control` for the D1 winner). Both controls read only the trade COUNT and/or the REAL
underlying prices (never a trade's own `pts`/`ret_pct`), so they are automatically real and
unperturbed by construction -- exactly A50's "leaving... every other session... untouched",
applied to the controls themselves. The calendar-day Sharpe and the timing control are computed
(so the scoring path re-run is genuinely complete) but are not among A50's fixed output columns;
their delta=0 values are cross-checked against the published tables in VERIFICATION rather than
carried as CSV columns.

**Two ambiguities A50 left open, resolved here and flagged loudly in the accompanying report**
(both affect `survives_all_six` and are stated per-row in `notes`, never silently absorbed):

(1) *Which six conditions.* ACCEPTANCE.md's canonical survival rule has six conditions (net > 0;
    one-sided block-bootstrap p < 0.05; family-wide BH-FDR at 10%; positive excess over the
    day-selection control; deflated Sharpe > 0.95; n >= 200). `pipeline/report.py`'s own per-
    family HOLDOUT verdict for gapliq/flatten/fvg gates on only FOUR of these (DSR is "reported...
    not a survival condition" there). Since A50 names its own gate `survives_all_six` and asks
    for "the six survival conditions", this module uses ACCEPTANCE's canonical six for every
    candidate (including DSR > 0.95 as a gating condition for gapliq/flatten/fvg, not merely a
    reported number) -- a deliberate, documented departure from report.py's narrower per-family
    prose, not an oversight.
(2) *Condition 3 (family-wide BH-FDR) under a HOLDOUT-only injection.* `pipeline/trials.py`
    counts and FDR-tests "GAPLIQ T1"/"FLATTEN U1"/"FVG short|R1|bos_off" on their SELECTION-window
    p-value (`out/trials.csv`) -- a window this validation's HOLDOUT-only injection (A50's own
    scope) structurally cannot touch. Re-running condition 3 so that it responds to delta for
    these three would require ALSO injecting the SELECTION window, which is out of scope; this is
    exactly A50's own anticipated case ("a control whose own pool would also need injecting").
    For these three, condition 3 is therefore reported as the REAL, delta-invariant value read
    from `out/trials.csv` (frozen at its actual measured value, never fabricated), with the
    per-row `notes` stating plainly that it cannot respond to delta and giving the pass/fail of
    the other five, re-runnable conditions as the substantive diagnostic. The D1 winner is the
    ONE candidate of the four whose own scoring path counts and FDR-tests it on HOLDOUT itself
    (`pipeline/trials.py`'s "holdout" family block uses `p_month`); for it alone, condition 3 IS
    meaningfully re-run: the injected p-value is substituted into a COPY of the real 48-row
    `out/trials.csv` pool (the other 47 trials' real, unmodified p-values) and
    `pipeline.stats.bh_fdr` is called fresh (`_d1_fdr_recompute`).

`excess_over_control_pct`: each family's own condition-4 comparison is reused verbatim -- SPX
POINTS for gapliq/flatten/fvg (`report.py`'s own `net_pts_cost1 - control_mean_pts_cost1`
check), PERCENT for the D1 winner (`insample.py`'s own `net_pct.mean() - ctrl_net.mean()`,
matching `out/holdout_pooled.csv`'s own column). The column is not converted to a single common
unit (no such conversion exists in either family's own scoring path); the unit in force is
stated per-row in `notes`.

delta sweep, fixed by A50, not extended: {0.0, 0.25, 0.5, 1.0, 2.0, 4.0, 8.0}. delta=0.0 is the
re-run-unchanged case and MUST reproduce each candidate's published HOLDOUT n and mean net points
exactly (`out/gapliq_candidates.csv`, `out/flatten_candidates.csv`, `out/fvg_candidates.csv`,
`out/holdout_pooled.csv`) -- checked in VERIFICATION, reported first if it ever disagrees.

Fully deterministic: every bootstrap/control draw reuses each function's own fixed seed (day-
selection seed 11 for gapliq/flatten/fvg, seed 0 for the D1 winner -- `insample.py`'s own
un-overridden default; timing-control seed 7 for gapliq/flatten, seed 1 for the D1 winner;
stats.one_sided_p reseeded 11 per call); no clock, no randomness beyond those registered seeds.
On any exception this unit follows `pipeline.units._gh.run` exactly as gapliq.py/flatten.py do:
an empty (zero-byte) output file plus `<out>.error` with the traceback, exit code 2 (A32).
"""
import argparse
import os

import numpy as np
import pandas as pd

from pipeline import insample, sessions, signals, stats
from pipeline.units import _gh, flatten, fvg, gapliq

DELTAS = [0.0, 0.25, 0.5, 1.0, 2.0, 4.0, 8.0]   # index points; fixed by A50, never extended
D1_WINNER = "15:00|both|vixmove_exp"
D1_START = str(insample.HOLDOUT_START.date())   # "2020-06-01" -- insample.py's own D2 window start, reused not retyped
D1_END = "2026-09-11"                            # run_all.py's own literal end for the "holdout_d2" step
GAPLIQ_TARGET = "T1"
FLATTEN_TARGET = "U1"
FVG_TARGET = ("short", "off", 1)                 # side, bos, R -- trial name "short|R1|bos_off"
OUT_COLS = ["candidate", "family", "window", "delta", "n", "mean_net_pts", "recovered_minus_delta",
            "p_boot_day", "excess_over_control_pct", "dsr", "survives_all_six", "theoretical_mde_at_n", "notes"]

SPEC_NOTE = (
    "A50 (pre-registered 2026-09-16, before any code; ZERO new trials): 'On a COPY of the "
    "underlying frame, add a synthetic drift of exactly delta index points to the realised "
    "entry->exit move on that candidate's signal days ONLY, leaving all other sessions, all "
    "thresholds and the entire gate untouched. Re-run that candidate's complete scoring path on "
    "the injected copy.' Scope: gapliq T1, flatten U1, the D1 winner 15:00|both|vixmove_exp, fvg "
    "short|R1|bos_off; HOLDOUT window only; delta in {0.0,0.25,0.5,1.0,2.0,4.0,8.0}. Answer "
    "condition: (a) delta=0 reproduces the published result exactly; (b) the recovered mean "
    "tracks the injected delta within 0.05 pts; (c) the empirical detection floor is within a "
    "factor of 2 of A47's theoretical MDE. This constant is documentation only (traceability to "
    "the registration); A50 fixes poscontrol.csv's own output columns exactly, and `spec` is not "
    "one of them, so it is never written as a column here.")


def _read_csv_or_empty(path):
    """`path` as a DataFrame, or an empty DataFrame when there is no usable row: file missing,
    zero bytes, an unparsable CSV -- same guard as `pipeline.units.power._read_csv_or_empty`
    (restated locally: pipeline.units modules do not import each other's private helpers)."""
    if not os.path.exists(path) or os.path.getsize(path) == 0:
        return pd.DataFrame()
    try:
        return pd.read_csv(path)
    except pd.errors.EmptyDataError:
        return pd.DataFrame()


def inject_delta(trades, delta):
    """A50's method, on a COPY: add exactly `delta` SPX index points to each trade's realised
    entry->exit move. `pts += delta` is the additive, exact injection A50 asks for; `ret_pct` is
    NOT a second, independent injection -- it is re-derived from the SAME underlying price shift
    (shifting exit_px by direction*delta moves pts by direction^2*delta == delta and moves ret_pct
    by 100*delta/entry_px), so the points and percent series a real trade would show stay mutually
    consistent. Every other column (date, entry_px, kind, stop_px, ...) is untouched, and no row
    outside the given `trades` (i.e. no other session, no sibling trial) is touched at all."""
    t = trades.copy()
    t["pts"] = t["pts"] + delta
    t["ret_pct"] = t["ret_pct"] + 100.0 * delta / t["entry_px"]
    return t


def _net_pct1(trades, cost):
    return (trades["ret_pct"] - 100.0 * cost / trades["entry_px"]).to_numpy()


def _real_fdr(real_trials, trial_name):
    """The REAL, unmodified `fdr_pass_10pct_family` value already published in `out/trials.csv`
    for `trial_name` -- used, never fabricated, for the three families whose own scoring path
    counts and FDR-tests this trial on the SELECTION window (see module docstring point (2))."""
    if not len(real_trials):
        return False
    m = real_trials[real_trials["trial"] == trial_name]
    return bool(m["fdr_pass_10pct_family"].iloc[0]) if len(m) else False


def _d1_fdr_recompute(real_trials, p_for_fdr_injected):
    """The ONE candidate whose own scoring path counts and FDR-tests it on HOLDOUT itself
    (`pipeline/trials.py`'s 'holdout' family block): substitute the injected p-value into a COPY
    of the real 48-row `out/trials.csv` pool (every other trial's real, unmodified p) and call
    `pipeline.stats.bh_fdr` fresh. NaN (never a fabricated bool) if the real row cannot be found."""
    if not len(real_trials):
        return np.nan
    idx = real_trials.index[real_trials["trial"] == f"HOLDOUT {D1_WINNER}"]
    if len(idx) != 1:
        return np.nan
    pool = real_trials["p_for_fdr"].to_numpy(dtype=float).copy()
    pool[idx[0]] = p_for_fdr_injected
    passed = stats.bh_fdr(pool, alpha=0.10)
    return bool(passed[idx[0]])


def _read_power_mde(power_df, family, window, candidate):
    """A47's theoretical MDE at this candidate's OWN observed n (`mde_at_n`, not the n=200 floor),
    read from `out/power_analysis.csv`; NaN (guarded) if the file or the row is absent."""
    if not len(power_df):
        return np.nan
    m = power_df[(power_df["family"] == family) & (power_df["window"] == window)
                & (power_df["candidate"].astype(str) == str(candidate))]
    return float(m["mde_at_n"].iloc[0]) if len(m) else np.nan


def _fleet_notes(family, trial, fdr_real, c1, c2, c4, c5, c6, unit):
    """Per-row note for gapliq/flatten/fvg (module docstring point (2)): condition 3 is frozen at
    its real, SELECTION-window value; the substantive diagnostic is the other five, re-runnable
    conditions, spelled out here so `survives_all_six` reading False never gets silently absorbed
    as 'no edge recovered' when the actual reason is condition 3's window scope."""
    five = c1 and c2 and c4 and c5 and c6
    return (f"cond3(BH-FDR)=REAL/frozen={fdr_real} -- {family} {trial}'s own scoring path counts and FDR-tests "
            f"this trial on the SELECTION window (out/trials.csv), not HOLDOUT; a HOLDOUT-only injection (A50's "
            f"own scope) cannot touch it, so cond3 cannot respond to delta and is not meaningfully re-runnable "
            f"here (reported as the real, unmodified value, per A50's own instruction for a control whose pool "
            f"would also need injecting). ex-FDR 5-of-6 {'PASS' if five else 'do not all pass'} at this delta "
            f"(net{'+' if c1 else '-'} p_day{'+' if c2 else '-'} ctrl{'+' if c4 else '-'} dsr{'+' if c5 else '-'} "
            f"n{'+' if c6 else '-'}). excess_over_control_pct is in SPX {unit} here (this family's own "
            f"condition-4 comparison, report.py's own check), not percent.")


def _d1_notes(p_month, c1, c2, c4, c5, c6):
    """Per-row note for the D1 winner (module docstring point (2)): condition 3 IS meaningfully
    re-run here (see `_d1_fdr_recompute`); its own condition-2 gate uses p_boot_month (its own
    scoring path), not the p_boot_day column reported for cross-candidate comparability."""
    five = c1 and c2 and c4 and c5 and c6
    return (f"cond3(BH-FDR) RECOMPUTED: this candidate's own scoring path counts and FDR-tests it on HOLDOUT "
            f"itself (out/trials.csv 'HOLDOUT {D1_WINNER}' row); the injected p_boot_month was substituted into "
            f"a copy of the real 48-trial pool and BH-FDR (stats.bh_fdr) re-run fresh. Own cond2 gate uses "
            f"p_boot_month={p_month:.4f} (own scoring path; the p_boot_day column above is reported for "
            f"cross-candidate comparability only). ex-FDR 5-of-6 {'PASS' if five else 'do not all pass'} "
            f"(net{'+' if c1 else '-'} p_month{'+' if c2 else '-'} ctrl{'+' if c4 else '-'} psr{'+' if c5 else '-'} "
            f"n{'+' if c6 else '-'}). excess_over_control_pct is in PERCENT here (this candidate's own "
            f"condition-4 check), matching out/holdout_pooled.csv's own column.")


# --------------------------------------------------------------------------------------------
# gapliq T1
# --------------------------------------------------------------------------------------------

def _gapliq_all_real(day, start_ts, end_ts):
    """The REAL (unperturbed) HOLDOUT per-trade series for all 3 gapliq trials, built by calling
    gapliq.py's own build_trades on gapliq.py's own TRIALS list -- needed so T2/T3's real trials
    can feed the DSR sr_pool alongside T1's injected series (A50: only T1's own signal days are
    touched)."""
    out = {}
    w = day[(day.index >= start_ts) & (day.index <= end_ts)]
    for name, sig_col, entry_col, direction, kind, _entry_time in gapliq.TRIALS:
        sig = w[w[sig_col]]
        elig_dates = sig.index[sig["both_bars"]]
        out[name] = dict(trades=gapliq.build_trades(day, elig_dates, entry_col, direction, kind),
                         sig_col=sig_col, entry_col=entry_col, direction=direction, kind=kind)
    return out


def score_gapliq(frame, day, real, start_ts, end_ts, real_trials, delta):
    cost = gapliq.COST1
    target = real[GAPLIQ_TARGET]
    trades = inject_delta(target["trades"], delta)
    n = len(trades)
    net_pts = trades["pts"] - cost
    net_pct = trades["ret_pct"] - 100.0 * cost / trades["entry_px"]
    mean_net_pts = float(net_pts.mean()) if n else np.nan
    p_day = stats.one_sided_p(net_pct.to_numpy(), stats.day_blocks(trades["date"])) if n else np.nan
    ctrl = gapliq.day_selection_control(day, start_ts, end_ts, target["sig_col"], target["entry_col"],
                                        target["direction"], cost, n)
    control_mean_pts = float(np.nanmean(ctrl)) if len(ctrl) else np.nan
    excess = (mean_net_pts - control_mean_pts) if (n and pd.notna(control_mean_pts)) else np.nan
    if n:
        gapliq.timing_control(frame, day, trades["date"].to_numpy(), target["direction"], cost)  # re-run for
        # completeness (A50's "complete scoring path"); real/unperturbed by construction (reads only real
        # underlying prices, never a trade's own pts/ret_pct); not one of A50's fixed output columns.
    sr_pool = [stats.per_trade_sharpe(_net_pct1(trades if name == GAPLIQ_TARGET else info["trades"], cost))
              for name, info in real.items()]
    dsr = stats.deflated_sharpe(net_pct.to_numpy(), sr_trials=sr_pool, n=gapliq.DSR_N)[0] if n >= 3 else np.nan
    fdr_real = _real_fdr(real_trials, "GAPLIQ T1")
    c1 = bool(n and mean_net_pts > 0)
    c2 = bool(n and pd.notna(p_day) and p_day < 0.05)
    c3 = bool(fdr_real)
    c4 = bool(n and pd.notna(excess) and excess > 0)
    c5 = bool(n and pd.notna(dsr) and dsr > 0.95)
    c6 = bool(n >= 200)
    return dict(n=n, mean_net_pts=mean_net_pts, p_boot_day=p_day, excess_over_control_pct=excess, dsr=dsr,
               survives_all_six=(c1 and c2 and c3 and c4 and c5 and c6),
               notes=_fleet_notes("gapliq", "T1", fdr_real, c1, c2, c4, c5, c6, unit="points"))


# --------------------------------------------------------------------------------------------
# flatten U1
# --------------------------------------------------------------------------------------------

def _flatten_all_real(day, start_ts, end_ts):
    out = {}
    w = day[(day.index >= start_ts) & (day.index <= end_ts)]
    for name, sig_col, direction, kind, _entry_time in flatten.TRIALS:
        sig = w[w[sig_col]]
        elig_dates = sig.index[sig["elig"]]
        out[name] = dict(trades=flatten.build_trades(day, elig_dates, direction, kind),
                         sig_col=sig_col, direction=direction, kind=kind)
    return out


def score_flatten(frame, day, real, start_ts, end_ts, real_trials, delta):
    cost = flatten.COST1
    target = real[FLATTEN_TARGET]
    trades = inject_delta(target["trades"], delta)
    n = len(trades)
    net_pts = trades["pts"] - cost
    net_pct = trades["ret_pct"] - 100.0 * cost / trades["entry_px"]
    mean_net_pts = float(net_pts.mean()) if n else np.nan
    p_day = stats.one_sided_p(net_pct.to_numpy(), stats.day_blocks(trades["date"])) if n else np.nan
    ctrl = flatten.day_selection_control(day, start_ts, end_ts, target["direction"], cost, n)
    control_mean_pts = float(np.nanmean(ctrl)) if len(ctrl) else np.nan
    excess = (mean_net_pts - control_mean_pts) if (n and pd.notna(control_mean_pts)) else np.nan
    if n:
        flatten.timing_control(frame, day, trades["date"].to_numpy(), target["direction"], cost)  # re-run for
        # completeness (A50); real/unperturbed by construction; not a dedicated output column (see score_gapliq).
    sr_pool = [stats.per_trade_sharpe(_net_pct1(trades if name == FLATTEN_TARGET else info["trades"], cost))
              for name, info in real.items()]
    dsr = stats.deflated_sharpe(net_pct.to_numpy(), sr_trials=sr_pool, n=flatten.DSR_N)[0] if n >= 3 else np.nan
    fdr_real = _real_fdr(real_trials, "FLATTEN U1")
    c1 = bool(n and mean_net_pts > 0)
    c2 = bool(n and pd.notna(p_day) and p_day < 0.05)
    c3 = bool(fdr_real)
    c4 = bool(n and pd.notna(excess) and excess > 0)
    c5 = bool(n and pd.notna(dsr) and dsr > 0.95)
    c6 = bool(n >= 200)
    return dict(n=n, mean_net_pts=mean_net_pts, p_boot_day=p_day, excess_over_control_pct=excess, dsr=dsr,
               survives_all_six=(c1 and c2 and c3 and c4 and c5 and c6),
               notes=_fleet_notes("flatten", "U1", fdr_real, c1, c2, c4, c5, c6, unit="points"))


# --------------------------------------------------------------------------------------------
# fvg short|R1|bos_off
# --------------------------------------------------------------------------------------------

def _fvg_ctx(frame):
    """The REAL (unperturbed) HOLDOUT per-trade series for all 8 fvg trials (fvg.py's own
    build_bars/detect_side/simulate, called once and cached: simulate() is stateful per call but
    each (side,bos,R) combination is independent, exactly fvg.main()'s own loop), needed so the
    other 7 trials' real series can feed the target's DSR sr_pool."""
    bars = fvg.build_bars(frame)
    day_arrays = fvg.to_day_arrays(bars)
    setups_by_side = {side: fvg.detect_side(bars, side) for side in ("short", "long")}
    win_name, start, end = fvg.WINDOWS[2]
    assert win_name == "HOLDOUT", f"fvg.WINDOWS[2] is not HOLDOUT: {win_name!r}"
    start_ts, end_ts = pd.Timestamp(start), pd.Timestamp(end)
    real = {}
    for side in ("short", "long"):
        s_win = setups_by_side[side]
        s_win = s_win[(s_win["date"] >= start_ts) & (s_win["date"] <= end_ts)]
        for bos in ("on", "off"):
            s_bos = s_win[s_win["structure_break"]] if bos == "on" else s_win
            for r in (1, 2):
                trades, _counts = fvg.simulate(day_arrays, s_bos, side, r)
                real[(side, bos, r)] = dict(trades=trades, filled=trades[trades["filled"]].copy())
    return dict(day_arrays=day_arrays, start_ts=start_ts, end_ts=end_ts, real=real)


def score_fvg(ctx, real_trials, delta):
    day_arrays, real = ctx["day_arrays"], ctx["real"]
    cost = fvg.COST1
    side, bos, r = FVG_TARGET
    target = real[FVG_TARGET]
    filled = inject_delta(target["filled"], delta)
    n = len(filled)
    net_pts = filled["pts"] - cost
    net_pct = filled["ret_pct"] - 100.0 * cost / filled["entry_px"]
    mean_net_pts = float(net_pts.mean()) if n else np.nan
    p_day = stats.one_sided_p(net_pct.to_numpy(), stats.day_blocks(filled["date"])) if n else np.nan
    # random_entry_control reads only entry_px/stop_px (never pts/ret_pct), so the REAL `target["trades"]`
    # (unfilled rows included, as fvg.py's own caller passes) is real/unperturbed by construction.
    _ctrl_pct, ctrl_pts = fvg.random_entry_control(day_arrays, target["trades"], side, r, cost)
    control_mean_pts = float(np.nanmean(ctrl_pts)) if len(ctrl_pts) and np.isfinite(ctrl_pts).any() else np.nan
    excess = (mean_net_pts - control_mean_pts) if (n and pd.notna(control_mean_pts)) else np.nan
    sr_pool = []
    for key, info in real.items():
        f = filled if key == FVG_TARGET else info["filled"]
        sr_pool.append(stats.per_trade_sharpe(_net_pct1(f, cost)) if len(f) else np.nan)
    dsr = stats.deflated_sharpe(net_pct.to_numpy(), sr_trials=sr_pool, n=fvg.DSR_N)[0] if n >= 3 else np.nan
    fdr_real = _real_fdr(real_trials, "FVG short|R1|bos_off")
    c1 = bool(n and mean_net_pts > 0)
    c2 = bool(n and pd.notna(p_day) and p_day < 0.05)
    c3 = bool(fdr_real)
    c4 = bool(n and pd.notna(excess) and excess > 0)
    c5 = bool(n and pd.notna(dsr) and dsr > 0.95)
    c6 = bool(n >= 200)
    return dict(n=n, mean_net_pts=mean_net_pts, p_boot_day=p_day, excess_over_control_pct=excess, dsr=dsr,
               survives_all_six=(c1 and c2 and c3 and c4 and c5 and c6),
               notes=_fleet_notes("fvg", "short|R1|bos_off", fdr_real, c1, c2, c4, c5, c6, unit="points"))


# --------------------------------------------------------------------------------------------
# D1 winner: 15:00|both|vixmove_exp
# --------------------------------------------------------------------------------------------

def _d1_build(frame, vix, meta, td):
    """The REAL (unperturbed) full-history trade table for the D1 winner, via signals.py's own
    day_table/fixed_thresholds/candidate -- D1_WINNER is fixed by A50's enumerated scope (not
    re-derived from out/reconcile_decision.md, which may name a different winner on a later run;
    A50 names this exact candidate, not 'whichever D1 currently produces')."""
    day = signals.day_table(frame, vix, dividends=meta["dividends"] if meta else None,
                            trading_days=td, roll_dates=meta["roll_dates"] if meta else ())
    fixed = {e: signals.fixed_thresholds(day, e) for e in (900, 930)}
    e, d, g = insample.parse_label(D1_WINNER)
    trades_full = signals.candidate(day, e, d, g, fixed=fixed.get(e), name=D1_WINNER)
    return day, trades_full, e, d, g


def score_d1(frame, day, td, trades_win, e, d, g, start_ts, end_ts, real_trials, delta):
    cost = insample.COST_PTS
    tr = inject_delta(trades_win, delta)
    n = len(tr)
    net_pts = tr["pts"] - cost
    net_pct = tr["ret_pct"] - 100.0 * cost / tr["entry_px"]
    mean_net_pts = float(net_pts.mean()) if n else np.nan
    base = "prev_close" if g != "mag" else "open"
    ctrl = signals.day_selection_control(day.loc[start_ts:end_ts], tr, e, d if g != "gap" else "both", base=base) if n else np.array([])
    ctrl_net = (ctrl - 100.0 * cost / tr["entry_px"].mean()) if len(ctrl) else np.array([])
    excess = float(net_pct.mean() - ctrl_net.mean()) if len(ctrl_net) else np.nan
    p_month = stats.one_sided_p(net_pct.to_numpy(), stats.month_blocks(tr["date"])) if n else np.nan
    p_day = stats.one_sided_p(net_pct.to_numpy(), stats.day_blocks(tr["date"])) if n else np.nan
    psr = stats.deflated_sharpe(net_pct.to_numpy(), n=1)[0] if n >= 3 else np.nan
    if n:
        frame_window = frame[(frame["date"] >= start_ts) & (frame["date"] <= end_ts)]
        signals.timing_control(frame_window, tr, n_seeds=50)   # re-run for completeness (A50); real/unperturbed
        # by construction (reads r.exit_px, the REAL price -- never the injected pts/ret_pct columns); not a
        # dedicated output column (see score_gapliq).
    p_for_fdr_inj = p_month if pd.notna(p_month) else (p_day if pd.notna(p_day) else 1.0)
    fdr_pass = _d1_fdr_recompute(real_trials, p_for_fdr_inj)
    c1 = bool(n and mean_net_pts > 0)
    c2 = bool(n and pd.notna(p_month) and p_month < 0.05)
    c3 = bool(fdr_pass) if pd.notna(fdr_pass) else False
    c4 = bool(n and pd.notna(excess) and excess > 0)
    c5 = bool(n and pd.notna(psr) and psr > 0.95)
    c6 = bool(n >= 200)
    return dict(n=n, mean_net_pts=mean_net_pts, p_boot_day=p_day, excess_over_control_pct=excess, dsr=psr,
               survives_all_six=(c1 and c2 and c3 and c4 and c5 and c6),
               notes=_d1_notes(p_month, c1, c2, c4, c5, c6))


def main(inp, out):
    if inp != "extended":
        raise ValueError(f"pipeline.units.poscontrol only supports --in extended (got {inp!r})")
    td = sessions.trading_days_from_vix()
    frame, _dropped, meta = sessions.build_extended(trading_days=td)
    vix = pd.read_parquet("data/raw/vix_daily.parquet")

    gap_day = gapliq.build_day_table(frame, vix, meta, td)
    _gwn, gap_start, gap_end = gapliq.WINDOWS[2]
    assert _gwn == "HOLDOUT", f"gapliq.WINDOWS[2] is not HOLDOUT: {_gwn!r}"
    gap_start_ts, gap_end_ts = pd.Timestamp(gap_start), pd.Timestamp(gap_end)
    gap_real = _gapliq_all_real(gap_day, gap_start_ts, gap_end_ts)

    flat_day = flatten.build_day_table(frame, vix, meta, td)
    _fwn, flat_start, flat_end = flatten.WINDOWS[2]
    assert _fwn == "HOLDOUT", f"flatten.WINDOWS[2] is not HOLDOUT: {_fwn!r}"
    flat_start_ts, flat_end_ts = pd.Timestamp(flat_start), pd.Timestamp(flat_end)
    flat_real = _flatten_all_real(flat_day, flat_start_ts, flat_end_ts)

    fvg_ctx = _fvg_ctx(frame)

    d1_day, d1_trades_full, e, d, g = _d1_build(frame, vix, meta, td)
    d1_start_ts, d1_end_ts = pd.Timestamp(D1_START), pd.Timestamp(D1_END)
    d1_trades_win = d1_trades_full[(d1_trades_full["date"] >= d1_start_ts)
                                   & (d1_trades_full["date"] <= d1_end_ts)].reset_index(drop=True)

    real_trials = _read_csv_or_empty("out/trials.csv")
    power_df = _read_csv_or_empty("out/power_analysis.csv")

    specs = [
        ("gapliq", "T1", "HOLDOUT", lambda dl: score_gapliq(frame, gap_day, gap_real, gap_start_ts, gap_end_ts, real_trials, dl)),
        ("flatten", "U1", "HOLDOUT", lambda dl: score_flatten(frame, flat_day, flat_real, flat_start_ts, flat_end_ts, real_trials, dl)),
        ("fvg", "short|R1|bos_off", "HOLDOUT", lambda dl: score_fvg(fvg_ctx, real_trials, dl)),
        ("pre_registered", D1_WINNER, "HOLDOUT",
         lambda dl: score_d1(frame, d1_day, td, d1_trades_win, e, d, g, d1_start_ts, d1_end_ts, real_trials, dl)),
    ]
    rows = []
    for family, candidate, window, score_fn in specs:
        mde = _read_power_mde(power_df, family, window, candidate)
        mean0 = None
        for delta in DELTAS:
            r = score_fn(delta)
            if delta == 0.0:
                mean0 = r["mean_net_pts"]
            # identically 0 under the additive per-trade injection (A52.1): an arithmetic check, not evidence
            recovered_minus_delta = (r["mean_net_pts"] - mean0 - delta) if pd.notna(mean0) else np.nan
            rows.append(dict(candidate=candidate, family=family, window=window, delta=delta, n=r["n"],
                             mean_net_pts=r["mean_net_pts"], recovered_minus_delta=recovered_minus_delta,
                             p_boot_day=r["p_boot_day"], excess_over_control_pct=r["excess_over_control_pct"],
                             dsr=r["dsr"], survives_all_six=r["survives_all_six"],
                             theoretical_mde_at_n=mde, notes=r["notes"]))
    res = pd.DataFrame(rows, columns=OUT_COLS)
    res = res.sort_values(["family", "candidate", "window", "delta"]).reset_index(drop=True)
    res.to_csv(out, index=False, float_format="%.6f")
    print(res.to_string(index=False, float_format=lambda x: f"{x:.4f}"))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", default="extended")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    _gh.run(lambda: main(a.inp, a.out), a.out)
