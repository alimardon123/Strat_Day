"""Defined-risk short 0DTE premium on real SPY 0DTE prices (A43, Track C, owner's option E,
pre-registered 2026-09-14 14:57 UTC, before any run; NOT tuned to look good). Question: does
SELLING defined-risk 0DTE premium (an iron butterfly/condor, wings bought so the loss is capped
at entry) earn more than its own worst-case tail costs, once the tail itself -- worst day, worst
month, full-loss frequency, intraday adverse excursion -- is measured, not just the mean? This
track is for a stock account with options approval for defined-risk spreads, NOT the prop account
(A43's own text): it is reported under its own heading (`TRACK_C.md`, `pipeline.report_c`) and
never enters `PLAYBOOK_0DTE.md`.

    python -m pipeline.units.sellvol --in extended --out out/sellvol_candidates.csv

Three trials, all counted (A43, family 39 -> 42): S1 iron butterfly at 09:31 (sell the nearest-
ATM call and put -- ONE shared body strike, matching a real iron butterfly's one-strike body --
wings bought at +/-1% of the 09:31 SPY price); S2 the same structure sold at 13:30; S3 iron condor
at 09:31 (short legs at +/-0.5%, wings at +/-1.5%, FOUR independent strikes -- a real condor's
two-strike body, unlike a butterfly's one). Every leg is a SPY same-day-expiry contract; every
structure holds to the 15:59 bar close. Costs: $0.10 and $0.20 per leg round trip (4 legs per
structure, so $0.40 / $0.80 per structure) -- no $0 row (unlike eventvol's A42 three-cost sweep;
A43 names only these two). Reuses `pipeline.units.eventvol`'s real-0DTE-shard loader, its SPX-
point/10 reference-price convention and its nearest-either-right ATM strike rule, and
`pipeline.units.realopt`'s causal strike-availability rule and per-leg entry-before-exit rule
(A41 clarification) -- see the numbered points below for exactly how each is reused or adapted for
a 4-leg defined-risk structure instead of a 2-leg long straddle / a single long option.

`data/ext/spy_0dte_1min_2024-02_2026-09.csv.gz` (or its per-year shards) is read via
`eventvol.option_shards`/`eventvol.load_0dte` unchanged: without it, this unit prints `[SKIP] ...`
and writes ALL FOUR output files with a header row only, exit 0 -- `pipeline.units.letf`'s (A38)
contract, copied here verbatim like eventvol.py/realopt.py, NOT `pipeline.units._gh.run`'s A32
empty-file+`.error`+exit-2 convention. On ANY exception (missing file, bad data, a bug) the same
header-only-outputs-and-exit-0 contract applies.

Every ambiguity the amendment (or the task that implements it) left open is fixed here and
restated in the `spec` column (SPEC_NOTE below); worth flagging up front:
(1) Reference price / ATM body strike: `eventvol.ref_price_series` (the 09:31/13:30 SPX-point
    minute close / 10, the SAME SPY-dollar proxy eventvol uses) supplies each trial's own entry-
    minute reference price. S1/S2's shared short call+put strike (an iron butterfly's one-strike
    body) reuses `eventvol.nearest_strike`'s own "nearest strike, either right, ties toward the
    smaller strike" rule -- but FIRST restricted to strikes with a print AT OR BEFORE the entry
    minute (point 2 below), a filter eventvol itself never needed (A42's day is skipped whole on
    ANY missing leg, so it never had to reason about which strikes were even tradable at entry).
    S3's four legs, and every wing on every trial, are each an INDEPENDENT target (+/-0.5%/1.5% or
    +/-1%) priced with `realopt.nearest_listed` on that leg's OWN right, matching a real iron
    condor's two-strike body (vs. a butterfly's shared one) and named as such in A43's own text
    ("sell the call at +0.5% and the put at -0.5%" -- two separate targets, not one).
(2) Causal strike availability: reused VERBATIM from `realopt.reprice_trades`/A41's clarification
    (judge round 7) -- a strike is a candidate for ANY leg's nearest-strike search only if it has
    at least one bar printed at or before that trial's own entry minute that session; a strike
    whose first print comes later could not have been dealt at entry time. Applied per (right,
    entry minute), same as realopt.py; the module's own unit test exercises this with a deliberate
    decoy strike that only prints after entry and must be skipped in favour of the next-nearest
    strike that was actually tradable.
(3) Entry/exit fill, and what a "print" is: A43's own words -- entry = the leg's bar close at the
    entry minute, else the NEXT print within 5 minutes; exit = the 15:59 bar close, else the LAST
    print within the previous 10 minutes. Unlike eventvol's (uncapped next-bar-OPEN) or realopt's
    (uncapped next-bar-open / last-bar-at-or-before) fallback, A43 names an explicit, CAPPED
    window on both sides and says "print", not "bar", so "the next/last print" is read as that
    bar's own CLOSE on both sides (there is no finer notion of "a print" than a 1-minute bar's own
    close in this file; using open on one side and close on the other, eventvol's own asymmetric
    convention, has no textual basis here since A43 never distinguishes the two sides by name).
    A leg with no print in its own window is missing; a structure with ANY leg missing is skipped
    and counted (n_skipped) -- never a partial (3-leg) structure. Per-leg entry-before-exit: A41's
    clarification ("the entry bar actually used must be strictly earlier than the exit bar
    actually used") is reused per LEG here (a structure has four, not one) -- a same-bar or
    inverted fill on ANY leg skips and counts the WHOLE structure.
(4) Wing width, when the two sides differ: real listed strikes, chosen independently on each side
    to two different percentage targets, need not sit the same distance from the short strike(s).
    `max_loss = wing_width - credit` uses the WIDER of the two sides (`max(call_wing_width,
    put_wing_width)`) -- the true worst case at expiry for a defined-risk spread with asymmetric
    wings, since either side alone can be the one that finishes far ITM. A structure whose
    resulting credit is not strictly positive, or whose resulting max_loss is not strictly
    positive (a data anomaly this task's own sizing rule cannot price), is skipped and counted --
    not a real premium-selling trade.
(5) Costs: $0.10 / $0.20 PER LEG round trip, subtracted ONCE per leg (4 legs => $0.40 / $0.80 per
    structure) -- unlike eventvol's A42 "one flat amount per PAIR, never split" convention, A43's
    own text prices this per leg, and a 4-leg defined-risk spread genuinely trades 4 separate
    contracts (never 2, so there is no "pair" to keep it flat over).
(6) Sizing: `contracts = floor(4% of a FIXED $100,000 account / (max_loss x 100))`, recomputed
    FRESH each day from THAT day's own max_loss -- never compounded against a running equity,
    since the amendment's own figure is a literal $100,000, not "4% of current equity"; this is
    what makes "the worst possible day is the daily limit" a CONSTANT, not a growing/shrinking
    number as the book wins or loses.
(7) Tail stats vs. calendar stats: `worst_day_usd`/`worst_month_usd`/`p05_day_usd`/
    `full_loss_share` are computed over TRADED days only (a day the trial actually held a
    structure) -- these describe the tail of the trades that happened. `sharpe_calday` and
    `max_drawdown_pct` are computed on the equity curve over the FULL window day population,
    zero-filled on skipped/non-trading days (mirrors `stats.calendar_day_sharpe`'s own internal
    zero-fill, exposed here as a full Series via `_zero_fill` so the equity curve/drawdown can be
    built from it, not just its Sharpe scalar) -- these describe the calendar-continuous risk of
    running the book. The two groups answer different questions and are never mixed.
(8) MAE: at every minute STRICTLY between the trial's own nominal entry minute and 15:59 where
    ALL FOUR legs have an EXACT (never a fallback) print, the structure is marked at the four bar
    closes; the mark's P&L relative to the credit banked at entry is `credit - debit(mark)`.
    MAE is the worst such mark, floored at 0 (`pipeline.playbook.mae`'s own convention -- a
    structure that never goes underwater has ZERO adverse excursion, never a positive number),
    reported in % of credit and % of max_loss. NaN (excluded from the two share statistics'
    denominator, not counted as "not exceeding") when no common minute exists across all four
    legs.
(9) Control ("positive excess over control"): the task's own resolution, stated here per its own
    instruction -- the seller's GROSS (pre-cost) P&L on the shared two legs a buyer would hold is
    the NEGATIVE of that buyer's own GROSS (cost=$0) `mean_pct` in `out/eventvol_candidates.csv`
    (A42). S1/S3 enter at 09:31, matched to E1 (every session at 09:31); S2 enters at 13:30,
    matched to E3 (every NON-FOMC session at 13:30) rather than E2 UNION E3, since S2 itself is
    NOT FOMC-restricted and E3 -- not the FOMC-only E2 -- is the day-population-matched buyer
    mirror the task names directly. The comparison is GROSS-vs-GROSS on both sides and therefore
    identical across a trial's two cost rows; NaN (fails the condition) before eventvol has run.
(10) `survives`/`promotable`: five of the six/nine conditions are computed for real; the sixth
     (family-wide BH-FDR pass) this STANDALONE unit cannot know, since `pipeline/trials.py`
     computes it once, downstream, across the WHOLE ledger (not just these 3 trials). That ONE
     condition is a hard-coded `False` placeholder here (per the task's own instruction), so
     `survives`/`promotable` are ALWAYS False in this file by construction -- never a silent true
     positive. The `cond_*` columns and `label` report the other conditions honestly so a
     downstream reader (`pipeline.report_c`, run AFTER `pipeline/trials.py`) can recombine them
     with the real family-wide FDR result and generate the true verdict.
(11) By-year / by-VIX-tercile table (`out/sellvol_by_year.csv`): computed at the $0.10/leg cost
     row only (the row `pipeline/trials.py`'s own wiring reads into the family ledger -- see that
     module). VIX terciles reuse `realopt.vix_terciles` (quantile rank, robust to duplicate
     values) over the FULL window's own day population (not each trial's own surviving days),
     mirroring `realopt.calibration_summary`'s own "terciles ... over the file's own sessions"
     reading; the per-day prior-close VIX itself reuses `signals.day_table`'s own merge_asof
     convention (`allow_exact_matches=False` -- strictly the prior session's close), computed
     directly here rather than by building a full `day_table` this unit does not otherwise need.
(12) Determinism: the only random draws are stats.one_sided_p's 2,000-sample day-block bootstrap for
     p_boot_day, re-seeded at 11 on every call — which is why two runs are byte-identical; sorted iteration
     everywhere else.
"""
import argparse
import os
import sys
import traceback

import numpy as np
import pandas as pd

from pipeline import sessions, stats
from pipeline.units import eventvol, realopt

LEG_ROLES = ["short_call", "short_put", "long_call", "long_put"]
ENTRY_TOL = 5     # minutes forward, A43's own text (point 3)
EXIT_TOL = 10      # minutes backward from 15:59, A43's own text (point 3)
LEGS_PER_STRUCTURE = 4
COST_PER_LEG = [0.10, 0.20]              # per leg round trip (point 5) -- no $0 row (A43)
SIZING_PCT, SIZING_ACCOUNT = 0.04, 100000.0
SIZING_BUDGET = SIZING_PCT * SIZING_ACCOUNT     # $4,000 (point 6)
DSR_N = 42                                # A43's own "family 39 -> 42"

# (name, entry minute-of-day, wing target %, short-leg target % or None for a shared ATM body)
TRIALS = [
    ("S1", eventvol.MOD_0931, 0.01, None),
    ("S2", eventvol.MOD_1330, 0.01, None),
    ("S3", eventvol.MOD_0931, 0.015, 0.005),
]
BUYER_CONTROL_TRIAL = {"S1": "E1", "S2": "E3", "S3": "E1"}   # point 9

BY_YEAR_PATH = "out/sellvol_by_year.csv"   # fixed literal name (realopt.CALIB_OUT's own convention)

TRADE_RAW_COLS = [
    "date", "ref_px",
    "short_call_strike", "short_put_strike", "long_call_strike", "long_put_strike",
    "short_call_entry_px", "short_call_entry_mod", "short_call_exit_px", "short_call_exit_mod",
    "short_put_entry_px", "short_put_entry_mod", "short_put_exit_px", "short_put_exit_mod",
    "long_call_entry_px", "long_call_entry_mod", "long_call_exit_px", "long_call_exit_mod",
    "long_put_entry_px", "long_put_entry_mod", "long_put_exit_px", "long_put_exit_mod",
    "credit", "call_wing_width", "put_wing_width", "wing_width", "max_loss",
    "gross_pnl", "gross_pct_credit", "mae_dollar", "mae_pct_credit", "mae_pct_maxloss",
]
TRADE_COLS = ["trial"] + TRADE_RAW_COLS + [
    "contracts", "net_pnl_cost0", "net_pnl_cost1", "net_pct_maxloss_cost0", "net_pct_maxloss_cost1",
    "pnl_usd_cost0", "pnl_usd_cost1",
]
EQUITY_COLS = ["trial", "cost_per_leg", "date", "contracts", "pnl_usd", "equity", "drawdown_pct"]
BY_YEAR_COLS = ["group_type", "group_value", "trial", "n", "mean_pct_maxloss", "worst_day_usd", "full_loss_share"]
OUT_COLS = [
    "trial", "cost_per_leg", "n", "n_skipped", "win", "mean_usd", "median_usd", "mean_pct_maxloss",
    "median_pct_maxloss", "worst_structure_pct_maxloss", "worst_day_usd", "worst_month_usd", "p05_day_usd",
    "full_loss_share", "mae_median_pct_credit", "mae_share_gt100", "mae_share_gt200", "contracts_median",
    "sharpe_calday", "max_drawdown_pct", "worst_month_pct", "p_boot_day", "dsr_N42", "survives", "promotable",
    "label", "control_mean_pct_credit", "cond_net", "cond_p_day", "cond_fdr", "cond_beats_control", "cond_dsr",
    "cond_n", "cond_drawdown", "cond_worst_month", "cond_p01", "spec",
]

SPEC_NOTE = (
    "FIXED (pre-registration, A43): S1 iron butterfly at 09:31 (shared ATM body strike, wings at "
    "+/-1% of the 09:31 SPY price); S2 the same structure at 13:30; S3 iron condor at 09:31 (short "
    "legs at +/-0.5%, wings at +/-1.5%, four independent strikes). Reference/ATM-body strike: "
    "eventvol's SPX-point/10 reference and nearest-either-right rule; every other leg is priced "
    "independently per right with realopt.nearest_listed. Causal availability (A41 clarification, "
    "reused verbatim): a strike is a candidate only if it has a print at or before that trial's own "
    "entry minute. Entry = the leg's bar close at the entry minute, else the next print within 5 "
    "minutes; exit = the 15:59 close, else the last print within the previous 10 minutes ('print' "
    "read as that bar's own close both sides); a leg with neither, or whose entry bar actually used "
    "is not strictly before its exit bar actually used, skips and counts the WHOLE structure "
    "(n_skipped), never a partial structure. max_loss = wing_width - credit, wing_width = the WIDER "
    "of the two independently-priced sides (the true worst case at expiry); a non-positive credit "
    "or max_loss also skips and counts. Costs: $0.10 / $0.20 PER LEG round trip (4 legs => $0.40 / "
    "$0.80 per structure), two rows, no $0 row. Sizing: contracts = floor(4% of a FIXED $100,000 "
    "account / (max_loss x 100)), recomputed fresh each day, never compounded. worst_day/"
    "worst_month/p05_day/full_loss_share are over TRADED days only; sharpe_calday/max_drawdown_pct "
    "are on the equity curve over the FULL window day population, zero-filled on skipped/non-"
    "trading days. MAE: worst minute-by-minute mark (all four legs, EXACT prints only, strictly "
    "between entry and 15:59) of credit-minus-debit-to-close, floored at 0, in % of credit and of "
    "max_loss; NaN excluded from the >100%/>200% share denominators. Control ('positive excess over "
    "control'): the seller's GROSS P&L on the shared two legs is the NEGATIVE of eventvol's (A42) "
    "own GROSS mean_pct for the day-matched buyer trial (E1 for S1/S3's 09:31 entries, E3 -- not E2 "
    "union E3 -- for S2's 13:30, non-FOMC-restricted entries), both sides pre-cost. survives/"
    "promotable: the family-wide BH-FDR condition is a hard-coded False placeholder here (this "
    "standalone unit cannot know it; pipeline/trials.py computes it downstream across the whole "
    "ledger) -- both columns are therefore ALWAYS False in this file; the cond_* columns and label "
    "report the other conditions honestly for pipeline.report_c to recombine with the real FDR "
    "result after pipeline/trials.py has run. DSR at N=42 (family 39->42) per cost row, using this "
    "run's own three trials' per-trade Sharpe AT THAT COST as the SR0 pool (this codebase's usual "
    "'this run's own trials only' convention). By-year/VIX-tercile table: the $0.10/leg cost row "
    "only; terciles over the window's own day population (realopt.vix_terciles), prior-close VIX "
    "via signals.day_table's own merge_asof convention. On ANY exception (including the 0DTE file "
    "being absent) this unit writes header-only outputs and exits 0, exactly pipeline.units.letf's "
    "(A38) contract, like eventvol.py/realopt.py -- this pre-registered candidate must never fail "
    "`make all`."
)


# ---------------------------------------------------------------------------------------------
# Strike selection (points 1-2)
# ---------------------------------------------------------------------------------------------

def body_strike(options_day, ref_px, entry_mod):
    """The iron butterfly's shared ATM strike for BOTH short legs (module docstring point 1):
    `eventvol.nearest_strike`'s own either-right, ties-toward-the-smaller-strike rule, restricted
    FIRST to strikes with a print at or before `entry_mod` (point 2, the causal-availability rule
    reused from realopt.py -- eventvol.py itself never needed this filter)."""
    causal = options_day.loc[options_day["mod"] <= entry_mod]
    return eventvol.nearest_strike(causal, ref_px)


def leg_strike(options_day, right, target, entry_mod):
    """One independent leg's strike (module docstring point 1): the nearest LISTED strike of
    `right` to `target`, among strikes with a print at or before `entry_mod` (point 2, reused
    verbatim from `realopt.reprice_trades`); ties toward the smaller strike
    (`realopt.nearest_listed`'s own np.argmin-on-a-sorted-array convention)."""
    strikes = options_day.loc[(options_day["right"] == right) & (options_day["mod"] <= entry_mod), "strike"]
    return realopt.nearest_listed(strikes, target)


# ---------------------------------------------------------------------------------------------
# Fill / structure pricing (points 3-4, 8)
# ---------------------------------------------------------------------------------------------

def _leg_fill(rows, entry_mod, exit_mod=eventvol.MOD_1559):
    """One leg's (entry_px, entry_used_mod, exit_px, exit_used_mod), or None (module docstring
    point 3): the bar close at the exact entry minute, else the NEXT print within ENTRY_TOL=5
    minutes; the bar close at the exact 15:59 minute, else the LAST print within the previous
    EXIT_TOL=10 minutes; None if either side has no such bar, or if the entry bar actually used is
    not strictly earlier than the exit bar actually used (A41 clarification, applied per leg)."""
    if not len(rows):
        return None
    rows = rows.sort_values("mod")
    exact_entry = rows.loc[rows["mod"] == entry_mod]
    if len(exact_entry):
        entry_px, entry_used = float(exact_entry["close"].iloc[0]), entry_mod
    else:
        nxt = rows.loc[(rows["mod"] > entry_mod) & (rows["mod"] <= entry_mod + ENTRY_TOL)]
        if not len(nxt):
            return None
        entry_px, entry_used = float(nxt["close"].iloc[0]), int(nxt["mod"].iloc[0])
    exact_exit = rows.loc[rows["mod"] == exit_mod]
    if len(exact_exit):
        exit_px, exit_used = float(exact_exit["close"].iloc[0]), exit_mod
    else:
        prior = rows.loc[(rows["mod"] < exit_mod) & (rows["mod"] >= exit_mod - EXIT_TOL)]
        if not len(prior):
            return None
        exit_px, exit_used = float(prior["close"].iloc[-1]), int(prior["mod"].iloc[-1])
    if not entry_used < exit_used:
        return None
    return entry_px, entry_used, exit_px, exit_used


def compute_mae(options_day, entry_mod, exit_mod, strikes, credit, max_loss):
    """Worst intraday mark of the structure relative to its own credit (module docstring point 8):
    at every minute STRICTLY between `entry_mod` and `exit_mod` where all four legs (`strikes`:
    role -> (right, strike)) have an EXACT print, mark = credit - (short closes - long closes);
    MAE is the worst (most negative) mark, floored at 0 (`pipeline.playbook.mae`'s own convention).
    Returns (mae_dollar, mae_pct_credit, mae_pct_maxloss); all NaN when no common minute exists."""
    series = {}
    for role, (right, K) in strikes.items():
        sub = options_day.loc[(options_day["right"] == right) & (options_day["strike"] == K)
                              & (options_day["mod"] > entry_mod) & (options_day["mod"] < exit_mod)]
        series[role] = sub.drop_duplicates("mod", keep="first").set_index("mod")["close"]
    common = series[LEG_ROLES[0]].index
    for role in LEG_ROLES[1:]:
        common = common.intersection(series[role].index)
    if len(common) == 0:
        return np.nan, np.nan, np.nan
    debit = (series["short_call"].loc[common] + series["short_put"].loc[common]
            - series["long_call"].loc[common] - series["long_put"].loc[common])
    pnl = credit - debit
    mae_dollar = -min(0.0, float(pnl.min()))
    mae_pct_credit = 100.0 * mae_dollar / credit
    mae_pct_maxloss = 100.0 * mae_dollar / max_loss
    return mae_dollar, mae_pct_credit, mae_pct_maxloss


def build_structure(options_day, ref_px, entry_mod, wing_pct, short_pct):
    """One day's 4-leg structure, or None if any strike/leg cannot be resolved, or the resulting
    credit/max_loss is not strictly positive (module docstring point 4). `short_pct=None` -> an
    iron butterfly (S1/S2): both short legs share ONE ATM strike (`body_strike`); otherwise (S3)
    every leg targets its OWN independent strike (`leg_strike`), a real iron condor's two-strike
    body."""
    if short_pct is None:
        K_body = body_strike(options_day, ref_px, entry_mod)
        if K_body is None:
            return None
        strikes = {"short_call": ("C", K_body), "short_put": ("P", K_body)}
    else:
        Kc = leg_strike(options_day, "C", ref_px * (1 + short_pct), entry_mod)
        Kp = leg_strike(options_day, "P", ref_px * (1 - short_pct), entry_mod)
        if Kc is None or Kp is None:
            return None
        strikes = {"short_call": ("C", Kc), "short_put": ("P", Kp)}
    Klc = leg_strike(options_day, "C", ref_px * (1 + wing_pct), entry_mod)
    Klp = leg_strike(options_day, "P", ref_px * (1 - wing_pct), entry_mod)
    if Klc is None or Klp is None:
        return None
    strikes["long_call"] = ("C", Klc)
    strikes["long_put"] = ("P", Klp)

    fills = {}
    for role, (right, K) in strikes.items():
        rows = options_day.loc[(options_day["right"] == right) & (options_day["strike"] == K)]
        fill = _leg_fill(rows, entry_mod)
        if fill is None:
            return None
        fills[role] = fill

    entry = {r: fills[r][0] for r in LEG_ROLES}
    exitpx = {r: fills[r][2] for r in LEG_ROLES}
    credit = (entry["short_call"] + entry["short_put"]) - (entry["long_call"] + entry["long_put"])
    if credit <= 0:
        return None
    call_wing_width = strikes["long_call"][1] - strikes["short_call"][1]
    put_wing_width = strikes["short_put"][1] - strikes["long_put"][1]
    wing_width = max(call_wing_width, put_wing_width)
    max_loss = wing_width - credit
    if max_loss <= 0:
        return None
    exit_debit = (exitpx["short_call"] + exitpx["short_put"]) - (exitpx["long_call"] + exitpx["long_put"])
    gross_pnl = credit - exit_debit
    mae_dollar, mae_pct_credit, mae_pct_maxloss = compute_mae(
        options_day, entry_mod, eventvol.MOD_1559, strikes, credit, max_loss)

    row = dict(ref_px=ref_px,
              short_call_strike=strikes["short_call"][1], short_put_strike=strikes["short_put"][1],
              long_call_strike=strikes["long_call"][1], long_put_strike=strikes["long_put"][1])
    for role in LEG_ROLES:
        e_px, e_mod, x_px, x_mod = fills[role]
        row[f"{role}_entry_px"], row[f"{role}_entry_mod"] = e_px, e_mod
        row[f"{role}_exit_px"], row[f"{role}_exit_mod"] = x_px, x_mod
    row.update(credit=credit, call_wing_width=call_wing_width, put_wing_width=put_wing_width,
               wing_width=wing_width, max_loss=max_loss, gross_pnl=gross_pnl,
               gross_pct_credit=100.0 * gross_pnl / credit, mae_dollar=mae_dollar,
               mae_pct_credit=mae_pct_credit, mae_pct_maxloss=mae_pct_maxloss)
    return row


def build_trades(groups, ref, days, entry_mod, wing_pct, short_pct):
    """One row per day where a full 4-leg structure could be priced (`build_structure`); returns
    (trades_df, n_skipped) over `days` (module docstring: one shared window across all trials)."""
    empty = pd.DataFrame(columns=["strike", "right", "mod", "open", "close"])
    rows, n_skipped = [], 0
    for d in days:
        ref_px = ref.get(d)
        if ref_px is None:
            n_skipped += 1
            continue
        options_day = groups.get(d.strftime("%Y-%m-%d"), empty)
        st = build_structure(options_day, ref_px, entry_mod, wing_pct, short_pct)
        if st is None:
            n_skipped += 1
            continue
        st["date"] = d
        rows.append(st)
    return pd.DataFrame(rows, columns=TRADE_RAW_COLS), n_skipped


def with_costs_and_sizing(trades):
    """Adds `contracts` (module docstring point 6) and, per cost row (point 5),
    net_pnl_cost{0,1}/net_pct_maxloss_cost{0,1}/pnl_usd_cost{0,1} (the sizing-rule dollar P&L)."""
    out = trades.copy()
    max_loss = out["max_loss"].astype(float)
    gross_pnl = out["gross_pnl"].astype(float)
    out["contracts"] = np.floor(SIZING_BUDGET / (max_loss * 100.0))
    for i, c in enumerate(COST_PER_LEG):
        out[f"net_pnl_cost{i}"] = gross_pnl - LEGS_PER_STRUCTURE * c
        out[f"net_pct_maxloss_cost{i}"] = out[f"net_pnl_cost{i}"] / max_loss * 100.0
        out[f"pnl_usd_cost{i}"] = out["contracts"] * out[f"net_pnl_cost{i}"] * 100.0
    return out


# ---------------------------------------------------------------------------------------------
# Calendar / tail statistics (point 7) and the control (point 9)
# ---------------------------------------------------------------------------------------------

def _zero_fill(pnl, dates, all_dates):
    """The daily P&L series zero-filled over `all_dates` (mirrors `stats.calendar_day_sharpe`'s
    own internal zero-fill, exposed here as a full Series so the equity curve/drawdown can be
    built from it, not just a Sharpe scalar)."""
    s = pd.Series(0.0, index=pd.DatetimeIndex(sorted(set(all_dates))))
    if len(dates):
        add = pd.Series(np.asarray(pnl, float), index=pd.DatetimeIndex(dates)).groupby(level=0).sum()
        s.loc[add.index] += add
    return s


def _worst_month_usd(trades, col):
    if not len(trades):
        return np.nan
    return float(trades.groupby(stats.month_blocks(trades["date"]))[col].sum().min())


def control_mirror_pct(trial):
    """A42's buyer-mirror control (module docstring point 9): NaN before `out/eventvol_candidates
    .csv` has run (this unit is deliberately still runnable without it)."""
    path = "out/eventvol_candidates.csv"
    if not os.path.exists(path) or os.path.getsize(path) == 0:
        return np.nan
    ev = pd.read_csv(path)
    if not len(ev):
        return np.nan
    buyer_trial = BUYER_CONTROL_TRIAL[trial]
    row = ev[(ev["trial"] == buyer_trial) & np.isclose(ev["cost"], 0.0)]
    if not len(row):
        return np.nan
    return -float(row["mean_pct"].iloc[0])


def summarize_trial(trial, cost_idx, trades, days, control_pct, pool):
    """One (trial, cost) row (module docstring points 6-10)."""
    pnl_col, pct_col, usd_col = f"net_pnl_cost{cost_idx}", f"net_pct_maxloss_cost{cost_idx}", f"pnl_usd_cost{cost_idx}"
    n = len(trades)
    row = dict(trial=trial, cost_per_leg=COST_PER_LEG[cost_idx], n=n)
    if n:
        net_pct = trades[pct_col].to_numpy(float)
        usd = trades[usd_col].to_numpy(float)
        mae_valid = trades["mae_pct_credit"].dropna()
        row.update(
            win=100.0 * (trades[pnl_col] > 0).mean(),
            mean_usd=float(usd.mean()), median_usd=float(np.median(usd)),
            mean_pct_maxloss=float(net_pct.mean()), median_pct_maxloss=float(np.median(net_pct)),
            worst_structure_pct_maxloss=float(net_pct.min()),
            worst_day_usd=float(usd.min()), worst_month_usd=_worst_month_usd(trades, usd_col),
            p05_day_usd=float(np.percentile(usd, 5)),
            full_loss_share=float((trades[pnl_col] <= -0.9 * trades["max_loss"]).mean()),
            mae_median_pct_credit=float(mae_valid.median()) if len(mae_valid) else np.nan,
            mae_share_gt100=float((mae_valid > 100).mean()) if len(mae_valid) else np.nan,
            mae_share_gt200=float((mae_valid > 200).mean()) if len(mae_valid) else np.nan,
            contracts_median=float(trades["contracts"].median()))
    else:
        net_pct = np.array([])
        row.update(win=np.nan, mean_usd=np.nan, median_usd=np.nan, mean_pct_maxloss=np.nan,
                  median_pct_maxloss=np.nan, worst_structure_pct_maxloss=np.nan, worst_day_usd=np.nan,
                  worst_month_usd=np.nan, p05_day_usd=np.nan, full_loss_share=np.nan,
                  mae_median_pct_credit=np.nan, mae_share_gt100=np.nan, mae_share_gt200=np.nan,
                  contracts_median=np.nan)

    daily = _zero_fill(trades[usd_col] if n else [], trades["date"] if n else [], days)
    equity = SIZING_ACCOUNT + daily.cumsum()
    peak = equity.cummax()
    drawdown = (peak - equity) / peak * 100.0
    row["sharpe_calday"] = stats.calendar_day_sharpe(daily.to_numpy(), daily.index, days)
    row["max_drawdown_pct"] = float(drawdown.max()) if len(drawdown) else np.nan
    row["worst_month_pct"] = row["worst_month_usd"] / SIZING_ACCOUNT * 100.0 if n else np.nan
    row["p_boot_day"] = stats.one_sided_p(net_pct, stats.day_blocks(trades["date"])) if n else np.nan
    row["dsr_N42"] = stats.deflated_sharpe(net_pct, sr_trials=pool, n=DSR_N)[0] if n >= 3 else np.nan

    row["control_mean_pct_credit"] = control_pct
    gross_pct_mean = float(trades["gross_pct_credit"].mean()) if n else np.nan
    row["cond_net"] = bool(n and row["mean_pct_maxloss"] > 0)
    row["cond_p_day"] = bool(n and pd.notna(row["p_boot_day"]) and row["p_boot_day"] < 0.05)
    row["cond_fdr"] = False   # placeholder -- pipeline/trials.py computes the real family-wide value
    row["cond_beats_control"] = bool(n and pd.notna(gross_pct_mean) and pd.notna(control_pct)
                                     and gross_pct_mean > control_pct)
    row["cond_dsr"] = bool(pd.notna(row["dsr_N42"]) and row["dsr_N42"] > 0.95)
    row["cond_n"] = bool(n >= 200)
    row["survives"] = (row["cond_net"] and row["cond_p_day"] and row["cond_fdr"]
                       and row["cond_beats_control"] and row["cond_dsr"] and row["cond_n"])
    row["cond_drawdown"] = bool(pd.notna(row["max_drawdown_pct"]) and row["max_drawdown_pct"] < 20)
    row["cond_worst_month"] = bool(pd.notna(row["worst_month_pct"]) and row["worst_month_pct"] > -10)
    row["cond_p01"] = bool(n and pd.notna(row["p_boot_day"]) and row["p_boot_day"] < 0.01)
    row["promotable"] = row["survives"] and row["cond_drawdown"] and row["cond_worst_month"] and row["cond_p01"]
    five_ok = (row["cond_net"] and row["cond_p_day"] and row["cond_beats_control"]
              and row["cond_dsr"] and row["cond_n"])
    row["label"] = ("UNDERPOWERED" if not row["cond_n"] else
                    "SURVIVES pending family FDR (out/trials.csv)" if five_ok else "FAILED")
    row["spec"] = SPEC_NOTE
    return row


def build_equity_rows(trial, cost_idx, trades, days):
    """One row per day in `days` (module docstring point 7): contracts/pnl_usd are 0 on a day this
    trial did not hold a structure; equity starts at SIZING_ACCOUNT and accumulates."""
    pnl_col = f"pnl_usd_cost{cost_idx}"
    by_date = ({pd.Timestamp(d): (float(p), float(c)) for d, p, c in
               zip(trades["date"], trades[pnl_col], trades["contracts"])} if len(trades) else {})
    rows = []
    equity = SIZING_ACCOUNT
    peak = SIZING_ACCOUNT
    for d in sorted(set(days)):
        pnl, contracts = by_date.get(d, (0.0, 0.0))
        equity += pnl
        peak = max(peak, equity)
        dd = (peak - equity) / peak * 100.0 if peak else 0.0
        rows.append(dict(trial=trial, cost_per_leg=COST_PER_LEG[cost_idx], date=d,
                         contracts=contracts, pnl_usd=pnl, equity=equity, drawdown_pct=dd))
    return rows


def _vix_prev_series(dates, vix):
    """Per-day prior-close VIX, `signals.day_table`'s own merge_asof convention (module docstring
    point 11), reused directly rather than building the full day_table this unit does not
    otherwise need."""
    v = vix[["date", "close"]].sort_values("date").rename(columns={"close": "vix_prev"})
    left = pd.DataFrame({"date": pd.DatetimeIndex(sorted(set(dates)))})
    m = pd.merge_asof(left, v, on="date", allow_exact_matches=False)
    return pd.Series(m["vix_prev"].to_numpy(), index=m["date"])


def by_year_and_tercile(priced_trials):
    """Descriptive-only rows at the $0.10/leg cost row (module docstring point 11)."""
    any_trades = any(len(t) for t in priced_trials.values())
    tercile_map = {}
    if any_trades:
        all_dates = sorted({pd.Timestamp(d) for t in priced_trials.values() for d in t["date"]})
        vix = pd.read_parquet("data/raw/vix_daily.parquet")
        tercile_map = realopt.vix_terciles(_vix_prev_series(all_dates, vix)).to_dict()
    rows = []
    for trial, trades in priced_trials.items():
        if not len(trades):
            continue
        t = trades.assign(year=pd.to_datetime(trades["date"]).dt.year,
                          vix_tercile=pd.to_datetime(trades["date"]).map(tercile_map))
        for group_type, col in (("year", "year"), ("vix_tercile", "vix_tercile")):
            for val, g in t.groupby(col):
                rows.append(dict(group_type=group_type, group_value=str(val), trial=trial, n=len(g),
                                 mean_pct_maxloss=float(g["net_pct_maxloss_cost0"].mean()),
                                 worst_day_usd=float(g["pnl_usd_cost0"].min()),
                                 full_loss_share=float((g["net_pnl_cost0"] <= -0.9 * g["max_loss"]).mean())))
    return pd.DataFrame(rows, columns=BY_YEAR_COLS)


# ---------------------------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------------------------

def _trades_path(out):
    if out.endswith("_candidates.csv"):
        return out[:-len("_candidates.csv")] + "_trades.csv"
    return out[:-4] + "_trades.csv" if out.endswith(".csv") else out + "_trades.csv"


def _equity_path(out):
    if out.endswith("_candidates.csv"):
        return out[:-len("_candidates.csv")] + "_equity.csv"
    return out[:-4] + "_equity.csv" if out.endswith(".csv") else out + "_equity.csv"


def _write_header_only(out, by_year_out=BY_YEAR_PATH):
    pd.DataFrame(columns=OUT_COLS).to_csv(out, index=False)
    pd.DataFrame(columns=TRADE_COLS).to_csv(_trades_path(out), index=False)
    pd.DataFrame(columns=EQUITY_COLS).to_csv(_equity_path(out), index=False)
    pd.DataFrame(columns=BY_YEAR_COLS).to_csv(by_year_out, index=False)


def main(inp, out, data_path=eventvol.DATA_PATH, by_year_out=BY_YEAR_PATH):
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    if inp != "extended":
        raise ValueError(f"pipeline.units.sellvol only supports --in extended (got {inp!r})")
    if not eventvol.option_shards(data_path):
        print(f"[SKIP] A43 waits for {data_path} (tools/fetch_spy_0dte_local.py)")
        _write_header_only(out, by_year_out)
        return

    odte = eventvol.load_0dte(data_path)
    td = sessions.trading_days_from_vix()
    frame, _dropped, _meta = sessions.build_extended(trading_days=td)
    file_start, file_end = pd.Timestamp(odte["expiry"].min()), pd.Timestamp(odte["expiry"].max())
    window_days = sorted(d for d in td if file_start <= d <= file_end)

    ref_by_mod = {eventvol.MOD_0931: eventvol.ref_price_series(frame, eventvol.MOD_0931),
                 eventvol.MOD_1330: eventvol.ref_price_series(frame, eventvol.MOD_1330)}
    groups = dict(tuple(odte.groupby("expiry")))

    trial_trades, trial_n_skipped = {}, {}
    for name, entry_mod, wing_pct, short_pct in TRIALS:
        trades, n_skipped = build_trades(groups, ref_by_mod[entry_mod], window_days, entry_mod, wing_pct, short_pct)
        trial_trades[name] = with_costs_and_sizing(trades)
        trial_n_skipped[name] = n_skipped

    control_pct = {name: control_mirror_pct(name) for name, *_ in TRIALS}

    rows = []
    for ci in range(len(COST_PER_LEG)):
        pool = [stats.per_trade_sharpe(trial_trades[name][f"net_pct_maxloss_cost{ci}"].dropna().to_numpy(float))
               for name, *_ in TRIALS]
        for name, *_ in TRIALS:
            trades = trial_trades[name]
            row = summarize_trial(name, ci, trades, window_days, control_pct[name], pool)
            row["n_skipped"] = trial_n_skipped[name]
            rows.append(row)

    res = pd.DataFrame(rows)[OUT_COLS]
    res.to_csv(out, index=False, float_format="%.6f")

    trade_frames = [trial_trades[name].assign(trial=name)[TRADE_COLS] for name, *_ in TRIALS]
    tr_all = pd.concat(trade_frames, ignore_index=True) if trade_frames else pd.DataFrame(columns=TRADE_COLS)
    tr_all.sort_values(["trial", "date"]).to_csv(_trades_path(out), index=False, float_format="%.6f")

    equity_rows = []
    for ci in range(len(COST_PER_LEG)):
        for name, *_ in TRIALS:
            equity_rows.extend(build_equity_rows(name, ci, trial_trades[name], window_days))
    pd.DataFrame(equity_rows, columns=EQUITY_COLS).to_csv(_equity_path(out), index=False, float_format="%.6f")

    by_year = by_year_and_tercile({name: trial_trades[name] for name, *_ in TRIALS})
    by_year.to_csv(by_year_out, index=False, float_format="%.6f")

    print(res.to_string(index=False, float_format=lambda x: f"{x:.4f}"))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", default="extended")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    try:
        main(a.inp, a.out)
    except Exception:
        # A38's own contract (see module docstring): header-only outputs, never a .error file, exit
        # 0 -- this pre-registered candidate must never fail `make all`.
        traceback.print_exc()
        _write_header_only(a.out)
    sys.exit(0)
