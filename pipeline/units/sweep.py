"""Track B, step B2 — causal swing-sweep REVERSAL/CONTINUATION family on range bars (A40, owner's
request 2026-09-13 12:26 UTC, pre-registered before any run; NOT tuned to look good).

    python -m pipeline.units.sweep --in extended --out out/trackB_sweep_candidates.csv

Reads the range-bar caches `pipeline.units.rangebars` writes (data/raw/trackB_spy_r034.parquet,
data/raw/trackB_spy_r100.parquet); does not rebuild bars itself.

Family (A40): type {reversal, continuation} x L {10, 20} x R {1, 2} x series {SPY $0.34,
SPY $1.00, XAUUSD $5} = 24 trials, all counted, none dropped, FDR-controlled on its own (a
family separate from Track A's). Gold is now ENABLED (A40c, mid-run re-registration, before any
gold row existed): `SERIES` below lists all three series, and both the SPY and the gold trials run
in this pass. Gold's own TRAIN/TEST are both rebuilds of the 2006-03..2020-05 Oanda XAU_USD minute
source found under A40b (`pipeline.units.rangebars`'s `build_range_bars_gold`,
`data/raw/trackB_xau_r5.parquet`) -- A40c replaced A40b's plan to use the owner's untouched 5000R
file as TEST, because no minute source overlaps it (A40b's own finding: "no overlap exists between
the two sources"); the owner's 5000R export is therefore CONTEXT ONLY from here on (never read by
this unit) and gold's own decision (below) is taken exactly like SPY's, on a TRAIN/TEST rebuilt the
same way. `DSR_N`/the `dsr_N24` column name and the decision rule's `N = 24` were always the
PRE-REGISTERED family size (A40b) and now literally equal the number of trials this run evaluates
(3 series x 8 trials/series = 24). `out/trackB_trials.csv`'s BH-FDR is computed over every TEST row
that exists in this run -- now the full 24-row family, both instruments together (A40b: "Gold and
SPY are decided separately (different instruments, same family for FDR)"); this is stated again at
that column's construction below.

Causal swing level (A40, literal): prior swing high at bar t = max(high) over the L bars STRICTLY
BEFORE t (bars[t-L..t-1]), excluding bar t itself; prior swing low symmetric. Computed with
`.shift(1).rolling(L)` so bar t's own high/low can never leak into its own reference level. The
rolling window runs CONTINUOUSLY across the whole multi-year bar series for a given (series, L) --
NOT reset at session boundaries -- because range bars are event-driven, not time-driven, and A40
gives no session-reset rule for the ANALYSIS (only the BUILD, in rangebars.py, resets at sessions);
a session's last, "partial" bar (rangebars.py) is a real, if early, price and is kept in this
series with no special treatment, both as a possible swing extreme and as a possible signal bar --
excluding it would also silently remove the causal predecessor of the next session's first bars.

Signals (bar-close decisions, fill at the NEXT bar's open -- always filled, unlike a limit order:
there is no "unfilled" case here). Side is NOT a family dimension (A40 states both directions
inside ONE trial definition, unlike e.g. fvg.py's family); each trial's signal set includes BOTH
directions, with ONE busy-until tracker PER DIRECTION (a short and a long may be open at the same
time; two shorts, or two longs, may not) -- "a pattern detected while its own side is already
occupied is skipped, not queued" (this codebase's precedent, fvg.py's SPEC_NOTE, generalised here
from one side to two independent trackers). The busy-until trackers, like the swing levels, run
CONTINUOUSLY across the whole series (not reset at the TRAIN/TEST window boundary): a trial is
simulated ONCE, in full, then its resulting trade table is split into TRAIN/TEST by each trade's
SIGNAL bar's ts_close (the bar-close decision moment; A40: "all bar-close decisions"). A trade
whose entry lands inside one window can still be exited using real bars after that window's end
(this only affects which window's REPORTED row counts the trade, never whether the trade exists
or what data resolves it -- consistent with how every other unit in this codebase treats a
reporting window as a filter on the signal date, not a wall on the data).
  REVERSAL: high[t] > prior_swing_high[t] AND close[t] < prior_swing_high[t] -> short (stop = the
    sweep extreme = high[t]); low[t] < prior_swing_low[t] AND close[t] > prior_swing_low[t] ->
    long (stop = the sweep extreme = low[t]).
  CONTINUATION: close[t] > prior_swing_high[t] -> long (stop = the broken level = prior_swing_high
    [t]); close[t] < prior_swing_low[t] -> short (stop = the broken level = prior_swing_low[t]).
Entry = the next bar's open; risk = |entry - stop|; target = entry +/- R * risk; time stop = 50
BARS, counting the entry bar itself as bar 1 of the hold (i.e. the walk checks the entry bar's own
high/low first, then up to 49 more bars); a stop/target touch in the SAME bar is resolved to the
STOP (this codebase's precedent, fvg.py/gapliq.py's `_walk_exit`, absent any A40 tie-break rule);
running out of the 50-bar window with neither touched exits at that 50th bar's close (exit_reason
"time_stop"); running out of DATA first (near the very end of the cached series) exits at the last
available bar's close instead ("end_of_data", a data-boundary artefact, not a genuine time stop).
Trade P&L / calendar attribution uses the ENTRY bar's session_date (the day capital was risked;
also the only choice that is always guaranteed inside the trade's own reporting window -- a 50-bar
hold can span many calendar days, or even weeks for the R=1.00 series, so the EXIT date routinely
falls outside the window's own calendar and broke `stats.calendar_day_sharpe`'s fixed-calendar
zero-fill on a real run, see also the defensive union below); this is the `date` column read by
the calendar-day Sharpe and both bootstrap p's.

Costs: SPY 2 bp/side, XAUUSD 1 bp/side (dormant, see above) -- round trip = 2 sides, so
cost_pct1 = 2 x bp_per_side x 0.01 (e.g. SPY: 2 x 2.0 x 0.01 = 0.04%); cost_pct2 = 2 x cost_pct1.
`win` is the GROSS (pre-cost) win rate (this codebase's precedent, fvg.py's `win` column).

Windows: SPY TRAIN 2020-07-27..2023-06-30, TEST 2023-07-01..2026-09-11 (`SPY_WINDOWS`, A40,
shared by both SPY series this run); XAUUSD TRAIN 2006-03-19..2016-12-31, TEST
2017-01-01..2020-05-14 (`XAU_WINDOWS`, A40c -- replaces A40b's original 2025-06..2026-03-18 TEST
window built from the owner's file, since gold TEST must also be a minute-data rebuild, per
A40c's own text). DSR's per-window SR0 pool spans EVERY trial evaluated in THIS run for that
window (all series together, since `series` is itself a family dimension, exactly mirroring
fvg.py's/gapliq.py's own precedent of pooling every trial the standalone unit can see) -- with
gold now enabled, that pool is all 24 trials' (16 SPY + 8 gold) per-trade Sharpes in that window,
matching `DSR_N`'s pre-registered N=24 exactly (state per the task brief: DSR at N=24 now uses
the per-trade-Sharpe dispersion of all 24 trials, not just SPY's 16).

Random-entry control (A40, "same stop/target structure", 200 seeds, seed 11): for the matched
window's real trades, 200 draws from ONE seeded generator (seed 11 -- this codebase's precedent
for controls this brief itself names a seed for, e.g. gapliq.py's day-selection control), drawn
WITHOUT replacement from every bar in that window whose ts_close falls in it (population is tens
of thousands of bars, always far larger than the trade count this run); a control "trade" opens at
that random bar's OWN open, uses the SAME direction, the SAME stop distance (price units) and the
SAME R as its matched real trade, and is walked through the identical stop/target/50-bar-time-stop
machinery; evaluated at cost1 only (fvg.py's precedent: the control is not swept at 2x cost).
`expected_rw_win` = 1/(1+R) (stop/(stop+target) for an unbiased random walk with a stop 1R away and
a target R away) is a pure arithmetic sanity check, reported beside the MEASURED `control_win`, not
a substitute for it -- the survival condition (below) uses the measured `control_net_pct`.

Rows (one per series x trial x window): series, trial (`{type}|L{L}|R{R}`), type, L, R, window, n,
win, net_pct_cost1, net_pct_cost2, mean_bars_held, sharpe_calday, p_boot_day, p_boot_month (NaN
below 20 month blocks -- `stats.one_sided_p`'s own floor, A26), control_win, control_net_pct,
frac_seeds_beaten, expected_rw_win, dsr_N24, spec.

Decision (pre-registered, A40; per-instrument split per A40b): SPY and gold are decided
SEPARATELY -- two calls to `decide()`, one per instrument, each restricted to that instrument's
own series/trials, sharing the SAME already-computed `fdr_pass_10pct` column (the 24-row family is
one BH-FDR run; only the winner-selection and the other five conditions are per-instrument). For
each instrument: on that instrument's own TRAIN rows, among trials with n >= 100, pick the single
highest `sharpe_calday` (ties broken by original (type, L, R) enumeration order -- A40 gives Track
B no tie-break rule of its own, unlike D1's explicit one; this is the conservative default). On
TEST, that SAME (series, trial) is checked against all six conditions: net_pct_cost1 > 0,
p_boot_day < 0.05, BH-FDR pass at 10% within the TEST-row family (all 24 rows, both instruments),
net_pct_cost1 > control_net_pct, dsr_N24 > 0.95, n >= 200. n < 200 forces verdict UNDERPOWERED
regardless of the other five (ACCEPTANCE's own convention: "Below 200 holdout trades ... label
UNDERPOWERED" -- A40b: "XAUUSD is reported under the same rule and labelled UNDERPOWERED where
n < 200"); otherwise SURVIVES iff all six hold, else FAILED. Written to `out/trackB_decision.csv`,
one row per instrument (`instrument` column: SPY / XAU).

Pattern table (`out/trackB_pattern_table.csv`, A40: "the pattern table the owner asked for ...
measured even when no trade survives costs"): for each series and L (SPY and, now enabled, gold),
the next
1/5/20-bar return after (a) a REVERSAL-shaped sweep, (b) a CONTINUATION-shaped close-through, (c)
unconditional (every bar) -- a pure census over EVERY qualifying bar (no busy-until gating, no R,
no cost: this is a pattern-frequency question, not a trading simulation) pooling the WHOLE cached
window (TRAIN+TEST together -- A40 does not window-split the pattern table, unlike the trial rows).
LONG format (one row per series x L x horizon x pattern) rather than wide, for readability and so
`pipeline.report_b`'s table helper renders it directly. Groups (a)/(b) fold both directions of
their pattern into ONE hypothesis-signed number (direction = -1 for the short-shaped instance, +1
for the long-shaped instance -- summed naively the two would cancel toward zero and hide the very
effect being measured); group (c) is left UN-signed (direction always +1, i.e. the series' own raw
per-bar drift) since an unconditional bar has no hypothesised direction to sign it by -- this is an
event-study-style framing (compare the hypothesis-direction move after a pattern against the
series' typical, undirected move) chosen because A40 does not specify a >2-group directional
pattern-table's exact mechanics; `p_vs_unconditional` (day-block bootstrap, two-sided, then Thread
B's one-sided halving) tests whether (a)'s or (b)'s mean differs from (c)'s, generalising
`stats.block_bootstrap_p`'s single-sample per-group-mean-centred null to two INDEPENDENT samples
(Var(A-C) = Var(A) + Var(C) for independent A, C) -- see `_two_sample_boot_p` below; NaN for the
`pattern == "unconditional"` rows themselves (nothing to compare it to) and below 20 day blocks in
either group.

Exception handling for THIS unit only (A40's item 2, explicitly DIFFERENT from the fleet's usual
A32 default that `pipeline.units._gh.run` implements for fvg.py/gapliq.py/rangebars.py): on any
exception, every output this unit writes is replaced by a HEADER-ONLY csv (never a literally empty
file) and the process exits 0, not 2 -- so a benign "no signals in some corner of the family"
outcome is published as an honest, empty result table instead of tripping `run_all`'s fleet-wide
*.error scan (which globs `out/*.error` regardless of which step produced it).

Determinism: every random draw is from a freshly-seeded generator (seed 11, this unit's own
`CONTROL_SEED`/`stats.SEED`); iteration order is fixed (module-level constant lists); two runs are
byte-identical (`out/*.csv` written with a fixed float_format, no wall-clock or PID in any output).
"""
import argparse
import os
import sys
import traceback

import numpy as np
import pandas as pd

from pipeline import stats
from pipeline.units import _gh

SERIES_CACHE = {"spy034": "data/raw/trackB_spy_r034.parquet", "spy100": "data/raw/trackB_spy_r100.parquet",
                 "xau5": "data/raw/trackB_xau_r5.parquet"}
R_SIZE = {"spy034": 0.34, "spy100": 1.00, "xau5": 5.0}
COST_BP_SIDE = {"spy034": 2.0, "spy100": 2.0, "xau5": 1.0}
# A40c (2026-09-13, mid-run re-registration, before any gold row existed): gold ENABLED -- both
# TRAIN and TEST are rebuilds of the 2006-2020 Oanda XAU_USD minute source
# (`pipeline.units.rangebars.build_range_bars_gold`, data/raw/trackB_xau_r5.parquet); the owner's
# 5000R file is context only from here on (never read by this unit).
SERIES = ["spy034", "spy100", "xau5"]
INSTRUMENT_SERIES = {"SPY": ["spy034", "spy100"], "XAU": ["xau5"]}   # A40b: decided separately per instrument

TYPES = ["reversal", "continuation"]
L_VALUES = [10, 20]
R_VALUES = [1, 2]
TIME_STOP_BARS = 50
N_SEEDS = 200
CONTROL_SEED = stats.SEED   # 11, per A40's own text ("200 seeds, seed 11")
DSR_N = 24                  # pre-registered family size (A40b); this run's pool is now all 24 trials
SPY_WINDOWS = [("TRAIN", "2020-07-27", "2023-06-30"), ("TEST", "2023-07-01", "2026-09-11")]
XAU_WINDOWS = [("TRAIN", "2006-03-19", "2016-12-31"), ("TEST", "2017-01-01", "2020-05-14")]  # A40c
WINDOWS_BY_SERIES = {"spy034": SPY_WINDOWS, "spy100": SPY_WINDOWS, "xau5": XAU_WINDOWS}
HORIZONS = [1, 5, 20]

TRADES_OUT = "out/trackB_sweep_trades.csv"    # fixed literal name (the brief's, not derived from --out)
OUT_COLS = ["series", "trial", "type", "L", "R", "window", "n", "win", "net_pct_cost1", "net_pct_cost2",
            "mean_bars_held", "sharpe_calday", "p_boot_day", "p_boot_month", "control_win",
            "control_net_pct", "frac_seeds_beaten", "expected_rw_win", "dsr_N24", "spec"]
TEST_COLS = OUT_COLS[:-1] + ["fdr_pass_10pct", "spec"]
TRADE_COLS = ["series", "trial", "window", "date", "direction", "entry_ts", "entry_px", "exit_ts",
              "exit_px", "exit_reason", "bars_held", "gross_ret_pct", "net_pct_cost1", "stop_px", "tp_px"]
DECISION_COLS = ["instrument", "winner_series", "winner_trial", "winner_type", "winner_L", "winner_R",
                  "train_n", "train_sharpe_calday", "test_n", "test_net_pct_cost1", "test_p_boot_day",
                  "test_control_net_pct", "test_dsr_N24", "cond_net_pos", "cond_p_boot_day",
                  "cond_fdr_pass_10pct", "cond_beats_control", "cond_dsr_gt_095", "cond_n_ge_200",
                  "verdict", "spec"]
PATTERN_COLS = ["series", "L", "horizon", "pattern", "n", "mean_range", "median_range", "mean_pct",
                 "median_pct", "p_vs_unconditional"]

SPEC_NOTE = (
    "FIXED (pre-registration, A40; gold ENABLED per A40c re-registration 2026-09-13, before any "
    "gold row existed -- all 24 trials run: 16 SPY + 8 XAU). Causal swing: prior swing "
    "high/low = rolling max/min of the L bars strictly before bar t (shift(1) then rolling(L)), "
    "computed continuously across the whole series (no session reset -- range bars are event-"
    "driven; only the BUILD resets at sessions). REVERSAL: high>prior_high & close<prior_high -> "
    "short (stop=high[t]); low<prior_low & close>prior_low -> long (stop=low[t]). CONTINUATION: "
    "close>prior_high -> long (stop=prior_high[t]); close<prior_low -> short (stop=prior_low[t]). "
    "Side is not a family dimension; one busy-until tracker per direction, continuous across the "
    "whole series (trades are simulated once, then split TRAIN/TEST by the SIGNAL bar's ts_close). "
    "Entry = next bar's open (always filled); target = entry +/- R*|entry-stop|; time stop 50 bars "
    "counting the entry bar as bar 1; a same-bar stop/target tie goes to the stop; P&L/calendar "
    "attribution uses the ENTRY bar's date (always inside the trade's own window; a multi-day hold's "
    "exit date routinely is not). Costs: SPY 2bp/side, XAU 1bp/side, round trip = 2 sides; "
    "cost2 = 2x cost1. Random-entry control: 200 draws from one generator seeded 11, without "
    "replacement, from the SAME window's bars, same direction/stop-distance/R as the matched real "
    "trade, net of cost1 only. DSR at N=24 uses the per-trade-Sharpe dispersion of ALL 24 TRIALS "
    "(16 SPY + 8 gold) in the same window as SR0's pool -- N=24 is both the pre-registered family "
    "size and, now that gold is enabled, the exact size of the pool. Windows: SPY TRAIN "
    "2020-07-27..2023-06-30, TEST 2023-07-01..2026-09-11; XAU TRAIN 2006-03-19..2016-12-31, TEST "
    "2017-01-01..2020-05-14 (A40c, both rebuilt from minute data, same rule as SPY). Decision: "
    "SPY and gold decided SEPARATELY (A40b) -- on each instrument's own TRAIN, winner = highest "
    "sharpe_calday among n>=100 trials; TEST verdict = SURVIVES iff net_pct_cost1>0 & p_boot_day<"
    "0.05 & BH-FDR pass @10% (the full 24-row TEST family, both instruments) & "
    "net_pct_cost1>control_net_pct & dsr_N24>0.95 & n>=200; n<200 forces UNDERPOWERED regardless "
    "of the other five. Exception handling for this unit only: header-only outputs, exit 0 (not "
    "_gh.run's usual empty-file/exit 2 -- see module docstring).")


def add_swing_levels(bars, L):
    prior_high = bars["high"].shift(1).rolling(L, min_periods=L).max()
    prior_low = bars["low"].shift(1).rolling(L, min_periods=L).min()
    return prior_high, prior_low


def detect_signals(bars, kind, L):
    """One row per qualifying bar-close pattern, BOTH directions together (side is a column, not
    a trial dimension -- see module docstring). direction: +1 long / -1 short; stop_px per the
    module docstring's REVERSAL/CONTINUATION definitions."""
    prior_high, prior_low = add_swing_levels(bars, L)
    high, low, close = bars["high"], bars["low"], bars["close"]
    ok = prior_high.notna() & prior_low.notna()
    if kind == "reversal":
        short = ok & (high > prior_high) & (close < prior_high)
        long_ = ok & (low < prior_low) & (close > prior_low)
        stop_short, stop_long = high, low
    else:
        short = ok & (close < prior_low)
        long_ = ok & (close > prior_high)
        stop_short, stop_long = prior_low, prior_high
    g = np.arange(len(bars))
    out_short = pd.DataFrame(dict(g_idx=g[short.to_numpy()], direction=-1, stop_px=stop_short[short].to_numpy()))
    out_long = pd.DataFrame(dict(g_idx=g[long_.to_numpy()], direction=1, stop_px=stop_long[long_].to_numpy()))
    return pd.concat([out_short, out_long], ignore_index=True).sort_values("g_idx").reset_index(drop=True)


def _walk_exit(high, low, close, entry_idx, stop_px, tp_px, direction, max_bars=TIME_STOP_BARS):
    """First bar at/after `entry_idx` (inclusive -- the entry bar itself is bar 1 of the hold)
    whose range touches stop_px or tp_px (stop wins a same-bar tie), within `max_bars`; else the
    close of the last bar in that window ("time_stop"), or of the last bar in the data if the
    series itself runs out first ("end_of_data"). Returns (exit_idx, exit_px, exit_reason)."""
    n = len(high)
    end_idx = min(entry_idx + max_bars - 1, n - 1)
    for i in range(entry_idx, end_idx + 1):
        if direction > 0:
            stop_hit, tp_hit = low[i] <= stop_px, high[i] >= tp_px
        else:
            stop_hit, tp_hit = high[i] >= stop_px, low[i] <= tp_px
        if stop_hit or tp_hit:
            return i, (stop_px if stop_hit else tp_px), ("stop" if stop_hit else "tp")
    reason = "time_stop" if end_idx == entry_idx + max_bars - 1 else "end_of_data"
    return end_idx, close[end_idx], reason


def simulate_trial(bars_arrays, signals, R):
    """Walk `signals` (already the (kind, L)-detected, BOTH-direction table) in bar order, one
    busy-until tracker per direction, continuous across the whole series. Returns the trade table
    (columns per the module's per-trade schema, pre-cost) and a counts dict."""
    high, low, close, open_ = bars_arrays["high"], bars_arrays["low"], bars_arrays["close"], bars_arrays["open"]
    ts_close, date = bars_arrays["ts_close"], bars_arrays["session_date"]
    n = len(high)
    busy_until = {1: -1, -1: -1}
    n_signals = n_skipped_open = n_skipped_no_bar = 0
    rows = []
    for row in signals.itertuples(index=False):
        g, d, stop_px = int(row.g_idx), int(row.direction), float(row.stop_px)
        n_signals += 1
        if g <= busy_until[d]:
            n_skipped_open += 1
            continue
        entry_idx = g + 1
        if entry_idx >= n:
            n_skipped_no_bar += 1
            continue
        entry_px = float(open_[entry_idx])
        stop_dist = abs(stop_px - entry_px)
        if stop_dist == 0:
            n_skipped_no_bar += 1   # degenerate zero-risk signal; cannot size a stop/target
            continue
        tp_px = entry_px + d * R * stop_dist
        exit_idx, exit_px, reason = _walk_exit(high, low, close, entry_idx, stop_px, tp_px, d)
        busy_until[d] = exit_idx
        gross_ret_pct = d * (exit_px / entry_px - 1) * 100
        rows.append(dict(g_idx_signal=g, sig_ts=ts_close[g], direction=d, entry_idx=entry_idx,
                          entry_ts=ts_close[entry_idx], entry_px=entry_px, exit_idx=exit_idx,
                          exit_ts=ts_close[exit_idx], exit_px=exit_px, exit_reason=reason,
                          bars_held=exit_idx - entry_idx + 1, gross_ret_pct=gross_ret_pct,
                          stop_px=stop_px, tp_px=tp_px, date=date[entry_idx]))
    cols = ["g_idx_signal", "sig_ts", "direction", "entry_idx", "entry_ts", "entry_px", "exit_idx",
            "exit_ts", "exit_px", "exit_reason", "bars_held", "gross_ret_pct", "stop_px", "tp_px", "date"]
    counts = dict(n_signals=n_signals, n_skipped_open=n_skipped_open, n_skipped_no_bar=n_skipped_no_bar)
    return pd.DataFrame(rows, columns=cols), counts


def _walk_exit_batch(high, low, close, entry_idx, stop_px, tp_px, direction, max_bars=TIME_STOP_BARS):
    """Vectorised form of `_walk_exit` for an ARRAY of independent entries at once (used only by
    the random-entry control, whose draws have no sequential dependency on each other -- unlike
    `simulate_trial`'s busy-until chaining, which genuinely needs the scalar, per-signal walk).
    Same stop-wins-a-tie / time_stop / end_of_data semantics as `_walk_exit`; a Python-level loop
    over `max_bars` (<=50) columns, fully vectorised over all entries per column, replaces a
    Python-level loop over entries x bars -- this is what keeps 200 control seeds x tens of
    thousands of trades tractable. Returns exit_idx, exit_px (float arrays, one per entry)."""
    n, m = len(high), len(entry_idx)
    is_long = direction > 0
    exit_idx = np.minimum(entry_idx + max_bars - 1, n - 1)   # default: time_stop / end_of_data
    exit_px = close[exit_idx]
    resolved = np.zeros(m, dtype=bool)
    for k in range(max_bars):
        i = entry_idx + k
        active = (~resolved) & (i <= n - 1)
        if not active.any():
            break
        ii = i[active]
        h, l = high[ii], low[ii]
        d, sp, tp = is_long[active], stop_px[active], tp_px[active]
        stop_hit = np.where(d, l <= sp, h >= sp)
        tp_hit = np.where(d, h >= tp, l <= tp)
        hit = stop_hit | tp_hit
        if hit.any():
            idx_active = np.flatnonzero(active)
            idx_hit = idx_active[hit]
            exit_idx[idx_hit] = ii[hit]
            exit_px[idx_hit] = np.where(stop_hit[hit], sp[hit], tp[hit])
            resolved[idx_hit] = True
    return exit_idx, exit_px


def random_entry_control(bars_arrays, trades, R, cost1, pool_idx, n_seeds=N_SEEDS, seed=CONTROL_SEED):
    """A40's random-entry control (see module docstring): 200 draws from ONE seeded generator,
    without replacement from `pool_idx` (bar indices whose ts_close falls in the matched window),
    same direction/stop-distance/R as each matched real trade, net of cost1 only. Returns
    (win_pct_per_seed, net_pct_per_seed), each length n_seeds."""
    n_tr = len(trades)
    win_pct, net_pct = np.full(n_seeds, np.nan), np.full(n_seeds, np.nan)
    if n_tr == 0 or len(pool_idx) == 0:
        return win_pct, net_pct
    high, low, close, open_ = bars_arrays["high"], bars_arrays["low"], bars_arrays["close"], bars_arrays["open"]
    directions = trades["direction"].to_numpy()
    stop_dists = (trades["stop_px"] - trades["entry_px"]).abs().to_numpy()
    rng = np.random.default_rng(seed)
    replace = len(pool_idx) < n_tr
    for s in range(n_seeds):
        draws = rng.choice(pool_idx, size=n_tr, replace=replace)
        entry_px = open_[draws]
        stop_px = entry_px - directions * stop_dists
        tp_px = entry_px + directions * R * stop_dists
        _, exit_px = _walk_exit_batch(high, low, close, draws, stop_px, tp_px, directions)
        g = directions * (exit_px / entry_px - 1) * 100
        win_pct[s] = 100 * np.mean(g > 0)
        net_pct[s] = np.mean(g - cost1)
    return win_pct, net_pct


def summarize_trial(series_id, kind, L, R, win_name, trades_w, cost1, cost2, all_dates,
                    bars_arrays, pool_idx):
    n = len(trades_w)
    if n:
        trades_w = trades_w.copy()
        trades_w["net_pct_cost1"] = trades_w["gross_ret_pct"] - cost1
        trades_w["net_pct_cost2"] = trades_w["gross_ret_pct"] - cost2
    row = dict(series=series_id, trial=f"{kind}|L{L}|R{R}", type=kind, L=L, R=R, window=win_name,
               n=n, win=(100 * (trades_w["gross_ret_pct"] > 0).mean()) if n else np.nan,
               net_pct_cost1=trades_w["net_pct_cost1"].mean() if n else np.nan,
               net_pct_cost2=trades_w["net_pct_cost2"].mean() if n else np.nan,
               mean_bars_held=trades_w["bars_held"].mean() if n else np.nan)
    net1 = trades_w["net_pct_cost1"].to_numpy() if n else np.array([])
    dates = trades_w["date"] if n else pd.Series([], dtype="datetime64[ns]")
    # Defensive union, not a normal path: entry-date attribution keeps a trade's date inside its
    # OWN window almost always, but a signal on a session's very last (partial) bar can fill on
    # the FIRST bar of the next session, one calendar day past a window boundary -- extend the
    # fixed calendar with any such stray dates so stats.calendar_day_sharpe's zero-fill never
    # KeyErrors instead of silently dropping/misdating that trade.
    all_dates_ext = sorted(set(all_dates) | set(pd.DatetimeIndex(dates))) if n else all_dates
    row["sharpe_calday"] = stats.calendar_day_sharpe(net1, dates, all_dates_ext)
    row["p_boot_day"] = stats.one_sided_p(net1, stats.day_blocks(dates)) if n else np.nan
    row["p_boot_month"] = stats.one_sided_p(net1, stats.month_blocks(dates)) if n else np.nan
    row["expected_rw_win"] = 100.0 / (1 + R)
    ctrl_win, ctrl_net = random_entry_control(bars_arrays, trades_w, R, cost1, pool_idx)
    valid = ~np.isnan(ctrl_net)
    row["control_win"] = float(np.nanmean(ctrl_win)) if valid.any() else np.nan
    row["control_net_pct"] = float(np.nanmean(ctrl_net)) if valid.any() else np.nan
    row["frac_seeds_beaten"] = float(np.mean(row["net_pct_cost1"] > ctrl_net[valid])) if (n and valid.any()) else np.nan
    row["spec"] = SPEC_NOTE
    return row, net1, trades_w


def _boot_group_means(vals, days, n_boot, rng):
    """`n_boot` resampled block-bootstrap means of `vals` (centred on its OWN grand mean),
    resampling whole day-blocks with replacement -- vectorised over ALL n_boot draws at once
    (a per-block sum/size pair is all a resampled mean needs: mean(concat(picked blocks)) =
    sum(picked block sums) / sum(picked block sizes), so there is no need to ever materialise the
    concatenated array itself, which is what made the naive per-iteration version too slow for
    the pattern table's "unconditional" group -- up to the whole multi-year bar series)."""
    codes, uniq = pd.factorize(days)
    centered = vals - vals.mean()
    n_blk = len(uniq)
    block_sum = np.zeros(n_blk)
    block_size = np.zeros(n_blk)
    np.add.at(block_sum, codes, centered)
    np.add.at(block_size, codes, 1.0)
    picks = rng.integers(0, n_blk, size=(n_boot, n_blk))
    return block_sum[picks].sum(axis=1) / block_size[picks].sum(axis=1)


def _two_sample_boot_p(vals_a, days_a, vals_c, days_c, n_boot=stats.N_BOOT, seed=stats.SEED):
    """Two-sided day-block bootstrap p for mean(vals_a) - mean(vals_c) != 0: each group is
    block-bootstrapped INDEPENDENTLY over its own day-blocks, centred on its OWN observed mean
    (generalising `stats.block_bootstrap_p`'s single-sample per-group-mean-centred null to two
    independent samples, since Var(A-C) = Var(A) + Var(C) for independent A, C -- see module
    docstring); NaN if either group has < `stats.MIN_BLOCKS` day blocks. One-sided (Thread B
    convention, matching `stats.one_sided_p`): p/2 when the observed difference is positive, else
    1.0."""
    a, da = np.asarray(vals_a, float), np.asarray(days_a)
    c, dc = np.asarray(vals_c, float), np.asarray(days_c)
    if stats.n_blocks(da) < stats.MIN_BLOCKS or stats.n_blocks(dc) < stats.MIN_BLOCKS:
        return np.nan
    obs = a.mean() - c.mean()
    rng = np.random.default_rng(seed)
    means_a = _boot_group_means(a, da, n_boot, rng)
    means_c = _boot_group_means(c, dc, n_boot, rng)
    diffs = means_a - means_c
    p_two = float((np.abs(diffs) >= abs(obs)).mean())
    return p_two / 2 if obs > 0 else 1.0


def pattern_table_for_series(series_id, bars, R_size):
    """One (series, L, horizon, pattern) row per combination -- see module docstring."""
    close = bars["close"].to_numpy(float)
    dates = bars["session_date"].to_numpy()
    n = len(bars)
    g = np.arange(n)
    rows = []
    for L in L_VALUES:
        prior_high, prior_low = add_swing_levels(bars, L)
        high, low, c = bars["high"], bars["low"], bars["close"]
        ok = (prior_high.notna() & prior_low.notna()).to_numpy()
        rev_short = (ok & (high > prior_high).to_numpy() & (c < prior_high).to_numpy())
        rev_long = (ok & (low < prior_low).to_numpy() & (c > prior_low).to_numpy())
        cont_short = (ok & (c < prior_low).to_numpy())
        cont_long = (ok & (c > prior_high).to_numpy())
        groups = {
            "reversal": (np.flatnonzero(rev_short), np.flatnonzero(rev_long), True),
            "continuation": (np.flatnonzero(cont_short), np.flatnonzero(cont_long), True),
            "unconditional": (np.array([], dtype=int), g, False),
        }
        cache = {}
        for hz in HORIZONS:
            valid_all = g + hz < n
            fwd = np.full(n, np.nan)
            fwd[valid_all] = close[g[valid_all] + hz] - close[valid_all]
            for pattern, (idx_short, idx_long, signed) in groups.items():
                idx = np.concatenate([idx_short, idx_long])
                direction = np.concatenate([-np.ones(len(idx_short)), np.ones(len(idx_long))]) if signed \
                    else np.ones(len(idx))
                keep = idx + hz < n
                idx, direction = idx[keep], direction[keep]
                d_ret = direction * fwd[idx]
                ret_range = d_ret / R_size
                ret_pct = direction * (close[idx + hz] / close[idx] - 1) * 100
                out_dates = dates[idx + hz]
                cache[(hz, pattern)] = (ret_range, ret_pct, out_dates)
                rows.append(dict(series=series_id, L=L, horizon=hz, pattern=pattern, n=len(idx),
                                  mean_range=np.mean(ret_range) if len(idx) else np.nan,
                                  median_range=np.median(ret_range) if len(idx) else np.nan,
                                  mean_pct=np.mean(ret_pct) if len(idx) else np.nan,
                                  median_pct=np.median(ret_pct) if len(idx) else np.nan,
                                  p_vs_unconditional=np.nan))
        unc_pct_by_hz = {hz: cache[(hz, "unconditional")][1] for hz in HORIZONS}
        unc_days_by_hz = {hz: cache[(hz, "unconditional")][2] for hz in HORIZONS}
        for row in rows:
            if row["L"] != L or row["pattern"] == "unconditional":
                continue
            _, ret_pct, out_dates = cache[(row["horizon"], row["pattern"])]
            if len(ret_pct) and len(unc_pct_by_hz[row["horizon"]]):
                row["p_vs_unconditional"] = _two_sample_boot_p(ret_pct, out_dates, unc_pct_by_hz[row["horizon"]],
                                                                unc_days_by_hz[row["horizon"]])
    return pd.DataFrame(rows, columns=PATTERN_COLS)


def _bars_arrays(bars):
    return dict(high=bars["high"].to_numpy(float), low=bars["low"].to_numpy(float),
                close=bars["close"].to_numpy(float), open=bars["open"].to_numpy(float),
                ts_close=bars["ts_close"].to_numpy(), session_date=bars["session_date"].to_numpy())


def decide(res, test_fdr, instrument):
    """A40b: SPY and gold are decided SEPARATELY. `res`/`test_fdr` are already restricted to
    `instrument`'s own series (see `main`); `test_fdr`'s `fdr_pass_10pct` column, however, was
    computed once over the FULL 24-row family (both instruments), so the FDR condition below is
    still family-wide even though the winner search is not."""
    train = res[(res["window"] == "TRAIN") & (res["n"] >= 100)]
    if train.empty:
        return dict(instrument=instrument, winner_series="NONE", winner_trial="NONE", winner_type="",
                    winner_L=np.nan, winner_R=np.nan, train_n=0, train_sharpe_calday=np.nan, test_n=0,
                    test_net_pct_cost1=np.nan, test_p_boot_day=np.nan, test_control_net_pct=np.nan,
                    test_dsr_N24=np.nan, cond_net_pos=False, cond_p_boot_day=False,
                    cond_fdr_pass_10pct=False, cond_beats_control=False, cond_dsr_gt_095=False,
                    cond_n_ge_200=False, verdict="UNDERPOWERED", spec=SPEC_NOTE)
    winner = train.sort_values("sharpe_calday", ascending=False).iloc[0]
    match = test_fdr[(test_fdr["series"] == winner["series"]) & (test_fdr["trial"] == winner["trial"])]
    t = match.iloc[0]
    cond_net = bool(t["net_pct_cost1"] > 0)
    cond_p = bool(t["p_boot_day"] < 0.05)
    cond_fdr = bool(t["fdr_pass_10pct"])
    cond_ctrl = bool(t["net_pct_cost1"] > t["control_net_pct"])
    cond_dsr = bool(t["dsr_N24"] > 0.95)
    cond_n = bool(t["n"] >= 200)
    verdict = "UNDERPOWERED" if not cond_n else ("SURVIVES" if (cond_net and cond_p and cond_fdr
                                                                 and cond_ctrl and cond_dsr) else "FAILED")
    return dict(instrument=instrument, winner_series=winner["series"], winner_trial=winner["trial"],
                winner_type=winner["type"], winner_L=int(winner["L"]), winner_R=int(winner["R"]),
                train_n=int(winner["n"]), train_sharpe_calday=winner["sharpe_calday"], test_n=int(t["n"]),
                test_net_pct_cost1=t["net_pct_cost1"], test_p_boot_day=t["p_boot_day"],
                test_control_net_pct=t["control_net_pct"], test_dsr_N24=t["dsr_N24"],
                cond_net_pos=cond_net, cond_p_boot_day=cond_p, cond_fdr_pass_10pct=cond_fdr,
                cond_beats_control=cond_ctrl, cond_dsr_gt_095=cond_dsr, cond_n_ge_200=cond_n,
                verdict=verdict, spec=SPEC_NOTE)


def main(inp, out):
    if inp != "extended":
        raise ValueError(f"pipeline.units.sweep only supports --in extended (got {inp!r})")
    all_bars, all_arrays, td_by_series = {}, {}, {}
    for sid in SERIES:
        b = pd.read_parquet(SERIES_CACHE[sid]).sort_values("ts_close").reset_index(drop=True)
        all_bars[sid] = b
        all_arrays[sid] = _bars_arrays(b)
        td_by_series[sid] = sorted(pd.unique(b["session_date"]))

    trials_full = {}   # (series, kind, L, R) -> (trades_df, counts)
    for sid in SERIES:
        for kind in TYPES:
            for L in L_VALUES:
                sig = detect_signals(all_bars[sid], kind, L)
                for R in R_VALUES:
                    trials_full[(sid, kind, L, R)] = simulate_trial(all_arrays[sid], sig, R)

    rows, trade_frames = [], []
    for win_name in ["TRAIN", "TEST"]:
        win_rows, win_nets = [], []
        for sid in SERIES:
            _, start, end = next(w for w in WINDOWS_BY_SERIES[sid] if w[0] == win_name)
            start_ts, end_ts = pd.Timestamp(start), pd.Timestamp(end)
            arrays = all_arrays[sid]
            pool_idx = np.flatnonzero((arrays["ts_close"] >= start_ts) & (arrays["ts_close"] <= end_ts))
            all_dates = [d for d in td_by_series[sid] if start_ts <= d <= end_ts]
            cost1 = 2 * COST_BP_SIDE[sid] * 0.01
            cost2 = 2 * cost1
            for kind in TYPES:
                for L in L_VALUES:
                    for R in R_VALUES:
                        trades_all, _counts = trials_full[(sid, kind, L, R)]
                        trades_w = trades_all[(trades_all["sig_ts"] >= start_ts) & (trades_all["sig_ts"] <= end_ts)]
                        row, net1, trades_w = summarize_trial(sid, kind, L, R, win_name, trades_w, cost1, cost2,
                                                              all_dates, arrays, pool_idx)
                        win_rows.append(row)
                        win_nets.append(net1)
                        if len(trades_w):
                            t = trades_w.assign(series=sid, trial=row["trial"], window=win_name)
                            trade_frames.append(t[TRADE_COLS])
        sr_pool = [stats.per_trade_sharpe(x) for x in win_nets]
        for row, x in zip(win_rows, win_nets):
            dsr = stats.deflated_sharpe(x, sr_trials=sr_pool, n=DSR_N)[0] if len(x) >= 3 else np.nan
            row["dsr_N24"] = dsr
        rows.extend(win_rows)

    res = pd.DataFrame(rows)[OUT_COLS]
    res.to_csv(out, index=False, float_format="%.6f")
    tr_all = pd.concat(trade_frames, ignore_index=True) if trade_frames else pd.DataFrame(columns=TRADE_COLS)
    tr_all.to_csv(TRADES_OUT, index=False, float_format="%.6f")

    test_rows = res[res["window"] == "TEST"].copy()
    test_rows["fdr_pass_10pct"] = stats.bh_fdr(test_rows["p_boot_day"].fillna(1.0).to_numpy(), alpha=0.10) \
        if len(test_rows) else np.array([], dtype=bool)
    test_rows[TEST_COLS].to_csv("out/trackB_trials.csv", index=False, float_format="%.6f")

    decisions = []
    for instrument, series_ids in INSTRUMENT_SERIES.items():
        present = [s for s in series_ids if s in SERIES]
        if not present:
            continue
        sub_res = res[res["series"].isin(present)]
        sub_test = test_rows[test_rows["series"].isin(present)]
        decisions.append(decide(sub_res, sub_test, instrument))
    pd.DataFrame(decisions)[DECISION_COLS].to_csv("out/trackB_decision.csv", index=False, float_format="%.6f")

    pat_frames = [pattern_table_for_series(sid, all_bars[sid], R_SIZE[sid]) for sid in SERIES]
    pat = pd.concat(pat_frames, ignore_index=True) if pat_frames else pd.DataFrame(columns=PATTERN_COLS)
    pat.to_csv("out/trackB_pattern_table.csv", index=False, float_format="%.6f")

    print(res.to_string(index=False, float_format=lambda x: f"{x:.4f}"))
    print("\nDECISIONS:", decisions)


def _empty_outputs(out):
    """This unit's own exception convention (A40 item 2, not `_gh.run`'s A32 default) -- see
    module docstring: header-only csvs, never a literally empty file."""
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    pd.DataFrame(columns=OUT_COLS).to_csv(out, index=False)
    pd.DataFrame(columns=TRADE_COLS).to_csv(TRADES_OUT, index=False)
    pd.DataFrame(columns=TEST_COLS).to_csv("out/trackB_trials.csv", index=False)
    pd.DataFrame(columns=DECISION_COLS).to_csv("out/trackB_decision.csv", index=False)
    pd.DataFrame(columns=PATTERN_COLS).to_csv("out/trackB_pattern_table.csv", index=False)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", default="extended")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    try:
        main(a.inp, a.out)
    except Exception:
        traceback.print_exc(file=sys.stderr)
        _empty_outputs(a.out)
    sys.exit(0)
