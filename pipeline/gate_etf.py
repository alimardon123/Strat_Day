"""Gate (f) — the ETF/vol panel that feeds S13 and its A13 VXX/VXZ bridge, guarding against the
judge's B1 finding: `pipeline.own_account.bridge()` was scaling each ext series onto the Kaggle
series by testing whether the last Kaggle date is IN the ext index rather than whether the ext
VALUE there is real. For vxx/vxz the date is in range (the pivot's index is the union across all
29 tickers) but the value is NaN (the Series B notes start 2018-01-25, long after the Kaggle
mirror ends 2017-11-10), so the scale was NaN and the whole post-2017 vxx/vxz series silently
vanished; the `vxx_new`/`vxz_new` guard in `build_sleeves` never fired and S13 ran on VIXY/VIXM
for the entire 2018->2026 leg without printing a new-note bridge correlation at all.

Checks (writes out/gate_etf.csv; [PASS]/[FAIL]/[SKIP] lines; "GATE (f): PASS|FAIL"; exit 0 only
if nothing FAILed):
  (a) every ticker in the ext panel survives `etf_closes()` with its last non-NaN date equal to
      the panel's last date (2026-09-11) -- the check that would have caught B1 directly;
  (b) all 29 required tickers (own_account.UNIVERSE + vxx, vxz, vixy, vixm) are present;
  (c) the A13 bridge table (`splice_vol` on vxx and vxz) has exactly 4 rows, each decided
      `bridged` or `refused (...)` from a real (non-NaN) correlation -- computed in-process, the
      same call `own_account.build_sleeves` makes, not the pipeline's own_account_bridge.csv;
  (d) the spliced VXX series has no NaN after 2017-11-10 and, from its decided source onward,
      its returns equal that source's own returns exactly (Series B's if the new pair was
      bridged, VIXY's for the whole post period if it was refused -- read off the actual
      decision, never assumed).
If data/ext (or an etf_daily_*.csv.gz panel inside it) is absent the pipeline still runs on the
Kaggle-only panel with none of the above applicable; the gate prints [SKIP] and exits 0.
"""
import os
from glob import glob

import numpy as np
import pandas as pd

from pipeline import own_account as oa

REQUIRED_TICKERS = sorted(set(oa.UNIVERSE) | {"vxx", "vxz", "vixy", "vixm"})
CUT = pd.Timestamp("2017-11-10")
SERIES_B_START = pd.Timestamp("2018-01-25")


def _finish(results):
    for name, status in results:
        print(f"[{status}] {name}")
    ok = all(status != "FAIL" for _, status in results)
    print("GATE (f):", "PASS" if ok else "FAIL")
    pd.DataFrame(results, columns=["check", "status"]).assign(ok=lambda d: d["status"] != "FAIL").to_csv(
        "out/gate_etf.csv", index=False)
    if not ok:
        raise SystemExit(1)


def main():
    os.makedirs("out", exist_ok=True)
    results = []
    ext_files = sorted(glob("data/ext/etf_daily_*.csv.gz"))
    if not os.path.isdir("data/ext") or not ext_files:
        results.append(("data/ext with an etf_daily_*.csv.gz panel present (pipeline must still run without it)", "SKIP"))
        _finish(results)
        return

    ext_tickers = sorted(pd.read_csv(ext_files[0], usecols=["ticker"])["ticker"].unique())
    C, note = oa.etf_closes()
    panel_end = C.index.max()

    # (b) all 29 required tickers present
    missing = [t for t in REQUIRED_TICKERS if t not in C.columns]
    results.append((f"{len(REQUIRED_TICKERS)} required tickers present in the panel ({note}); missing: {missing or 'none'}",
                     "FAIL" if missing else "PASS"))

    # (a) every ext-panel ticker survives etf_closes() through the panel's last date -- the B1 check
    stale = {t: (str(C[t].dropna().index.max().date()) if t in C and C[t].notna().any() else "all-NaN/missing")
             for t in ext_tickers if t not in C.columns or C[t].dropna().index.max() != panel_end}
    results.append((f"every ext ticker's last non-NaN date == panel end ({panel_end.date()}); stale: {stale or 'none'}",
                     "FAIL" if stale else "PASS"))

    # (c) the A13 bridge table: 4 rows, each a real decision off a real correlation
    Cs = oa.split_new_notes(C.copy())
    bridge = []
    vxx, rx = oa.splice_vol(Cs, "vxx", "vxx_new", "vixy")
    _, rz = oa.splice_vol(Cs, "vxz", "vxz_new", "vixm")
    bridge.extend(rx)
    bridge.extend(rz)
    summary = {r["pair"]: (round(r["daily_return_corr"], 4) if r["daily_return_corr"] == r["daily_return_corr"] else None, r["decision"])
               for r in bridge}
    bad = [p for p, (c, d) in summary.items() if c is None or not (d == "bridged" or d.startswith("refused"))]
    results.append((f"bridge table has 4 rows, each bridged/refused off a printed correlation: {summary}",
                     "FAIL" if (len(bridge) != 4 or bad) else "PASS"))

    # (d) the spliced VXX series: no gap after 2017-11-10, matches its decided source exactly
    new_row = next((r for r in rx if r["pair"].startswith("new_")), None)
    if new_row is None:
        results.append(("spliced VXX has a new-pair bridge row to decide against (B1 regression: none found -- "
                         "vxx_new was never split out of the panel)", "FAIL"))
    else:
        decision = new_row["decision"]
        post = vxx.loc[vxx.index > CUT]
        no_gap = bool(post.notna().all()) and bool(len(post)) and post.index.max() == panel_end
        r_spliced = vxx.pct_change()
        if decision == "bridged":
            ref, since, ref_label = Cs["vxx_new"].pct_change(), SERIES_B_START, "real Series B VXX"
        else:
            ref, since, ref_label = Cs["vixy"].pct_change(), CUT, "VIXY proxy"
        idx = r_spliced.index[r_spliced.index >= since].intersection(ref.dropna().index)
        matches = len(idx) > 0 and bool(np.allclose(r_spliced.reindex(idx), ref.reindex(idx), atol=1e-9))
        results.append((f"spliced VXX (new pair {decision}) has no NaN after {CUT.date()} and its returns from "
                         f"{since.date()} equal {ref_label}'s ({len(idx)} days checked): no_gap={no_gap} match={matches}",
                         "PASS" if (no_gap and matches) else "FAIL"))

    _finish(results)


if __name__ == "__main__":
    main()
