"""A48 -- does a bounded exit make an already-registered candidate's question answerable? An
ANALYSIS of DISPERSION ONLY, not a trial. It adds ZERO trials, computes no new signal, opens no
new window, fits no parameter and can promote nothing; the family stays at 45
(ACCEPTANCE.md amendment A48).

    python -m pipeline.units.bexit --in extended --out out/bexit_detectability.csv

A47 showed the four hold-to-close, one-trade-per-day families cannot resolve a 1-2 point effect
at the survival rule's n=200 floor because their per-trade dispersion (21.9-50.9 pts) is far wider
than the one bounded-exit family already on the branch (`pipeline.units.fvg`, 4.4-7.2 pts). This
unit asks, for each of the 8 already-registered hold-to-close candidates (A39's T1/T2/T3, A46's
U1/U2/U3, and the two pre-registered signals), what its per-trade dispersion would be under a
bounded exit, and whether the resulting MDE would clear the 1-2 point cost band. It computes and
emits DISPERSION ONLY: standard deviation of per-trade net points, the implied MDE at the
observed n and at n=200, and the trade count -- NEVER a mean, a win rate, a Sharpe, a p-value, a
cumulative P&L or any other location/profitability statistic, for any candidate or exit rule,
anywhere in this module, not even as a discarded intermediate. Every candidate here has a KNOWN
holdout result (`out/gapliq_candidates.csv`, `out/flatten_candidates.csv`,
`out/holdout_summary.csv`); computing profitability under a new exit rule and then choosing among
the results would be a re-tune on the holdout, which the contract forbids (BLOCKED.md). Dispersion
is a second moment: it says which questions become ANSWERABLE, never which exit rule PAYS. `sd` is computed
with `np.std(..., ddof=1)` -- numpy materialises an average internally to do so, but this module
never names, keeps or emits one; `pipeline.units.test_bexit` source-scans this file for a short
list of forbidden profitability-statistic call/identifier patterns (a running total, a per-trade
success rate, a risk-adjusted-return ratio, an option-premium-return abbreviation) to enforce it
(A48's own requirement) -- deliberately not spelled out literally here, so this very sentence
cannot itself trip the scan it describes.

Trade universe -- reusing each candidate's own signal-day selection so the SAME trades are
evaluated, just with a different exit, via TWO routes (A48 offers both; this unit uses whichever
is the more direct read of each family's own published construction):
  * A39/A46 (gapliq/flatten): `gapliq.build_day_table`/`gapliq.build_trades` and
    `flatten.build_day_table`/`flatten.build_trades` are called DIRECTLY (the owning modules' own
    gate/day-table/trade construction, never re-derived) with each module's own `TRIALS`/`WINDOWS`
    tables, so entry time, exit time and direction are read from those constants, never hand-
    typed. The few lines selecting `elig_dates` per (window, trial) restate `summarize()`'s own
    window-filter/signal-column lines (unavoidable glue -- the gate itself, the expanding
    thresholds, live entirely inside `build_day_table`); `summarize()` itself is never called,
    since it also computes bootstrap p-values, DSR and an option-leg mean this unit must never
    touch.
  * The two pre-registered signals: read directly from `power.HOLDOUT_SIGNAL_FILES`
    (`out/holdout_d4_<name>_s1_cash_k1.0.csv`), the exact per-trade files `pipeline.units.power`
    already uses for this family -- these already carry `entry_mod`/`exit_mod`/`direction` per row
    (a real signal's fill drifts by a bar or two under A11), so no day-table reconstruction is
    needed. Only HOLDOUT exists for this family: `pipeline.insample` only ever prices the HOLDOUT
    window this way, so HOLDOUT is the only "already registered" per-trade series this family has
    -- not a cherry-pick, the only window available (A48: "windows as already registered").

Entry convention (which minute the position becomes live, hence where the intrabar walk starts):
gapliq/flatten enter at the CLOSE of a fixed bar (own docstrings, point 1) -- the walk starts at
the NEXT bar (`entry_mod + 1`); the pre-registered signals enter at the OPEN of the first bar
after the decision (A11, `signals._first_open_after`) -- the walk starts AT that same bar
(`entry_mod`), since the position is already live for its own range. Both conventions are each
family's own already-registered one, not invented here.

Exit grid (fixed by A48, not extended): stop and target placed symmetrically at
m * `pipeline.execution.atr_at_decision`'s own 5-minute/14-bar ATR proxy, for m in
{0.5, 1.0, 1.5, 2.0}, plus a fixed-points variant at {5, 10, 20} index points, walked over the
1-minute bars between the registered entry and the registered exit; whichever of stop/target is
touched first ends the trade; if neither is touched the registered exit stands. A bar whose range
contains BOTH triggers the STOP -- `pipeline/units/fvg.py`'s own `_walk_exit` convention
(same-bar stop+TP tie goes to the stop), reused here rather than invented, and the conservative
assumption on a book already governed by a strict daily loss limit (ACCEPTANCE.md's own "the
constraint that governs everything"): assuming the adverse outcome first cannot overstate
detectability, where assuming the favourable one first could. Costs 1.0/2.0 pts, as elsewhere;
`sd` is invariant to a constant cost shift, so `sd_net_pts_cost1` == `sd_net_pts_cost2` always --
both are still computed and emitted explicitly (never asserted equal and reused) because the
output spec (A48) names both columns.

IMPORTANT FINDING, stated up front rather than buried in a comment: A39's T1 (entry 10:00, mod
600) and T2 (entry 09:31, mod 571) always enter BEFORE `execution.atr_at_decision`'s 14-bar proxy
is available that session (first available at mod 640, i.e. ~10:40 ET, on every date checked --
14 five-minute bars from the 09:30 open) -- so does T3 (also 10:00 entry). Reusing
`execution.py`'s own convention (`avail_from <= decision_mod`, exactly `execution.limit_fills`'s
own `if usable.empty: continue`) rather than inventing a fallback, this means ALL of gapliq's
T1/T2/T3 have ZERO usable trades under EVERY m*ATR exit rule (n=0, so the group is SKIPPED, same
floor `pipeline.units.power.group_row` already uses for n<2) -- their FIXED-points exit rules
(5/10/20 pts, which need no ATR) are fully populated. A46's U1/U2/U3 (11:00 entry, mod 660) and
both pre-registered signals (13:00/15:00, well past mod 640) always have an ATR available. This is
a structural fact about `execution.py`'s own proxy applied to gapliq's early entries, not a bug in
this unit and not a cherry-pick (the same rule is applied uniformly to all 8 candidates).

Output columns, exactly and only: family, candidate, window, exit_rule, n, sd_net_pts_cost1,
sd_net_pts_cost2, mde_at_n, mde_at_200, answerable_at_n (mde_at_n <= 2.0, A48's own answer
condition). `mde` is `pipeline.units.power.mde` (z_0.95+z_0.80)*sd/sqrt(n) -- imported, not
re-derived. A `("<candidate>", "<window>", "registered")` row per candidate/window carries the
hold-to-close dispersion (built directly from the same `pts` array published elsewhere, so it
reproduces `out/power_analysis.csv`'s own sd figures, e.g. flatten HOLDOUT U1 sd 44.6991, gapliq
HOLDOUT T2 sd 50.8580 -- `test_bexit.py` pins this), so the comparison against the bounded-exit
grid is visible in the same table.

Rows are emitted in each family's own pre-registered order (gapliq's T1/T2/T3 x its own CONTEXT/
SELECTION/HOLDOUT window order, then flatten's U1/U2/U3 x the same window order, then the two
pre-registered signals in `power.HOLDOUT_SIGNAL_FILES`'s own listed order), each with the fixed
exit-rule grid order (registered, then the ATR multiples ascending, then the fixed-points grid
ascending) -- fully deterministic (no randomness, no clock), and a more direct audit trail against
each candidate's own pre-registration than an alphabetical re-sort would be.

On failure (an unexpected exception) this unit follows `pipeline.units._gh.run` exactly as
power.py/flatten.py/gapliq.py do: an empty (zero-byte) output file plus `<out>.error` with the
traceback, exit code 2 (A32).
"""
import argparse
import os

import numpy as np
import pandas as pd

from pipeline import execution, sessions
from pipeline.units import _gh, flatten, gapliq, power

ATR_MULTS = (0.5, 1.0, 1.5, 2.0)     # A48's own grid, symmetric stop/target at m x the ATR proxy
FIXED_GRID = (5.0, 10.0, 20.0)        # A48's own grid, symmetric stop/target at fixed index points
MDE_ANSWERABLE = 2.0                  # A48's own answer condition: mde_at_n <= 2.0 pts
OUT_COLS = ["family", "candidate", "window", "exit_rule", "n", "sd_net_pts_cost1", "sd_net_pts_cost2",
            "mde_at_n", "mde_at_200", "answerable_at_n"]
TG_COLS = ["date", "entry_px", "exit_px", "direction", "entry_mod", "exit_mod", "pts"]


def _minute_bars_by_date(frame):
    """date -> {mod, high, low} numpy arrays (sorted by mod) from the same 1-minute extended
    frame every owning module already builds (`sessions.build_extended`) -- the intrabar
    stop/target walk below never re-derives its own bar frame."""
    out = {}
    for d, g in frame.groupby("date"):
        g = g.sort_values("mod")
        out[d] = dict(mod=g["mod"].to_numpy(), high=g["high"].to_numpy(float), low=g["low"].to_numpy(float))
    return out


def _atr_lookup(frame):
    """date -> (avail_from, atr) sorted arrays, atr non-NaN only -- `pipeline.execution`'s own
    5-minute/14-bar ATR proxy (`execution.atr_at_decision`), never re-derived (A48: "reuse the ATR
    proxy already used by pipeline/execution.py")."""
    tab = execution.atr_at_decision(frame).dropna(subset=["atr"])
    out = {}
    for d, g in tab.groupby("date"):
        g = g.sort_values("avail_from")
        out[d] = (g["avail_from"].to_numpy(), g["atr"].to_numpy(float))
    return out


def _atr_at(atr_lookup, date, mod):
    """Last ATR value available at or before `mod` on `date` -- `execution.py`'s own
    `avail_from <= decision_mod` gate; NaN if none is available yet that session (see module
    docstring's "IMPORTANT FINDING" -- a 09:31/10:00 entry is always before the proxy's first
    availability at mod 640)."""
    pair = atr_lookup.get(pd.Timestamp(date))
    if pair is None:
        return np.nan
    avail, atr = pair
    ok = avail <= mod
    return float(atr[ok][-1]) if ok.any() else np.nan


def walk_bounded_exit(bars, start_mod, end_mod, entry_px, direction, dist, registered_exit_px):
    """Net points (BEFORE cost) for one trade under one bounded-exit rule: stop/target placed at
    entry_px -/+ direction*dist, walked over 1-minute bars in [start_mod, end_mod] (inclusive);
    whichever triggers first ends the trade; a bar touching BOTH triggers the STOP
    (`pipeline/units/fvg.py`'s own `_walk_exit` convention, see module docstring); if neither
    triggers, `registered_exit_px` stands. `bars` is one date's {mod, high, low} arrays
    (`_minute_bars_by_date`). Pure function of its arguments -- directly unit-testable on a
    synthetic path (`test_bexit.py` checks (c)/(d))."""
    stop_px = entry_px - direction * dist
    tp_px = entry_px + direction * dist
    mod, high, low = bars["mod"], bars["high"], bars["low"]
    sel = (mod >= start_mod) & (mod <= end_mod)
    h, l = high[sel], low[sel]
    if direction > 0:
        stop_hit, tp_hit = l <= stop_px, h >= tp_px
    else:
        stop_hit, tp_hit = h >= stop_px, l <= tp_px
    hit = stop_hit | tp_hit
    if hit.any():
        pos = int(np.argmax(hit))
        exit_px = stop_px if stop_hit[pos] else tp_px
    else:
        exit_px = registered_exit_px
    return direction * (exit_px - entry_px)


def _gapliq_groups(frame, vix, meta, td):
    """(family, candidate, window, trades) for A39's T1/T2/T3, built by calling
    `gapliq.build_day_table`/`gapliq.build_trades` directly -- entry time, exit time and
    direction all come from `gapliq.TRIALS`/`gapliq.WINDOWS`, never hand-typed."""
    day = gapliq.build_day_table(frame, vix, meta, td)
    for win_name, start, end in gapliq.WINDOWS:
        start_ts, end_ts = pd.Timestamp(start), pd.Timestamp(end)
        w = day[(day.index >= start_ts) & (day.index <= end_ts)]
        for name, sig_col, entry_col, direction, kind, _entry_time in gapliq.TRIALS:
            sig = w[w[sig_col]]
            elig_dates = sig.index[sig["both_bars"]]     # gapliq.summarize's own eligibility gate
            tr = gapliq.build_trades(day, elig_dates, entry_col, direction, kind)
            tg = pd.DataFrame(dict(date=tr["date"], entry_px=tr["entry_px"], exit_px=tr["exit_px"],
                                   direction=direction, entry_mod=tr["entry_mod"], exit_mod=tr["exit_mod"],
                                   pts=tr["pts"]))[TG_COLS]
            yield "gapliq", name, win_name, tg


def _flatten_groups(frame, vix, meta, td):
    """(family, candidate, window, trades) for A46's U1/U2/U3, built by calling
    `flatten.build_day_table`/`flatten.build_trades` directly -- entry time, exit time and
    direction all come from `flatten.TRIALS`/`flatten.WINDOWS`, never hand-typed."""
    day = flatten.build_day_table(frame, vix, meta, td)
    for win_name, start, end in flatten.WINDOWS:
        start_ts, end_ts = pd.Timestamp(start), pd.Timestamp(end)
        w = day[(day.index >= start_ts) & (day.index <= end_ts)]
        for name, sig_col, direction, kind, _entry_time in flatten.TRIALS:
            sig = w[w[sig_col]]
            elig_dates = sig.index[sig["elig"]]          # flatten.summarize's own eligibility gate
            tr = flatten.build_trades(day, elig_dates, direction, kind)
            tg = pd.DataFrame(dict(date=tr["date"], entry_px=tr["entry_px"], exit_px=tr["exit_px"],
                                   direction=direction, entry_mod=tr["entry_mod"], exit_mod=tr["exit_mod"],
                                   pts=tr["pts"]))[TG_COLS]
            yield "flatten", name, win_name, tg


def _read_csv_or_empty(path):
    """`path` as a DataFrame, or an empty DataFrame when there is no usable row -- the same guard
    `pipeline.units.power._read_csv_or_empty` uses, restated here rather than importing a sibling
    unit's private helper (power.py's own docstring: this guard is kept local to each unit)."""
    if not os.path.exists(path) or os.path.getsize(path) == 0:
        return pd.DataFrame()
    try:
        return pd.read_csv(path)
    except pd.errors.EmptyDataError:
        return pd.DataFrame()


def _pre_registered_groups():
    """(family, candidate, "HOLDOUT", trades) for D1's winner and Thread A's gap-up call, read
    directly from `power.HOLDOUT_SIGNAL_FILES` -- these per-trade files already carry
    entry_mod/exit_mod/direction per row (a real fill drifts by a bar or two, A11), so no
    day-table reconstruction is needed here. Only HOLDOUT exists for this family (see module
    docstring)."""
    for path in power.HOLDOUT_SIGNAL_FILES:
        df = _read_csv_or_empty(path)
        if not len(df):
            continue
        name = df["candidate"].iloc[0]
        tg = pd.DataFrame(dict(date=pd.to_datetime(df["date"]), entry_px=df["entry_px"], exit_px=df["exit_px"],
                               direction=df["direction"].astype(float), entry_mod=df["entry_mod"].astype(int),
                               exit_mod=df["exit_mod"].astype(int), pts=df["pts"]))[TG_COLS]
        yield "pre_registered", name, "HOLDOUT", tg


def _dispersion_row(family, candidate, window, exit_rule, raw_pts):
    """One output row for a (family, candidate, window, exit_rule) group of per-trade RAW
    (before-cost) points, or None if n < 2 (a sample sd needs n >= 2 -- same floor
    `power.group_row` uses; an exit rule with zero usable trades, e.g. gapliq's ATR grid, see
    module docstring, is SKIPPED, never emitted with a fabricated sd). Computes `sd` via
    `np.std(..., ddof=1)` only -- no mean, win rate or any other location statistic is named,
    kept or returned (A48)."""
    n = len(raw_pts)
    if n < 2:
        return None
    net1 = raw_pts - power.COST1
    net2 = raw_pts - power.COST2
    sd1 = float(np.std(net1, ddof=1))
    sd2 = float(np.std(net2, ddof=1))     # == sd1 always (sd is invariant to a constant shift);
                                           # both computed explicitly since the output spec names both columns
    mde_n = power.mde(sd1, n)
    mde_200 = power.mde(sd1, power.N_FLOOR)
    return dict(family=family, candidate=candidate, window=window, exit_rule=exit_rule, n=n,
                sd_net_pts_cost1=sd1, sd_net_pts_cost2=sd2, mde_at_n=mde_n, mde_at_200=mde_200,
                answerable_at_n=bool(mde_n <= MDE_ANSWERABLE))


def group_rows(family, candidate, window, tg, entry_is_close, day_bars, atr_lookup):
    """Every exit-rule row for one (family, candidate, window) trade group: the registered
    baseline (the group's own already-published `pts`, direction-adjusted, no walk needed) plus
    the bounded-exit grid (ATR_MULTS then FIXED_GRID, A48's own fixed grid). `entry_is_close`
    selects each family's own already-registered entry convention (module docstring): True
    (gapliq/flatten, entry at a bar's CLOSE) walks from `entry_mod + 1`; False (the pre-registered
    signals, entry at a bar's OPEN, A11) walks from `entry_mod` itself."""
    rows = []
    offset = 1 if entry_is_close else 0
    dates = pd.to_datetime(tg["date"]).to_numpy()
    entry_px = tg["entry_px"].to_numpy(float)
    exit_px = tg["exit_px"].to_numpy(float)
    direction = tg["direction"].to_numpy(float)
    entry_mod = tg["entry_mod"].to_numpy(int)
    exit_mod = tg["exit_mod"].to_numpy(int)

    row = _dispersion_row(family, candidate, window, "registered", tg["pts"].to_numpy(float))
    if row is not None:
        rows.append(row)

    for m in ATR_MULTS:
        out = []
        for i in range(len(tg)):
            date_i = pd.Timestamp(dates[i])
            atr = _atr_at(atr_lookup, date_i, int(entry_mod[i]))
            bars = day_bars.get(date_i)
            if np.isnan(atr) or bars is None:
                continue        # no ATR available at entry yet, or no bar frame for this date (see docstring)
            out.append(walk_bounded_exit(bars, int(entry_mod[i]) + offset, int(exit_mod[i]),
                                         entry_px[i], direction[i], m * atr, exit_px[i]))
        row = _dispersion_row(family, candidate, window, f"atr{m:.1f}x", np.asarray(out, dtype=float))
        if row is not None:
            rows.append(row)

    for p in FIXED_GRID:
        out = []
        for i in range(len(tg)):
            date_i = pd.Timestamp(dates[i])
            bars = day_bars.get(date_i)
            if bars is None:
                continue
            out.append(walk_bounded_exit(bars, int(entry_mod[i]) + offset, int(exit_mod[i]),
                                         entry_px[i], direction[i], float(p), exit_px[i]))
        row = _dispersion_row(family, candidate, window, f"fixed{int(p)}pts", np.asarray(out, dtype=float))
        if row is not None:
            rows.append(row)
    return rows


def main(inp, out):
    if inp != "extended":
        raise ValueError(f"pipeline.units.bexit only supports --in extended (got {inp!r})")
    td = sessions.trading_days_from_vix()
    frame, _dropped, meta = sessions.build_extended(trading_days=td)
    vix = pd.read_parquet("data/raw/vix_daily.parquet")
    day_bars = _minute_bars_by_date(frame)
    atr_lookup = _atr_lookup(frame)

    rows = []
    for family, candidate, window, tg in _gapliq_groups(frame, vix, meta, td):
        rows.extend(group_rows(family, candidate, window, tg, True, day_bars, atr_lookup))
    for family, candidate, window, tg in _flatten_groups(frame, vix, meta, td):
        rows.extend(group_rows(family, candidate, window, tg, True, day_bars, atr_lookup))
    for family, candidate, window, tg in _pre_registered_groups():
        rows.extend(group_rows(family, candidate, window, tg, False, day_bars, atr_lookup))

    res = pd.DataFrame(rows, columns=OUT_COLS)   # already in deterministic order (module docstring)
    res.to_csv(out, index=False, float_format="%.6f")
    print(res.to_string(index=False, float_format=lambda x: f"{x:.4f}"))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", default="extended")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    _gh.run(lambda: main(a.inp, a.out), a.out)
