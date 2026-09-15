"""Regenerate every table under out/ from data/raw (+ data/ext when present), in order.
Fails (exit 1) on any empty expected output or any *.error file (ACCEPTANCE A32, D7).
Stale per-run tables (insample_*, holdout_*) are removed first so `make repeat` can detect
orphans. The holdout (D2) step runs only when the ext minute file exists."""
import glob
import os
import subprocess
import sys

from pipeline import sessions

EXT_MIN = "data/ext/spx_1min_2020-05_2026-09.csv.gz"
STEPS = [
    ("gate_b_oanda", ["python", "-m", "pipeline.sessions", "oanda", "data/raw/oanda_SPX500_USD.parquet"], "out/gate_b_oanda.log"),
    ("gate_b_histdata", ["python", "-m", "pipeline.sessions", "histdata", "data/raw/histdata_SPXUSD.parquet"], "out/gate_b_histdata.log"),
    ("gate_c", ["python", "-m", "pipeline.reproduce"], "out/gate_c.log"),
    ("gate_e", ["python", "-m", "pipeline.gate_ext"], "out/gate_e.log"),
    ("gate_f_etf", ["python", "-m", "pipeline.gate_etf"], "out/gate_f_etf.log"),
    ("reconcile", ["python", "-m", "pipeline.reconcile"], "out/reconcile.log"),
    ("pbo", ["python", "-m", "pipeline.pbo"], "out/pbo.log"),
    ("insample_d3_d4", ["python", "-m", "pipeline.insample", "2013-01-01", "2020-05-13", "IN-SAMPLE 2013-01..2020-05-13",
                        "out/insample"], "out/insample.log"),
    ("holdout_d2", ["python", "-m", "pipeline.insample", "2020-06-01", "2026-09-11", "HOLDOUT 2020-06-01..2026-09-11",
                    "out/holdout"], "out/holdout.log"),
    ("reconcile_holdout", ["python", "-m", "pipeline.reconcile", "holdout"], "out/reconcile_holdout.log"),
    ("fullsample_d4", ["python", "-m", "pipeline.insample", "2013-01-01", "2026-09-11", "IN-SAMPLE + HOLDOUT 2013-01..2026-09-11",
                       "out/fullsample"], "out/fullsample.log"),
    ("own_account_d5", ["python", "-m", "pipeline.own_account"], "out/own_account.log"),
    ("xmarket_SPXUSD", ["python", "-m", "pipeline.units.xmarket", "--in", "SPXUSD", "--out", "out/xmarket_SPXUSD.csv"], "out/xmarket_SPXUSD.log"),
    ("xmarket_GRXEUR", ["python", "-m", "pipeline.units.xmarket", "--in", "GRXEUR", "--out", "out/xmarket_GRXEUR.csv"], "out/xmarket_GRXEUR.log"),
    ("xmarket_ETXEUR", ["python", "-m", "pipeline.units.xmarket", "--in", "ETXEUR", "--out", "out/xmarket_ETXEUR.csv"], "out/xmarket_ETXEUR.log"),
    ("vrp", ["python", "-m", "pipeline.vrp"], "out/vrp.log"),
    ("flow", ["python", "-m", "pipeline.units.flow", "--in", "data/raw/oanda_SPX500_USD.parquet", "--out", "out/flow_candidates.csv"], "out/flow.log"),
    ("fvg", ["python", "-m", "pipeline.units.fvg", "--in", "extended", "--out", "out/fvg_candidates.csv"], "out/fvg.log"),
    ("gapliq", ["python", "-m", "pipeline.units.gapliq", "--in", "extended", "--out", "out/gapliq_candidates.csv"], "out/gapliq.log"),
    ("flatten", ["python", "-m", "pipeline.units.flatten", "--in", "extended", "--out", "out/flatten_candidates.csv"], "out/flatten.log"),
    ("sizing", ["python", "-m", "pipeline.units.sizing", "--in", "extended", "--out", "out/sizing_forward.csv"], "out/sizing.log"),
    ("letf", ["python", "-m", "pipeline.units.letf", "--in", "extended", "--out", "out/letf_candidates.csv"], "out/letf.log"),
    ("realopt", ["python", "-m", "pipeline.units.realopt", "--in", "extended", "--out", "out/realopt_reeval.csv"], "out/realopt.log"),
    ("eventvol", ["python", "-m", "pipeline.units.eventvol", "--in", "extended",
                  "--out", "out/eventvol_candidates.csv"], "out/eventvol.log"),
    ("sellvol", ["python", "-m", "pipeline.units.sellvol", "--in", "extended",
                "--out", "out/sellvol_candidates.csv"], "out/sellvol.log"),
    ("trials", ["python", "-m", "pipeline.trials"], "out/trials.log"),
    ("options_timevalue", ["python", "-m", "pipeline.options"], "out/options_timevalue.log"),
    ("report", ["python", "-m", "pipeline.report"], "out/report.log"),
    ("trackB_rangebars", ["python", "-m", "pipeline.units.rangebars", "--in", "extended", "--out", "out/trackB_rangebars_gate.csv"], "out/trackB_rangebars.log"),
    ("trackB_sweep", ["python", "-m", "pipeline.units.sweep", "--in", "extended", "--out", "out/trackB_sweep_candidates.csv"], "out/trackB_sweep.log"),
    ("trackB_report", ["python", "-m", "pipeline.report_b"], "out/trackB_report.log"),
    ("trackC_report", ["python", "-m", "pipeline.report_c"], "out/trackC_report.log"),
]
EXPECTED = ["out/dst_probe_oanda.csv", "out/calendar_oanda.csv", "out/dst_probe_histdata.csv", "out/calendar_histdata.csv",
            "out/gate_c.csv", "out/gate_e.csv", "out/gate_etf.csv", "out/reconcile_candidates.csv", "out/reconcile_decision.md",
            "out/pbo.csv",
            "out/insample_execution.csv", "out/insample_summary.csv", "out/insample_sizing.csv",
            "out/own_account_summary.csv", "out/own_account_by_year.csv", "out/own_account_by_regime.csv", "out/own_account_bridge.csv",
            "out/xmarket_SPXUSD.csv", "out/xmarket_GRXEUR.csv", "out/xmarket_ETXEUR.csv",
            "out/vrp_vix_minus_rv.csv", "out/flow_candidates.csv", "out/fvg_candidates.csv", "out/gapliq_candidates.csv",
            "out/flatten_candidates.csv",
            "out/letf_candidates.csv",
            "out/realopt_reeval.csv", "out/realopt_calibration.csv",
            "out/eventvol_candidates.csv",
            "out/sellvol_candidates.csv", "out/sellvol_by_year.csv",
            "out/trials.csv", "out/options_timevalue.csv",
            "PLAYBOOK_0DTE.md", "OWN_ACCOUNT.md",
            "out/trackB_rangebars_gate.csv", "out/trackB_sweep_candidates.csv", "out/trackB_decision.csv", "TRACK_B.md",
            "TRACK_C.md"]
EXPECTED_HOLDOUT = ["out/sizing_forward.csv",
                    "out/holdout_summary.csv", "out/holdout_by_year.csv", "out/holdout_pooled.csv",
                    "out/holdout_d4_execution.csv", "out/holdout_d4_summary.csv", "out/holdout_d4_sizing.csv",
                    "out/fullsample_execution.csv", "out/fullsample_summary.csv", "out/fullsample_sizing.csv"]
HOLDOUT_STEPS = {"holdout_d2", "reconcile_holdout", "fullsample_d4", "sizing"}   # ext-only steps (skipped when data/ext is absent)


def main():
    os.makedirs("out", exist_ok=True)
    ext = sessions.ext_present()
    for pat in ("out/*.error", "out/insample_*", "out/holdout_*", "out/fullsample_*", "out/fvg_*", "out/gapliq_*",
                "out/flatten_*", "out/sizing_*", "out/letf_*", "out/realopt_*", "out/eventvol_*", "out/sellvol_*", "out/trackB_*"):
        for f in glob.glob(pat):
            os.remove(f)
    steps = [s for s in STEPS if s[0] not in HOLDOUT_STEPS or ext]
    expected = EXPECTED + (EXPECTED_HOLDOUT if ext else [])
    print(f"ext feed: {'present (manifest + minute file) — holdout step enabled' if ext else 'absent — holdout step skipped (DATA.md)'}")
    for name, cmd, log in steps:
        with open(log, "w") as f:
            r = subprocess.run(cmd, stdout=f, stderr=subprocess.STDOUT)
        print(f"{name}: exit {r.returncode}")
        if r.returncode != 0:
            open(log.replace(".log", ".error"), "w").write(f"exit {r.returncode}; see {log}\n")
    bad = [p for p in expected if not os.path.exists(p) or os.path.getsize(p) == 0] + glob.glob("out/*.error")
    if bad:
        print("FAIL: empty or missing outputs / error files:", bad)
        sys.exit(1)
    print("OK: all expected outputs present and non-empty")


if __name__ == "__main__":
    main()
