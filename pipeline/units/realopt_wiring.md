# realopt_wiring.md — exact hunks for the orchestrator to apply

`pipeline/units/realopt.py` (A41) is written and self-contained; it does not require any other
file to change to be *runnable* (`python -m pipeline.units.realopt --in extended --out
out/realopt_reeval.csv` already works standalone, SKIP path verified: prints `[SKIP] A41 waits
for data/ext/spy_0dte_1min_2024-02_2026-09.csv.gz (DATA.md)`, writes header-only
`out/realopt_reeval.csv`, `out/realopt_reeval_trades.csv` and `out/realopt_calibration.csv`, exit
0). The two hunks below wire it into the fleet the same way `letf` (A38) is already wired, per the
task instructions: I did not edit `pipeline/run_all.py` or `pipeline/report.py` myself. Unlike
`letf_wiring.md`, there is **no `pipeline/trials.py` hunk** here — ACCEPTANCE A41 says explicitly
"the trial count does not grow (these are re-pricings of counted trials, not new trials)", so
nothing in `out/realopt_reeval.csv` or `out/realopt_calibration.csv` is ever added to the trial
family. Each hunk is unified-diff style against the file contents I read; line numbers are from
that read and may have shifted if another coder's edits landed first — match by the surrounding
context lines, not the numbers.

## 1. `pipeline/run_all.py` — three separate edits

### 1a. STEPS: add the `realopt` step after `letf` (before `trials`)

```diff
     ("letf", ["python", "-m", "pipeline.units.letf", "--in", "extended", "--out", "out/letf_candidates.csv"], "out/letf.log"),
+    ("realopt", ["python", "-m", "pipeline.units.realopt", "--in", "extended", "--out", "out/realopt_reeval.csv"], "out/realopt.log"),
     ("trials", ["python", "-m", "pipeline.trials"], "out/trials.log"),
```

### 1b. EXPECTED: add `out/realopt_reeval.csv` (after `out/letf_candidates.csv`; the calibration
     file and the trades file are not gated separately, matching how `gapliq`/`letf`'s own
     `_trades.csv` companions are not listed in `EXPECTED` either — only the primary output per
     unit is)

```diff
             "out/vrp_vix_minus_rv.csv", "out/flow_candidates.csv", "out/fvg_candidates.csv", "out/gapliq_candidates.csv",
             "out/letf_candidates.csv",
+            "out/realopt_reeval.csv",
             "out/trials.csv", "out/options_timevalue.csv",
```

### 1c. stale-output cleanup glob: add `out/realopt_*` alongside `out/fvg_*`/`out/gapliq_*`/
     `out/letf_*` so a rerun cannot leave an orphaned reeval/trades/calibration triple when a
     prior run's file shape changes

```diff
-    for pat in ("out/*.error", "out/insample_*", "out/holdout_*", "out/fullsample_*", "out/fvg_*", "out/gapliq_*",
-                "out/letf_*", "out/trackB_*"):
+    for pat in ("out/*.error", "out/insample_*", "out/holdout_*", "out/fullsample_*", "out/fvg_*", "out/gapliq_*",
+                "out/letf_*", "out/realopt_*", "out/trackB_*"):
         for f in glob.glob(pat):
             os.remove(f)
```

Note: `pipeline.units.realopt` never writes `out/realopt_reeval.csv.error` (see its own module
docstring — A41's failure contract is header-only + exit 0, copied verbatim from A38's letf.py,
not the A32 empty-file+.error+exit-2 convention every other unit uses), so it can never trip
`run_all`'s `out/*.error` gate; the `EXPECTED` entry is satisfied because the header-only file is
never zero bytes (it always has a header row).

## 2. `pipeline/report.py` — three separate edits

### 2a. Add `import io` (needed to parse `out/realopt_calibration.csv`'s two-block format, see
     point 2b below) and `REALOPT_REEVAL_COLS`, `realopt_calibration_blocks`, `realopt_caption`,
     `realopt_labels` (insert after `letf_caption`, before `def describe(label):`)

```diff
 import glob
+import io
 import os
 import re
 import sys

 import numpy as np
 import pandas as pd
```

```diff
 def letf_caption(df):
     """First two sentences of the `spec` column (identical on every row — the fixed pre-
     registration), generated rather than typed (D7)."""
     if "spec" not in df or not len(df):
         return ""
     parts = re.split(r"(?<=\.)\s+", str(df["spec"].iloc[0]).strip())
     return " ".join(parts[:2])


+REALOPT_REEVAL_COLS = ["signal", "cost_label", "n", "n_skipped_missing", "win", "mean_pct_of_premium",
+                       "median_pct", "worst_pct", "model_mean_pct", "label", "p_boot_day", "sharpe_calday"]
+
+
+def realopt_calibration_blocks(path):
+    """Split out/realopt_calibration.csv's two blocks (per-(date,minute,right) table, one blank
+    line, then the by-VIX-tercile/by-minute/overall summary table — pipeline.units.realopt's own
+    convention, see its module docstring point 6) into two DataFrames; the second is empty if the
+    file only ever got a header (the skip path writes no summary block at all)."""
+    text = open(path).read()
+    parts = [p for p in re.split(r"\n\s*\n", text.strip()) if p.strip()]
+    calib = pd.read_csv(io.StringIO(parts[0]))
+    summary = pd.read_csv(io.StringIO(parts[1])) if len(parts) > 1 else pd.DataFrame()
+    return calib, summary
+
+
+def realopt_caption(df):
+    """First two sentences of the `spec` column (identical on every row — the fixed pre-
+    registration), generated rather than typed (D7)."""
+    if "spec" not in df or not len(df):
+        return ""
+    parts = re.split(r"(?<=\.)\s+", str(df["spec"].iloc[0]).strip())
+    return " ".join(parts[:2])
+
+
+def realopt_labels(df):
+    """One generated line per signal x cost row, straight from the `label`/`note` columns
+    themselves (D7: never typed), e.g. '- T1 at +$0.10: model pessimistic here (n=42, real mean
+    +3.10% of premium vs model +5.00%; sub-window, not a verdict).'."""
+    lines = []
+    for _, r in df.iterrows():
+        if r["n"] == 0:
+            lines.append(f"- {r['signal']} at {r['cost_label']}: {r['label']} "
+                         f"(n_skipped_missing={int(r['n_skipped_missing'])}; {r['note']}).")
+            continue
+        lines.append(f"- {r['signal']} at {r['cost_label']}: {r['label']} "
+                     f"(n={int(r['n'])}, real mean {r['mean_pct_of_premium']:+.2f}% of premium vs "
+                     f"model {r['model_mean_pct']:+.2f}%; {r['note']}).")
+    return lines
+
+
 def describe(label):
```

### 2b. Render section 12 (insert in `playbook()`, after the existing `## 11.` letf block, before
     `open("PLAYBOOK_0DTE.md", "w").write("\n".join(L))`)

```diff
         else:
             L += ["Waits for `data/ext/letf_aum_2006_2026.csv`; the unit skipped.", ""]
+    if os.path.exists("out/realopt_reeval.csv"):
+        reeval = pd.read_csv("out/realopt_reeval.csv")
+        L += ["## 12. Real 0DTE prices (A41) — model calibration and re-evaluation, pre-registered "
+              "2026-09-13", ""]
+        if len(reeval):
+            calib, calib_summary = realopt_calibration_blocks("out/realopt_calibration.csv")
+            L += ["### Calibration (diagnostic, no decision): implied k = real bar close ÷ Black-Scholes "
+                  "premium at k=1 × prior-close VIX, by VIX tercile and by minute (`out/realopt_calibration.csv`)",
+                  "",
+                  md(calib_summary, fmt="{:.4f}") if len(calib_summary) else "No calibration rows.", ""]
+            L += [f"{len(calib)} (date, minute, right) calibration rows over {calib['date'].nunique() if len(calib) else 0} "
+                  "sessions." if len(calib) else "", ""]
+            L += ["### Re-evaluation: real 1-minute option bars replace the k×VIX model on every counted "
+                  "trial's sessions ≥ 2024-02-01 (the two pre-registered D4 holdout signals, A39 T1/T2/T3, "
+                  "and any POST-SELECTION row with a per-trade file), at three added-cost rows "
+                  "(`out/realopt_reeval.csv`, per-trade detail in `out/realopt_reeval_trades.csv`)", "",
+                  md(reeval[[c for c in REALOPT_REEVAL_COLS if c in reeval]], fmt="{:.4f}", int_cols=INT_COLS), ""]
+            L += realopt_labels(reeval) + [""]
+            cap = realopt_caption(reeval)
+            if cap:
+                L += [cap, ""]
+            L += ["Sub-window, not a verdict: nothing above is promoted, added to the trial family (A41: "
+                  "\"the trial count does not grow\"), or scored against BH-FDR.", ""]
+        else:
+            L += ["Waits for `data/ext/spy_0dte_1min_2024-02_2026-09.csv.gz`; the unit skipped.", ""]
     open("PLAYBOOK_0DTE.md", "w").write("\n".join(L))
```

## Ambiguities resolved while drafting these hunks

- Section number: the existing file has `## 9.` (fvg, A36), `## 10.` (gapliq, A39) and `## 11.`
  (letf, A38), so A41 is `## 12.`, matching the task's own heading text verbatim ("Real 0DTE
  prices (A41)").
- `out/realopt_reeval.csv` always exists once `pipeline.units.realopt` has run at all (header-only
  until `data/ext/spy_0dte_1min_2024-02_2026-09.csv.gz` lands), so the report-side gate follows
  the exact same two-step pattern as section 11 (`letf`): `os.path.exists(...)` first, then branch
  on `len(reeval)` for the genuine "waits for the data" one-liner the task asked for verbatim
  ("Waits for `data/ext/spy_0dte_1min_2024-02_2026-09.csv.gz`; the unit skipped.").
- `out/realopt_calibration.csv` is read only inside the `len(reeval)` branch (it is only ever
  non-header-only in lockstep with `out/realopt_reeval.csv`, since both are written by the same
  `main()` on the same branch of `pipeline.units.realopt`) — there is deliberately no separate
  `os.path.exists("out/realopt_calibration.csv")` gate, to avoid a report that shows calibration
  numbers while still printing the "waits for the data" sentence for re-evaluation (or vice
  versa), which would read as internally contradictory.
- The two-block calibration csv (per-row table, blank line, summary table — `pipeline.units.
  realopt.write_calibration`'s own convention, see that module's docstring point 6) is parsed by
  splitting on the blank-line boundary rather than adding a second `out/realopt_calibration_
  summary.csv` file, since the amendment's own text explicitly allows "(or a second block)" and
  `pipeline.units.realopt.py` was written to take that reading literally.
- `realopt_labels` prints the model comparison only when `n > 0` (falls back to a shorter line
  naming `n_skipped_missing` when a signal/cost row has zero re-priced trades), mirroring how
  `letf_verdict`/`gapliq_verdict` already guard every `pd.notna(...)` before rendering a verdict
  sentence from a possibly-empty row.
