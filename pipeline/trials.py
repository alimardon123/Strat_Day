"""D6 — the family-wide trial ledger: every trial this run tested for an edge (A31), one BH-FDR
across all of them. Reads the per-module tables, writes out/trials.csv.
    python -m pipeline.trials
"""
import glob
import os

import numpy as np
import pandas as pd

from pipeline import stats


def main():
    rows = []
    r = pd.read_csv("out/reconcile_trials.csv")
    for _, x in r.iterrows():
        rows.append(dict(family=x["family"], trial=x["candidate"], n=x["n"], p=x["p_boot_month"], p_day=x["p_boot_day"],
                         dsr_this_run=x["dsr_N12"], dsr_historical=x["dsr_N42"]))
    for f in sorted(glob.glob("out/xmarket_*.csv")):
        x = pd.read_csv(f).iloc[0]
        rows.append(dict(family="xmarket", trial=f"gap-up on {x['market']}", n=x["n"], p=x["p_boot_day"], p_day=x["p_boot_day"]))
    if glob.glob("out/flow_candidates.csv"):
        for _, x in pd.read_csv("out/flow_candidates.csv").iterrows():
            rows.append(dict(family="flow", trial=x["candidate"], n=x["n"], p=x["p_boot_day"], p_day=x["p_boot_day"]))
    if os.path.exists("out/fvg_candidates.csv"):
        # A36: only the SELECTION-window rows are trials; CONTEXT is reported context and HOLDOUT
        # is these same 8 trials' out-of-sample rows (reported in the fvg table, not re-counted).
        fvg = pd.read_csv("out/fvg_candidates.csv")
        for _, x in fvg[fvg["window"] == "SELECTION"].iterrows():
            rows.append(dict(family="fvg", trial=f"FVG {x['trial']}", n=x["n"], p=x["p_boot_month"], p_day=x["p_boot_day"]))
    hold = pd.read_csv("out/holdout_summary.csv") if os.path.exists("out/holdout_summary.csv") else None
    if hold is not None:
        for _, x in hold.iterrows():
            rows.append(dict(family="holdout", trial=f"HOLDOUT {x['signal']}", n=x.get("n", 0), p=x.get("p_month", np.nan), p_day=x.get("p_day", np.nan)))
    t = pd.DataFrame(rows)
    # the month-block p is NA below 20 blocks; use the day-block p for the family-wide test in that case
    t["p_for_fdr"] = t["p"].fillna(t["p_day"]).fillna(1.0)
    t["fdr_pass_10pct_family"] = stats.bh_fdr(t["p_for_fdr"].to_numpy(), alpha=0.10)
    t.to_csv("out/trials.csv", index=False, float_format="%.6f")
    if hold is not None:
        # survival rule 3: finalise the holdout labels with the family-wide FDR result
        fdr = dict(zip(t.loc[t["family"] == "holdout", "trial"], t.loc[t["family"] == "holdout", "fdr_pass_10pct_family"]))
        hold["fdr_pass_10pct_family"] = [bool(fdr.get(f"HOLDOUT {s_}", False)) for s_ in hold["signal"]]
        hold["label_final"] = [("SURVIVES" if f else "FAILED (family FDR)") if str(l).startswith("SURVIVES") else l
                               for l, f in zip(hold["label"], hold["fdr_pass_10pct_family"])]
        hold.to_csv("out/holdout_summary.csv", index=False, float_format="%.6f")
        hold.to_csv("out/holdout_pooled.csv", index=False, float_format="%.6f")
        print("holdout labels finalised:", dict(zip(hold["signal"], hold["label_final"])))
    print(f"trials counted: {len(t)} (families: {t['family'].value_counts().to_dict()}); FDR passes at 10%: {int(t['fdr_pass_10pct_family'].sum())}")
    print(t[["family", "trial", "n", "p_for_fdr", "fdr_pass_10pct_family"]].to_string(index=False, float_format=lambda x: f"{x:.4f}"))


if __name__ == "__main__":
    main()
