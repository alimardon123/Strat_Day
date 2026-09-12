"""D6 — the family-wide trial ledger: every trial this run tested for an edge (A31), one BH-FDR
across all of them. Reads the per-module tables, writes out/trials.csv.
    python -m pipeline.trials
"""
import glob

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
    t = pd.DataFrame(rows)
    # the momentum family's month-block p is NA below 20 blocks; use the day-block p for the family-wide test in that case
    t["p_for_fdr"] = t["p"].fillna(t["p_day"]).fillna(1.0)
    t["fdr_pass_10pct_family"] = stats.bh_fdr(t["p_for_fdr"].to_numpy(), alpha=0.10)
    t.to_csv("out/trials.csv", index=False, float_format="%.6f")
    print(f"trials counted: {len(t)} (families: {t['family'].value_counts().to_dict()}); FDR passes at 10%: {int(t['fdr_pass_10pct_family'].sum())}")
    print(t[["family", "trial", "n", "p_for_fdr", "fdr_pass_10pct_family"]].to_string(index=False, float_format=lambda x: f"{x:.4f}"))


if __name__ == "__main__":
    main()
