# letf_wiring.md — exact hunks for the orchestrator to apply

`pipeline/units/letf.py` (A38) is written and self-contained; it does not require any other file
to change to be *runnable* (`python -m pipeline.units.letf --in extended --out
out/letf_candidates.csv` already works standalone, SKIP path verified). The three hunks below wire
it into the fleet the same way `gapliq` (A39) is already wired, per the task instructions: I did
not edit `pipeline/trials.py`, `pipeline/run_all.py` or `pipeline/report.py` myself because another
coder is editing them concurrently. Each hunk is unified-diff style against the file contents I
read; line numbers are from that read and may have shifted if the other coder's edits landed
first — match by the surrounding context lines, not the numbers.

## 1. `pipeline/trials.py` — add the `letf` family (insert after the existing `gapliq` block, i.e.
   directly before the `hold = pd.read_csv("out/holdout_summary.csv" ...)` line)

```diff
     if os.path.exists("out/gapliq_candidates.csv"):
         # A39: only the SELECTION-window rows are trials (mirrors the fvg block above); CONTEXT is
         # background and HOLDOUT is these same 3 trials' out-of-sample rows, reported in the gapliq
         # table, not re-counted.
         gapliq = pd.read_csv("out/gapliq_candidates.csv")
         for _, x in gapliq[gapliq["window"] == "SELECTION"].iterrows():
             rows.append(dict(family="gapliq", trial=f"GAPLIQ {x['trial']}", n=x["n"], p=x["p_boot_month"], p_day=x["p_boot_day"]))
+    if os.path.exists("out/letf_candidates.csv"):
+        # A38: only the SELECTION-window row is a trial (mirrors the fvg/gapliq blocks above); this
+        # file always exists (pipeline.units.letf writes it header-only until data/ext/
+        # letf_aum_2006_2026.csv lands), so a header-only file has zero rows and this loop adds
+        # nothing until the assets file arrives -- the family count grows to 37 only when the row
+        # exists (ACCEPTANCE A38).
+        letf = pd.read_csv("out/letf_candidates.csv")
+        for _, x in letf[letf["window"] == "SELECTION"].iterrows():
+            rows.append(dict(family="letf", trial=f"LETF {x['trial']}", n=x["n"], p=x["p_boot_month"], p_day=x["p_boot_day"]))
     hold = pd.read_csv("out/holdout_summary.csv") if os.path.exists("out/holdout_summary.csv") else None
```

## 2. `pipeline/run_all.py` — three separate edits

### 2a. STEPS: add the `letf` step after `gapliq` (before `trials`)

```diff
     ("gapliq", ["python", "-m", "pipeline.units.gapliq", "--in", "extended", "--out", "out/gapliq_candidates.csv"], "out/gapliq.log"),
+    ("letf", ["python", "-m", "pipeline.units.letf", "--in", "extended", "--out", "out/letf_candidates.csv"], "out/letf.log"),
     ("trials", ["python", "-m", "pipeline.trials"], "out/trials.log"),
```

### 2b. EXPECTED: add `out/letf_candidates.csv` (after `out/gapliq_candidates.csv`)

```diff
             "out/vrp_vix_minus_rv.csv", "out/flow_candidates.csv", "out/fvg_candidates.csv", "out/gapliq_candidates.csv",
+            "out/letf_candidates.csv",
             "out/trials.csv", "out/options_timevalue.csv",
```

### 2c. stale-output cleanup glob: add `out/letf_*` alongside `out/fvg_*`/`out/gapliq_*` so a rerun
     cannot leave an orphaned candidates/trades pair when a prior run's file shape changes

```diff
-    for pat in ("out/*.error", "out/insample_*", "out/holdout_*", "out/fullsample_*", "out/fvg_*", "out/gapliq_*"):
+    for pat in ("out/*.error", "out/insample_*", "out/holdout_*", "out/fullsample_*", "out/fvg_*", "out/gapliq_*", "out/letf_*"):
         for f in glob.glob(pat):
             os.remove(f)
```

Note: `pipeline.units.letf` never writes `out/letf_candidates.csv.error` (see its own module
docstring — A38's failure contract is header-only + exit 0, not the A32 empty-file+.error+exit-2
convention every other unit uses), so it can never trip `run_all`'s `out/*.error` gate; the
`EXPECTED` entry is satisfied because the header-only file is never zero bytes (it always has a
header row).

## 3. `pipeline/report.py` — three separate edits

### 3a. Add `LETF_COLS`, `letf_verdict`, `letf_caption` (insert after `gapliq_caption`, before
     `def describe(label):`)

```diff
 def gapliq_caption(df):
     """First two sentences of the `spec` column (identical on every row — the fixed pre-
     registration), generated rather than typed (D7)."""
     if "spec" not in df or not len(df):
         return ""
     parts = re.split(r"(?<=\.)\s+", str(df["spec"].iloc[0]).strip())
     return " ".join(parts[:2])


+LETF_COLS = ["trial", "n_sessions_with_assets", "n_signal", "n_skipped", "n", "win", "net_pts_cost1",
+             "net_pts_cost2", "net_pct_cost1", "worst_trade_pts_cost1", "worst_day_pts_cost1", "sharpe_calday",
+             "p_boot_day", "p_boot_month", "control_mean_pts_cost1", "frac_seeds_beaten",
+             "magnitude_row_net_pts", "beats_magnitude_row", "opt_mean_pct_s1", "dsr_N37"]
+
+
+def letf_verdict(sub):
+    """Generated per-window verdict for the A38 letf trial: the same four programmatic survival
+    checks as fvg_verdict/gapliq_verdict (net > 0 at 1 pt, p_day < 0.05, excess over the day-
+    selection control > 0, n >= 200; DSR at N=37 is reported in the table, not a survival condition
+    here either), PLUS the amendment's own kill rule (net <= 0 at 1 pt on the holdout, OR not above
+    the day-selection control, OR not above the price-only magnitude row)."""
+    row = sub.iloc[0]
+    net_pos = bool(row["net_pts_cost1"] > 0) if pd.notna(row["net_pts_cost1"]) else False
+    p_sig = bool(row["p_boot_day"] < 0.05) if pd.notna(row["p_boot_day"]) else False
+    excess = row["net_pts_cost1"] - row["control_mean_pts_cost1"]
+    beats_control = bool(excess > 0) if pd.notna(excess) else False
+    n_ok = bool(row["n"] >= 200)
+    beats_mag = bool(row["beats_magnitude_row"]) if pd.notna(row.get("beats_magnitude_row")) else False
+    survives = net_pos and p_sig and beats_control and n_ok
+    killed = (not net_pos) or (not beats_control) or (not beats_mag)
+    return (f"net {'>' if net_pos else '<='} 0 at 1 pt, p_day {'<' if p_sig else '>='} 0.05, excess over the "
+            f"day-selection control {'>' if beats_control else '<='} 0, n {'>=' if n_ok else '<'} 200 -> "
+            f"{'SURVIVES' if survives else 'does not survive'} the four programmatic checks (DSR at N=37 is "
+            f"reported in the table above, not a survival condition). Beats the price-only magnitude row "
+            f"(`15:30|both|mag`): {'yes' if beats_mag else 'no'}. A38 kill rule (net <= 0 at 1 pt, OR not above "
+            f"the day-selection control, OR not above the magnitude row): {'KILLED' if killed else 'not triggered'}.")
+
+
+def letf_caption(df):
+    """First two sentences of the `spec` column (identical on every row — the fixed pre-
+    registration), generated rather than typed (D7)."""
+    if "spec" not in df or not len(df):
+        return ""
+    parts = re.split(r"(?<=\.)\s+", str(df["spec"].iloc[0]).strip())
+    return " ".join(parts[:2])
+
+
 def describe(label):
```

### 3b. Render section 11 (insert in `playbook()`, after the existing `## 10.` gapliq block, before
     `open("PLAYBOOK_0DTE.md", "w").write("\n".join(L))`)

```diff
         cap = gapliq_caption(gapliq)
         if cap:
             L += [cap, ""]
+    if os.path.exists("out/letf_candidates.csv"):
+        letf = pd.read_csv("out/letf_candidates.csv")
+        L += ["## 11. Leveraged-ETF close rebalancing (A38, owner's option C) — pre-registered 2026-09-13, 1 trial", ""]
+        if len(letf):
+            L += ["1 trial (`15:30|both|letf_demand`) from `pipeline.units.letf` (`out/letf_candidates.csv`), "
+                  "reported on three windows, each over sessions with leveraged-ETF assets data only. Only the "
+                  "SELECTION-window row is counted in the trial family (`pipeline/trials.py`, `out/trials.csv`); "
+                  "CONTEXT is background and HOLDOUT is this same trial's out-of-sample row, reported here, not "
+                  "double-counted.", ""]
+            for win_name, win_label in (("CONTEXT", "CONTEXT (2005-01-01 → 2012-12-31)"),
+                                         ("SELECTION", "SELECTION (2013-01-01 → 2020-05-13) — counted in the trial family"),
+                                         ("HOLDOUT", "HOLDOUT (2020-07-27 → 2026-09-11)")):
+                sub = letf[letf["window"] == win_name]
+                if not len(sub):
+                    continue
+                L += [f"### {win_label}", "",
+                      md(sub[[c for c in LETF_COLS if c in sub]], fmt="{:.4f}", int_cols=INT_COLS), "",
+                      letf_verdict(sub), ""]
+            cap = letf_caption(letf)
+            if cap:
+                L += [cap, ""]
+        else:
+            L += ["Waits for `data/ext/letf_aum_2006_2026.csv`; the unit skipped.", ""]
     open("PLAYBOOK_0DTE.md", "w").write("\n".join(L))
```

## Ambiguities resolved while drafting these hunks

- Section number: the existing file already has `## 9.` (fvg, A36) and `## 10.` (gapliq, A39), so
  A38 is `## 11.`, matching the task's own heading text verbatim.
- `out/letf_candidates.csv` always exists once `pipeline.units.letf` has run at all (header-only
  until the assets file lands), so the report-side gate cannot be a plain `os.path.exists(...)`
  the way fvg's/gapliq's sections are (those files also always exist once their units have run —
  but I followed the same `os.path.exists` gate for consistency, then branched on `len(letf)` for
  the actual "waits for the data" one-liner, since that is what genuinely distinguishes "not yet
  runnable" from "ran with zero rows for some other reason" is not otherwise observable here and a
  header-only file is the only zero-row case this unit ever produces).
- `pipeline/trials.py`'s new block is placed after the `gapliq` block and before the `hold = ...`
  line, matching the file's existing top-to-bottom family order (reconcile/momentum, xmarket, flow,
  fvg, gapliq, then holdout) with `letf` appended last among the per-unit families, consistent with
  A38 being the last-registered family (A39 already occupies the slot immediately before holdout).
