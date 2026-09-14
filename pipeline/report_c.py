"""Render TRACK_C.md from out/sellvol_*.csv and out/trials.csv only (D7's rule, reused for Track
C, mirroring pipeline.report_b's own convention for Track B: tables generated, never typed; every
number below is read from a csv or computed from one at render time, never hand-typed into this
file's source).

    python -m pipeline.report_c

Track C (Amendment A43, owner's option E, pre-registered 2026-09-14 14:57 UTC, before any run) is
for a stock account with options approval for DEFINED-RISK SPREADS (iron butterflies/condors,
bought wings capping the loss at entry) -- NOT the prop account that governs every other track in
this repository (`pipeline.units.eventvol`'s A42 buyer side and everything in `PLAYBOOK_0DTE.md`
are the prop account's own 0DTE book). It is reported here, under its own heading, and MUST NEVER
enter `PLAYBOOK_0DTE.md` (the task's own instruction). `pipeline.units.sellvol` writes its own
`survives`/`promotable` columns with the family-wide BH-FDR condition hard-coded False (that
STANDALONE unit cannot know the real, family-wide result -- `pipeline/trials.py` computes it
downstream, across the WHOLE ledger, not just these 3 trials); this module recombines the real
FDR-pass bit (`out/trials.csv`, family "sellvol", trial "SELLVOL <name>") with sellvol's own five
other `cond_*` columns to generate the TRUE verdict per trial, at the row `pipeline/trials.py`
itself reads into the family (`cost_per_leg == 0.10`, mirroring `pipeline.trials`'s own "family
39 -> 42" wiring) -- the $0.20 row is a cost-sensitivity sweep only, never itself a family/FDR
row, and is reported with the OTHER five conditions but an explicitly UNDETERMINED FDR/verdict.

This unit does not fit `pipeline.units._gh.run`'s A32 convention or `pipeline.units.sellvol`'s own
header-only-on-exception contract; like `pipeline.report`/`pipeline.report_b`, it is a plain
script expected to run only after its inputs already exist (`pipeline/trials.py`, then this
module, per `pipeline/run_all.py`'s own step order), with no try/except of its own -- a missing
input surfaces as a normal Python traceback. A header-only `out/sellvol_candidates.csv` (the
pre-registered-but-not-yet-runnable state, before the real 0DTE file existed) renders a TRACK_C.md
with empty tables and no verdict sentences, never a crash (`md()`'s own empty-frame behaviour, and
the verdict loop simply has nothing to iterate).
"""
import os

import pandas as pd

from pipeline.report import md

CANDIDATES_PATH = "out/sellvol_candidates.csv"
BY_YEAR_PATH = "out/sellvol_by_year.csv"
TRIALS_PATH = "out/trials.csv"
FAMILY_COST = 0.10   # the row pipeline/trials.py reads into the family ledger (family 39 -> 42)

RESULTS_COLS = ["trial", "cost_per_leg", "n", "n_skipped", "win", "mean_usd", "median_usd",
                "mean_pct_maxloss", "median_pct_maxloss", "worst_structure_pct_maxloss",
                "control_mean_pct_credit", "contracts_median", "sharpe_calday", "p_boot_day",
                "dsr_N42", "label"]
TAIL_COLS = ["trial", "cost_per_leg", "worst_day_usd", "worst_month_usd", "p05_day_usd",
            "full_loss_share", "mae_median_pct_credit", "mae_share_gt100", "mae_share_gt200",
            "max_drawdown_pct", "worst_month_pct"]
BY_YEAR_COLS = ["group_value", "trial", "n", "mean_pct_maxloss", "worst_day_usd", "full_loss_share"]
INT_COLS = ("n", "n_skipped")

FAMILY_CONDS = [
    ("net return (mean_pct_maxloss) > 0", "cond_net"),
    ("day-block bootstrap p < 0.05", "cond_p_day"),
    ("passes BH-FDR at 10% within the family (`out/trials.csv`)", None),   # filled with the real bit
    ("beats the A42 buyer-mirror control", "cond_beats_control"),
    ("deflated Sharpe (N=42) > 0.95", "cond_dsr"),
    ("at least 200 trades", "cond_n"),
]
TAIL_CONDS = [
    ("max drawdown at the sizing rule < 20%", "cond_drawdown"),
    ("worst month (equity) > -10%", "cond_worst_month"),
    ("day-block bootstrap p < 0.01", "cond_p01"),
]


def fdr_pass_map():
    """{trial name ('S1'/'S2'/'S3') -> real family-wide BH-FDR pass} from out/trials.csv's
    "sellvol" family, added by `pipeline.trials`'s own wiring at the SAME $0.10/leg row this
    module reads (module docstring); {} if trials.py has not run yet or found no sellvol rows."""
    if not os.path.exists(TRIALS_PATH):
        return {}
    t = pd.read_csv(TRIALS_PATH)
    sub = t[t["family"] == "sellvol"]
    out = {}
    for _, r in sub.iterrows():
        name = str(r["trial"]).replace("SELLVOL ", "", 1)
        out[name] = bool(r["fdr_pass_10pct_family"])
    return out


def verdict_sentence(row, fdr_pass):
    """One generated verdict sentence for a single (trial, cost) row (module docstring): at the
    family cost row (`fdr_pass` not None), recombines sellvol's own five real `cond_*` columns
    with the REAL FDR-pass bit to compute the true survives/promotable and states which condition
    (if any) failed; at the non-family cost row (`fdr_pass=None`) the FDR condition -- and hence
    the true verdict -- is explicitly UNDETERMINED, and only the other five conditions are stated."""
    if fdr_pass is None:
        conds = [(label, bool(row[col])) for label, col in FAMILY_CONDS if col is not None]
        passed = [c for c, ok in conds if ok]
        failed = [c for c, ok in conds if not ok]
        return (f"**{row['trial']} at ${row['cost_per_leg']:.2f}/leg** (a cost-sensitivity row, "
                f"not the family row): FDR -- and therefore survives/promotable -- is UNDETERMINED "
                f"at this cost (only the ${FAMILY_COST:.2f}/leg row feeds `pipeline/trials.py`'s "
                f"family ledger). Other conditions met: {'; '.join(passed) if passed else 'none'}. "
                f"Other conditions not met: {'; '.join(failed) if failed else 'none'}.")
    conds = [(label, bool(fdr_pass) if col is None else bool(row[col])) for label, col in FAMILY_CONDS]
    survives = all(ok for _, ok in conds)
    tail_conds = [(label, bool(row[col])) for label, col in TAIL_CONDS]
    promotable = survives and all(ok for _, ok in tail_conds)
    passed = [c for c, ok in conds if ok]
    failed = [c for c, ok in conds if not ok]
    tail_failed = [c for c, ok in tail_conds if not ok]
    verdict = "PROMOTABLE" if promotable else ("SURVIVES but not promotable" if survives else "does not survive")
    tail_txt = (f" Tail condition(s) that keep it from promotion: {'; '.join(tail_failed)}."
               if (survives and not promotable) else "")
    return (f"**{row['trial']} at ${row['cost_per_leg']:.2f}/leg** (the family row): **{verdict}**. "
            f"Conditions met: {'; '.join(passed) if passed else 'none'}. Conditions not met: "
            f"{'; '.join(failed) if failed else 'none'}.{tail_txt}")


def fixed_footer(spec_col):
    """The FIXED-parameters footer: the pre-registration text carried verbatim in every row's
    `spec` column (identical across rows), never re-typed here (mirrors pipeline.report_b's own
    `fixed_footer`)."""
    if not len(spec_col):
        return ""
    return str(spec_col.iloc[0])


def track_c():
    cand = pd.read_csv(CANDIDATES_PATH)
    by_year = pd.read_csv(BY_YEAR_PATH) if os.path.exists(BY_YEAR_PATH) else pd.DataFrame(columns=BY_YEAR_COLS)
    fdr_map = fdr_pass_map()

    L = ["# TRACK_C.md — defined-risk short 0DTE premium (Amendment A43, owner's option E)", "",
         "Track C requires a stock account with OPTIONS APPROVAL FOR DEFINED-RISK SPREADS (iron "
         "butterflies/condors, the long wings bought so the loss is capped at entry) -- NOT the "
         "prop account that governs every other deliverable in this repository (the 0DTE buyer's "
         "side, `pipeline.units.eventvol`'s A42, and `PLAYBOOK_0DTE.md` itself). It is reported "
         "here, under its own heading, and never enters the prop-account playbook. The reference "
         "class a risk desk actually cares about for a short-premium book is the TAIL -- worst "
         "day, worst month, full-loss frequency, intraday adverse excursion -- not the mean; the "
         "tail table below exists for exactly that reason. Three trials (S1 iron butterfly at "
         "09:31, S2 the same structure at 13:30, S3 iron condor at 09:31), each at two per-leg "
         "round-trip costs, on the owner's real SPY 0DTE 1-minute bars as one out-of-sample "
         "window (no CONTEXT/SELECTION/HOLDOUT split); every parameter was pre-registered before "
         "this unit ever ran (`ACCEPTANCE.md` Amendment A43).", ""]

    L += ["## Results (`out/sellvol_candidates.csv`)", "",
         md(cand[[c for c in RESULTS_COLS if c in cand]], fmt="{:.4f}", int_cols=INT_COLS), ""]

    L += ["## Tail table (worst day/month, 5th-percentile day, full-loss share, intraday MAE "
         "shares, max drawdown, worst month as % of equity)", "",
         md(cand[[c for c in TAIL_COLS if c in cand]], fmt="{:.4f}", int_cols=INT_COLS), ""]

    L += ["## By calendar year (`out/sellvol_by_year.csv`, $0.10/leg row only, descriptive)", ""]
    by_year_rows = by_year[by_year["group_type"] == "year"] if len(by_year) else by_year
    L += [md(by_year_rows[[c for c in BY_YEAR_COLS if c in by_year_rows]], fmt="{:.4f}", int_cols=INT_COLS), ""]

    L += ["## By prior-close VIX tercile (`out/sellvol_by_year.csv`, $0.10/leg row only, descriptive)", ""]
    by_terc_rows = by_year[by_year["group_type"] == "vix_tercile"] if len(by_year) else by_year
    L += [md(by_terc_rows[[c for c in BY_YEAR_COLS if c in by_terc_rows]], fmt="{:.4f}", int_cols=INT_COLS), ""]

    L += ["## Verdict per trial (family row = $0.10/leg, recombining the REAL family-wide BH-FDR "
         "result from `out/trials.csv` with `out/sellvol_candidates.csv`'s own five other "
         "conditions -- `pipeline.units.sellvol`'s own `survives`/`promotable` columns carry a "
         "hard-coded False FDR placeholder and are not the true verdict)", ""]
    for _, row in cand.sort_values(["trial", "cost_per_leg"]).iterrows():
        fdr = fdr_map.get(row["trial"]) if abs(row["cost_per_leg"] - FAMILY_COST) < 1e-9 else None
        L += [verdict_sentence(row, fdr), ""]

    L += ["## FIXED parameters (pre-registration, never re-tuned on any window)", "",
         fixed_footer(cand["spec"]) if "spec" in cand and len(cand) else "", ""]

    open("TRACK_C.md", "w").write("\n".join(L))


if __name__ == "__main__":
    track_c()
    print("wrote TRACK_C.md")
