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
    ("reconcile", ["python", "-m", "pipeline.reconcile"], "out/reconcile.log"),
    ("insample_d3_d4", ["python", "-m", "pipeline.insample", "2013-01-01", "2020-05-13", "IN-SAMPLE 2013-01..2020-05-13",
                        "out/insample"], "out/insample.log"),
]
EXPECTED = ["out/dst_probe_oanda.csv", "out/calendar_oanda.csv", "out/dst_probe_histdata.csv", "out/calendar_histdata.csv",
            "out/gate_c.csv", "out/reconcile_candidates.csv", "out/reconcile_decision.md",
            "out/insample_execution.csv", "out/insample_summary.csv", "out/insample_sizing.csv"]


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
