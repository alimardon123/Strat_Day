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
Sharpe) but not to the account constraint, and it is scored in raw SPY dollars / % return, not SPX
points. The train/test LOCK is fixed and never re-opened: a single SPY winner is chosen on TRAIN
by the highest calendar-day Sharpe among trials with at least 100 trades, then checked ONCE on
TEST against six survival conditions; no parameter here may be re-tuned after seeing a TEST number,
and the range values, the causal swing lookback, the stop/target construction and the 24-trial
family enumeration were all pre-registered before `pipeline.units.rangebars`/`pipeline.units.sweep`
ever ran. XAUUSD is DEFERRED to a later, separate run (Amendments A40b/A40c, mid-run scope
changes): a longer 2006-2020 Oanda gold minute source was found after this family was first
pre-registered, so the gold trials wait for a TRAIN rebuild of that source, with the owner's own
5000R export reserved, unseen, as the TEST-only window; this report is therefore SPY-only (16 of
the pre-registered 24 trials). Gate B-a was itself amended mid-run (A40c) once the owner's own
34R TradingView export was found not to be a faithful range-bar series in its own right (see the
gate table below); the rebuild's construction rule was NOT changed in response -- only what
"correct" means for the gate was.

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
DECISION_TABLE_COLS = ["winner_series", "winner_trial", "train_n", "train_sharpe_calday", "test_n",
                        "test_net_pct_cost1", "test_p_boot_day", "test_control_net_pct", "test_dsr_N24",
                        "cond_net_pos", "cond_p_boot_day", "cond_fdr_pass_10pct", "cond_beats_control",
                        "cond_dsr_gt_095", "cond_n_ge_200", "verdict"]
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
            f"the SPY rebuild's OWN internal consistency (every completed bar's high-low equals "
            "its range to the cent and threads with no gap within a session, and every session "
            "has at least as many bars as its own high-low span requires) plus determinism "
            "(rebuilding twice yields byte-identical parquet) -- NOT a byte match against the "
            "owner's TradingView 34R export, which A40c's own diagnostic found is not a faithful "
            f"range-bar series in its own right: {n_pass} of {len(gating)} checks pass, so "
            f"`GATE (B-a): {verdict}`. The remaining rows are CONTEXT ONLY (never gating): the "
            "rebuild's own and the owner's own bars-per-session, and the correlation between "
            "their 5-minute-resampled close series, on their overlap.")


def decision_sentence(dec):
    row = dec.iloc[0]
    conds = [("net_pct_cost1 > 0 at 1x cost", row["cond_net_pos"]),
             ("day-block bootstrap p < 0.05", row["cond_p_boot_day"]),
             ("passes BH-FDR at 10% within this run's TEST-row family", row["cond_fdr_pass_10pct"]),
             ("beats the random-entry control", row["cond_beats_control"]),
             ("deflated Sharpe (N=24) > 0.95", row["cond_dsr_gt_095"]),
             ("at least 200 TEST trades", row["cond_n_ge_200"])]
    passed = [c for c, ok in conds if _isyes(ok)]
    failed = [c for c, ok in conds if not _isyes(ok)]
    passed_txt = "; ".join(passed) if passed else "none"
    failed_txt = "; ".join(failed) if failed else "none"
    return (f"The pre-registered SPY-TRAIN winner (highest calendar-day Sharpe among TRAIN trials "
            f"with at least 100 trades) is `{row['winner_series']} {row['winner_trial']}`, checked "
            f"exactly once on TEST: **verdict {row['verdict']}**. Conditions met: {passed_txt}. "
            f"Conditions not met: {failed_txt}.")


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
         "fixed and never re-opened: one SPY winner is chosen on TRAIN by the highest "
         "calendar-day Sharpe among trials with at least 100 trades, then checked EXACTLY ONCE on "
         "TEST; no parameter may be re-tuned after seeing a TEST number. XAUUSD is DEFERRED to a "
         "separate, later run (mid-run Amendments A40b/A40c): a longer Oanda gold minute source "
         "was found after this family was pre-registered, so the gold trials wait for a TRAIN "
         "rebuild of it, with the owner's own 5000R export reserved, unseen, as the TEST-only "
         "window -- this report and the family below are SPY-only. Whatever the verdict, the "
         "pattern table at the end stands as the finding (A40's own instruction).", "",
         "## Gate B-a (range-bar rebuild)", "",
         gate_sentence(gate), "", md(gate[GATE_COLS], fmt="{:.6f}"), ""]

    L += ["## SPY sweep family — TRAIN (`out/trackB_sweep_candidates.csv`)", ""]
    train = cand[cand["window"] == "TRAIN"]
    L += [md(train[[c for c in TRIAL_COLS if c in train]], fmt="{:.4f}", int_cols=INT_COLS), ""]

    L += ["## SPY sweep family — TEST (`out/trackB_trials.csv`, this run's own BH-FDR family)", ""]
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
