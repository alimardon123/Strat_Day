"""Regenerate every table under out/ from data/raw (+ data/ext when present), in order.
Fails (exit 1) on any empty expected output or any *.error file (ACCEPTANCE A32, D7).
`make repeat` runs this a second time and diffs out/ against the first run."""
import glob
import os
import subprocess
import sys

STEPS = [
    ("gate_b_oanda", ["python", "-m", "pipeline.sessions", "oanda", "data/raw/oanda_SPX500_USD.parquet"], "out/gate_b_oanda.log"),
    ("gate_b_histdata", ["python", "-m", "pipeline.sessions", "histdata", "data/raw/histdata_SPXUSD.parquet"], "out/gate_b_histdata.log"),
    ("gate_c", ["python", "-m", "pipeline.reproduce"], "out/gate_c.log"),
    ("gate_e", ["python", "-m", "pipeline.gate_ext"], "out/gate_e.log"),
    ("reconcile", ["python", "-m", "pipeline.reconcile"], "out/reconcile.log"),
    ("insample_d3_d4", ["python", "-m", "pipeline.insample", "2013-01-01", "2020-05-13", "IN-SAMPLE 2013-01..2020-05-13",
                        "out/insample"], "out/insample.log"),
    ("own_account_d5", ["python", "-m", "pipeline.own_account"], "out/own_account.log"),
    ("xmarket_SPXUSD", ["python", "-m", "pipeline.units.xmarket", "--in", "SPXUSD", "--out", "out/xmarket_SPXUSD.csv"], "out/xmarket_SPXUSD.log"),
    ("xmarket_GRXEUR", ["python", "-m", "pipeline.units.xmarket", "--in", "GRXEUR", "--out", "out/xmarket_GRXEUR.csv"], "out/xmarket_GRXEUR.log"),
    ("xmarket_ETXEUR", ["python", "-m", "pipeline.units.xmarket", "--in", "ETXEUR", "--out", "out/xmarket_ETXEUR.csv"], "out/xmarket_ETXEUR.log"),
    ("vrp", ["python", "-m", "pipeline.vrp"], "out/vrp.log"),
    ("flow", ["python", "-m", "pipeline.units.flow", "--in", "data/raw/oanda_SPX500_USD.parquet", "--out", "out/flow_candidates.csv"], "out/flow.log"),
    ("trials", ["python", "-m", "pipeline.trials"], "out/trials.log"),
    ("report", ["python", "-m", "pipeline.report"], "out/report.log"),
]
EXPECTED = ["out/dst_probe_oanda.csv", "out/calendar_oanda.csv", "out/dst_probe_histdata.csv", "out/calendar_histdata.csv",
            "out/gate_c.csv", "out/reconcile_candidates.csv", "out/reconcile_decision.md",
            "out/insample_execution.csv", "out/insample_summary.csv", "out/insample_sizing.csv",
            "out/own_account_summary.csv", "out/own_account_by_year.csv", "out/own_account_by_regime.csv",
            "out/xmarket_SPXUSD.csv", "out/xmarket_GRXEUR.csv", "out/xmarket_ETXEUR.csv",
            "out/vrp_vix_minus_rv.csv", "out/flow_candidates.csv", "PLAYBOOK_0DTE.md", "OWN_ACCOUNT.md"]


def main():
    os.makedirs("out", exist_ok=True)
    for err in glob.glob("out/*.error"):
        os.remove(err)
    for name, cmd, log in STEPS:
        with open(log, "w") as f:
            r = subprocess.run(cmd, stdout=f, stderr=subprocess.STDOUT)
        print(f"{name}: exit {r.returncode}")
        if r.returncode != 0:
            open(log.replace(".log", ".error"), "w").write(f"exit {r.returncode}; see {log}\n")
    bad = [p for p in EXPECTED if not os.path.exists(p) or os.path.getsize(p) == 0] + glob.glob("out/*.error")
    if bad:
        print("FAIL: empty or missing outputs / error files:", bad)
        sys.exit(1)
    print("OK: all expected outputs present and non-empty")


if __name__ == "__main__":
    main()
