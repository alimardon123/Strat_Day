# eventvol wiring (A42) — hunks for `run_all.py` / `trials.py` / `report.py`

Per the task, `pipeline/units/eventvol.py` and `pipeline/units/test_eventvol.py` are complete and
self-contained (the unit runs standalone, SKIPs cleanly without
`data/ext/spy_0dte_1min_2024-02_2026-09.csv.gz`, and its own test is runnable standalone). This
file is the exact set of hunks a maintainer applies to wire it into `pipeline/run_all.py`,
`pipeline/trials.py` and `pipeline/report.py` — none of those three files are touched by this
change, per the task's instructions (a sibling coder is editing `realopt.py` concurrently and
those three files are shared/COUPLED).

All three hunks below are additive only (no existing line is changed or removed).

## 1. `pipeline/run_all.py` — step `eventvol` after `realopt`

Insert this tuple into `STEPS` immediately after the `realopt` step the sibling coder's A41 wiring
adds (wherever in `STEPS` that ends up — the natural place is right after `letf`/before `trials`,
mirroring this file's existing `gapliq` -> `letf` -> `trials` ordering; ASSUMPTION: the sibling's
step is literally named `"realopt"`, since that is the unit's module name):

```python
    ("realopt", [...]),   # <- sibling coder's A41 wiring (not part of this hunk)
    ("eventvol", ["python", "-m", "pipeline.units.eventvol", "--in", "extended",
                  "--out", "out/eventvol_candidates.csv"], "out/eventvol.log"),
```

Add the new EXPECTED output right after `letf`'s (so a missing/empty file still fails `make all`
even though the unit's own header-only-on-skip contract keeps it non-empty):

```python
EXPECTED = [..., "out/letf_candidates.csv",
            "out/eventvol_candidates.csv",
            "out/trials.csv", "out/options_timevalue.csv", ...]
```

Add `out/eventvol_*` to the per-run stale-output cleanup glob (same list `letf`/`gapliq` are
already in, so a stale eventvol run is removed before the next `make all`, just like every other
per-run unit table):

```python
    for pat in ("out/*.error", "out/insample_*", "out/holdout_*", "out/fullsample_*", "out/fvg_*",
                "out/gapliq_*", "out/letf_*", "out/eventvol_*", "out/trackB_*"):
```

## 2. `pipeline/trials.py` — family `"eventvol"`, three rows when present (family → 39)

Insert immediately after the `letf` block (before the `hold = pd.read_csv(...)` line):

```python
    if os.path.exists("out/eventvol_candidates.csv"):
        # A42: three trials (E1 baseline, E2 FOMC, E3 non-FOMC control), each counted ONCE at
        # cost=$0.10 (mirrors the "one row per trial" filter the fvg/gapliq/letf blocks above
        # apply on their SELECTION window — the $0 and $0.20 rows are a cost-sensitivity sweep,
        # not additional trials); family becomes 39. This file always exists
        # (pipeline.units.eventvol writes it header-only until data/ext/
        # spy_0dte_1min_2024-02_2026-09.csv.gz lands), so a header-only file has zero rows and this
        # loop adds nothing until the real 0DTE file arrives (ACCEPTANCE A42).
        eventvol = pd.read_csv("out/eventvol_candidates.csv")
        for _, x in eventvol[np.isclose(eventvol["cost"], 0.10)].iterrows():
            rows.append(dict(family="eventvol", trial=f"EVENTVOL {x['trial']}", n=x["n"],
                             p=x["p_boot_day"], p_day=x["p_boot_day"]))
```

ASSUMPTION (stated in `eventvol.py`'s own SPEC_NOTE too): `eventvol_candidates.csv` has no
`p_boot_month` column (only `p_boot_day`, per the task's exact column list), so `p` is set
directly from `p_boot_day` here — the same pattern the existing `flow`/`xmarket` blocks above
already use (`p=x["p_boot_day"]`), not the `p_boot_month` pattern the `fvg`/`gapliq`/`letf` blocks
use. `t["p_for_fdr"] = t["p"].fillna(t["p_day"]).fillna(1.0)` (unchanged, a few lines below) needs
no edit: it already falls back correctly when `p` is itself `p_boot_day`.

## 3. `pipeline/report.py` — section 13 "Event-day long volatility (A42)"

Insert these two function definitions after `letf_caption` (i.e. right before `def describe(label):`):

```python
EVENTVOL_COLS = ["trial", "cost", "n", "n_skipped", "win", "mean_pct", "median_pct", "worst_pct",
                 "mean_usd", "p_boot_day", "sharpe_calday", "dsr_N39", "e2_minus_e3_pct",
                 "p_e2_vs_e3", "underpowered"]


def eventvol_verdict(df):
    """Generated verdict for the A42 event-day long-volatility family: E1 (baseline, LOW prior,
    expected negative) is reported for context; E2 (FOMC) is UNDERPOWERED by construction
    (n ~ 20 < 200) at every cost and is never promoted on this sample regardless of sign or
    significance; E2 - E3 (LOW-MEDIUM prior) is the pre-registered comparison, reported per cost."""
    e2 = df[df["trial"] == "E2"]
    lines = []
    for _, row in e2.iterrows():
        diff = row["e2_minus_e3_pct"]
        sign = "positive" if pd.notna(diff) and diff > 0 else ("negative" if pd.notna(diff) else "n/a")
        diff_str = f"{diff:.4f}" if pd.notna(diff) else "n/a"
        p_str = f"{row['p_e2_vs_e3']:.4f}" if pd.notna(row["p_e2_vs_e3"]) else "n/a"
        lines.append(f"at cost ${row['cost']:.2f}: E2 - E3 = {diff_str} pct-pts ({sign}), p_e2_vs_e3 = {p_str}")
    detail = "; ".join(lines) if lines else "no E2 rows"
    return (f"E2 (FOMC) is UNDERPOWERED by construction (n ~ 20 < 200) at every cost and is never "
            f"promoted on this sample regardless of sign or significance. E2 - E3: {detail}. "
            f"Nothing in this family is promoted here (pre-registered as reported-only, A42).")


def eventvol_caption(df):
    """First two sentences of the `spec` column (identical on every row — the fixed pre-
    registration), generated rather than typed (D7)."""
    if "spec" not in df or not len(df):
        return ""
    parts = re.split(r"(?<=\.)\s+", str(df["spec"].iloc[0]).strip())
    return " ".join(parts[:2])
```

Insert this block immediately before the final `open("PLAYBOOK_0DTE.md", "w").write("\n".join(L))`
line at the end of `playbook()` — i.e. after whichever section the sibling coder's A41 `realopt`
wiring adds as "section 12" (ASSUMPTION: that section is inserted before this point too; if the
sibling instead appends section 12 at the very end, insert this eventvol block after theirs so
this stays "section 13"):

```python
    if os.path.exists("out/eventvol_candidates.csv"):
        eventvol = pd.read_csv("out/eventvol_candidates.csv")
        L += ["## 13. Event-day long volatility (A42) — pre-registered 2026-09-13, 3 trials", ""]
        if len(eventvol):
            L += ["3 trials (E1 baseline every session, E2 FOMC statement days, E3 the E2 rule on "
                  "every non-FOMC session) from `pipeline.units.eventvol` "
                  "(`out/eventvol_candidates.csv`), each at three round-trip costs ($0, $0.10, "
                  "$0.20 per two-leg trade). All three are counted trials (family 36 -> 39); only "
                  "the $0.10 row per trial is counted in the trial family ledger "
                  "(`pipeline/trials.py`, `out/trials.csv`) — the $0 and $0.20 rows are a cost "
                  "sensitivity, not additional trials. This is the whole file's one out-of-sample "
                  "window by construction (2024-02-01 onward), not a CONTEXT/SELECTION/HOLDOUT "
                  "split.", ""]
            L += [md(eventvol[[c for c in EVENTVOL_COLS if c in eventvol]], fmt="{:.4f}", int_cols=INT_COLS), "",
                  eventvol_verdict(eventvol), ""]
            cap = eventvol_caption(eventvol)
            if cap:
                L += [cap, ""]
        else:
            L += ["Waits for `data/ext/spy_0dte_1min_2024-02_2026-09.csv.gz`; the unit skipped.", ""]
    open("PLAYBOOK_0DTE.md", "w").write("\n".join(L))
```

(The last line, `open("PLAYBOOK_0DTE.md", ...)`, already exists at the end of `playbook()` — it is
repeated here only to show where the new block ends relative to it; do not duplicate it.)

## Verification these hunks were designed against

- `pipeline/run_all.py` (read as of this task, `git show HEAD:pipeline/run_all.py`): `STEPS`/
  `EXPECTED`/the cleanup-glob tuple in `main()`, as they stood before any `realopt` step existed.
- `pipeline/trials.py`: the `fvg`/`gapliq`/`letf` family blocks (identical `if os.path.exists(...)`
  pattern), `hold = pd.read_csv(...)` immediately after the `letf` block.
- `pipeline/report.py`: `letf_caption`/`describe`, and the `## 11. Leveraged-ETF...` block ending
  at `open("PLAYBOOK_0DTE.md", "w").write(...)` — the last thing `playbook()` does, as it stood
  before any `realopt`/A41 "section 12" wiring existed.

None of `run_all.py`, `trials.py`, `report.py` are modified by this task; a maintainer applies the
hunks above by hand once `realopt.py`'s own wiring has landed (so the `STEPS`/section-number
context lines above match the file on disk at that time).
