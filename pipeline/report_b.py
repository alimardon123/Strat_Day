"""Render TRACK_B.md from out/trackB_*.csv only (D7's rule, reused for Track B: tables generated,
never typed; every number below is read from a csv or computed from one at render time, never
hand-typed into this file's source).

    python -m pipeline.report_b

Track B (Amendment A40, owner's request, pre-registered 2026-09-13 12:26 UTC, before any run) is
a technical-analysis question, independent of the 0DTE prop-account constraint that governs every
other deliverable in this repository: does a "liquidation" of a prior swing extreme on a range-bar
chart (a stop-hunt beyond it) mark the START of a swing, either by REVERSAL (price rejects back
inside the level) or by CONTINUATION (price closes through it)? It is bound to the SAME statistical
guards as Track A (block bootstrap, its own BH-FDR family, a random-entry control, a deflated
Sharpe) but not to the account constraint, and it is scored in raw price-level dollars / % return,
not SPX points. The train/test LOCK is fixed and never re-opened: SPY and XAUUSD winners are each
chosen SEPARATELY on their own TRAIN window by the highest calendar-day Sharpe among trials with at
least 100 trades (A40b), then each checked ONCE on its own TEST window against six survival
conditions that share one thing across instruments -- the BH-FDR pass column, computed once over
the full 24-row TEST family; no parameter here may be re-tuned after seeing a TEST number, and the
range values, the causal swing lookback, the stop/target construction and the 24-trial family
enumeration were all pre-registered before `pipeline.units.rangebars`/`pipeline.units.sweep` ever
ran. Gold's own TRAIN/TEST windows were re-registered TWICE before any gold result existed (A40b
found the 2006-2020 Oanda XAU_USD minute source; A40c then replaced A40b's TEST window -- the
owner's untouched 5000R export -- with a second rebuild from that same minute source, since no
independent minute source exists to gate the owner's file against); the owner's 5000R export is
CONTEXT ONLY throughout this report, never a trial input. Gate B-a was itself amended mid-run
(A40c) once the owner's own 34R TradingView export was found not to be a faithful range-bar series
in its own right (see the gate table below); the rebuild's construction rule was NOT changed in
response -- only what "correct" means for the gate was, for both instruments.

This unit does not fit `pipeline.report`'s `pipeline.units._gh.run`/A32 convention (its inputs are
`pipeline.units.sweep`'s own header-only-on-exception outputs, not a fleet unit's); like
`pipeline.report`, it is a plain script expected to run only after its inputs already exist, with
no try/except of its own -- a missing/empty input surfaces as a normal Python traceback.
"""
import re

import numpy as np
import pandas as pd

from pipeline.report import md

GATE_PATH = "out/trackB_rangebars_gate.csv"
CANDIDATES_PATH = "out/trackB_sweep_candidates.csv"
TRIALS_PATH = "out/trackB_trials.csv"
DECISION_PATH = "out/trackB_decision.csv"
PATTERN_PATH = "out/trackB_pattern_table.csv"
TRADES_PATH = "out/trackB_sweep_trades.csv"

GATE_COLS = ["check", "value", "threshold", "ok", "counts_toward_gate", "note"]
TRIAL_COLS = ["series", "trial", "n", "win", "net_pct_cost1", "net_pct_cost2", "mean_bars_held",
              "sharpe_calday", "p_boot_day", "p_boot_month", "control_win", "control_net_pct",
              "frac_seeds_beaten", "expected_rw_win", "dsr_N24"]
TEST_TABLE_COLS = TRIAL_COLS + ["fdr_pass_10pct"]
DECISION_TABLE_COLS = ["instrument", "winner_series", "winner_trial", "train_n", "train_sharpe_calday",
                        "test_n", "test_net_pct_cost1", "test_p_boot_day", "test_control_net_pct",
                        "test_dsr_N24", "cond_net_pos", "cond_p_boot_day", "cond_fdr_pass_10pct",
                        "cond_beats_control", "cond_dsr_gt_095", "cond_n_ge_200", "verdict"]
PATTERN_TABLE_COLS = ["series", "L", "horizon", "pattern", "n", "mean_range", "median_range",
                       "mean_pct", "median_pct", "p_vs_unconditional"]
INT_COLS = ("L", "horizon", "n", "train_n", "test_n", "winner_L", "winner_R")


def _isyes(v):
    return str(v) in ("True", "1", "1.0")


def gate_sentence(gate):
    gating = gate[gate["counts_toward_gate"].apply(_isyes)]
    n_pass = int(gating["ok"].apply(_isyes).sum())
    verdict = "PASS" if n_pass == len(gating) else "FAIL"
    return (f"Gate B-a (`pipeline.units.rangebars`, redefined as Amendment A40c mid-run) checks "
            f"the SPY and XAUUSD rebuilds' OWN internal consistency (every completed bar's "
            "high-low equals its own range to the cent and threads with no gap within a session "
            "-- the NYSE trading day for SPY, the trading WEEK for gold -- and every session/week "
            "has at least as many bars as its own high-low span requires) plus determinism for "
            "both series (rebuilding twice yields byte-identical parquet) -- NOT a byte match "
            "against either owner TradingView export: A40c's own diagnostic found the SPY 34R "
            "export is not a faithful range-bar series in its own right, and no minute source "
            "exists to gate the gold 5000R export against at all (A40b). "
            f"{n_pass} of {len(gating)} checks pass, so `GATE (B-a): {verdict}`. The remaining "
            "rows are CONTEXT ONLY (never gating): the SPY rebuild's own and the owner 34R file's "
            "own bars-per-session and the correlation between their 5-minute-resampled close "
            "series on their overlap; and, for gold, the rebuild's own and the owner 5000R file's "
            "own bars-per-week, packed into a single row per the task brief.")


def decision_sentence(dec):
    lines = []
    for _, row in dec.iterrows():
        conds = [("net_pct_cost1 > 0 at 1x cost", row["cond_net_pos"]),
                 ("day-block bootstrap p < 0.05", row["cond_p_boot_day"]),
                 ("passes BH-FDR at 10% within the 24-trial TEST family", row["cond_fdr_pass_10pct"]),
                 ("beats the random-entry control", row["cond_beats_control"]),
                 ("deflated Sharpe (N=24) > 0.95", row["cond_dsr_gt_095"]),
                 ("at least 200 TEST trades", row["cond_n_ge_200"])]
        passed = [c for c, ok in conds if _isyes(ok)]
        failed = [c for c, ok in conds if not _isyes(ok)]
        passed_txt = "; ".join(passed) if passed else "none"
        failed_txt = "; ".join(failed) if failed else "none"
        lines.append(f"**{row['instrument']}**: the pre-registered TRAIN winner (highest "
                      f"calendar-day Sharpe among that instrument's own TRAIN trials with at "
                      f"least 100 trades) is `{row['winner_series']} {row['winner_trial']}`, "
                      f"checked exactly once on TEST: **verdict {row['verdict']}**. Conditions "
                      f"met: {passed_txt}. Conditions not met: {failed_txt}.")
    return "\n\n".join(lines)


def pattern_sentence(series_id, sub):
    rev, cont = sub[sub["pattern"] == "reversal"], sub[sub["pattern"] == "continuation"]
    n_rev_sig, n_cont_sig = int((rev["p_vs_unconditional"] < 0.05).sum()), int((cont["p_vs_unconditional"] < 0.05).sum())
    rev_txt = (f"carries directional content beyond the unconditional baseline at {n_rev_sig} of "
               f"{len(rev)} (L x horizon) combinations tested (day-block bootstrap p<0.05)") if n_rev_sig \
        else f"does not carry directional content beyond the unconditional baseline at any of the {len(rev)} (L x horizon) combinations tested"
    cont_txt = (f"carries directional content beyond the unconditional baseline at {n_cont_sig} of "
                f"{len(cont)} (L x horizon) combinations tested (day-block bootstrap p<0.05)") if n_cont_sig \
        else f"does not carry directional content beyond the unconditional baseline at any of the {len(cont)} (L x horizon) combinations tested"
    return f"**{series_id}**: a reversal-shaped sweep {rev_txt}; a continuation-shaped close-through {cont_txt}."


def fixed_footer(spec_col):
    """The FIXED-parameters footer: the pre-registration text carried verbatim in every row's
    `spec` column (identical across rows), never re-typed here."""
    if not len(spec_col):
        return ""
    return str(spec_col.iloc[0])


def track_b():
    gate = pd.read_csv(GATE_PATH)
    cand = pd.read_csv(CANDIDATES_PATH)
    trials = pd.read_csv(TRIALS_PATH)
    dec = pd.read_csv(DECISION_PATH)
    pat = pd.read_csv(PATTERN_PATH)

    L = ["# TRACK_B.md — technical swing-start detector on range bars (Amendment A40)", "",
         "Track B asks whether a stop-hunting sweep of a prior swing extreme on a range-bar chart "
         "marks the START of a swing, either by REVERSAL (price rejects back inside the level) or "
         "by CONTINUATION (price closes through it) -- a pure technical-analysis question, "
         "independent of the 0DTE prop-account constraint governing every other deliverable in "
         "this repository, but bound to the same statistical guards (block bootstrap, its own "
         "family-wide BH-FDR, a random-entry control, a deflated Sharpe). The TRAIN/TEST lock is "
         "fixed and never re-opened: SPY and XAUUSD winners are each chosen SEPARATELY, on their "
         "own TRAIN window, by the highest calendar-day Sharpe among trials with at least 100 "
         "trades (A40b), then each checked EXACTLY ONCE on their own TEST window; no parameter may "
         "be re-tuned after seeing a TEST number. Gold's windows were re-registered twice before "
         "any gold result existed: A40b found a 2006-2020 Oanda XAU_USD minute source; A40c then "
         "replaced A40b's planned TEST window (the owner's untouched 5000R export) with a second "
         "rebuild from that same minute source, since no independent minute source exists to gate "
         "the owner's file against -- the owner's 5000R export is CONTEXT ONLY throughout this "
         "report. Whatever the verdict, the pattern table at the end stands as the finding (A40's "
         "own instruction).", "",
         "## Gate B-a (range-bar rebuild, SPY and gold)", "",
         gate_sentence(gate), "", md(gate[GATE_COLS], fmt="{:.6f}"), ""]

    L += ["## Sweep family — TRAIN (SPY + XAU, `out/trackB_sweep_candidates.csv`)", ""]
    train = cand[cand["window"] == "TRAIN"]
    L += [md(train[[c for c in TRIAL_COLS if c in train]], fmt="{:.4f}", int_cols=INT_COLS), ""]

    L += ["## Sweep family — TEST (SPY + XAU, `out/trackB_trials.csv`, this run's own 24-row BH-FDR family)", ""]
    L += [md(trials[[c for c in TEST_TABLE_COLS if c in trials]], fmt="{:.4f}", int_cols=INT_COLS), ""]

    L += ["## Decision (`out/trackB_decision.csv`)", "",
          md(dec[[c for c in DECISION_TABLE_COLS if c in dec]], fmt="{:.4f}", int_cols=INT_COLS), "",
          decision_sentence(dec), ""]

    L += ["## Pattern table (`out/trackB_pattern_table.csv`) — sweeps vs the unconditional baseline", "",
          "mean/median_range are in bar-range units (the series' own fixed $ range); mean/median_pct "
          "are in %; both are HYPOTHESIS-DIRECTION-signed for the reversal/continuation rows (short "
          "instances flipped so they combine with long instances instead of cancelling) and "
          "UN-signed for the unconditional row (the series' own raw per-bar drift); "
          "p_vs_unconditional is a day-block bootstrap p for the gap against that same row's "
          "unconditional baseline (blank for the unconditional rows themselves).", "",
          md(pat[PATTERN_TABLE_COLS], fmt="{:.6f}", int_cols=INT_COLS), ""]
    for series_id, sub in pat.groupby("series"):
        L += [pattern_sentence(series_id, sub), ""]

    L += ["## FIXED parameters (pre-registration, never re-tuned on any window)", "",
          fixed_footer(cand["spec"]) if "spec" in cand and len(cand) else fixed_footer(trials["spec"]), ""]

    open("TRACK_B.md", "w").write("\n".join(L))


if __name__ == "__main__":
    track_b()
    print("wrote TRACK_B.md")
