"""Phase 2 gate (e) — prove the ext (holdout) data path BEFORE real data arrives (Phase 4
defect 1). Builds a synthetic data/ext in the scratch directory from the Oanda feed itself:
  (1) IDENTITY: Oanda 2019-06-01→2020-05-13 written as a SPY file (prices ÷ 10, UTC stamps, an
      empty dividends file, manifest instrument SPY); the pipeline run on Oanda-to-2019-05-31 +
      that ext file must reproduce every candidate's trade table on 2019-06→2020-05 EXACTLY.
  (2) DIVIDEND: a synthetic ex-date must shift that day's reference close by the dividend and
      nothing else.
  (3) ROLL: a declared ES roll date must drop that session from every prior-close signal.
  (4) REFUSAL: no manifest → refuse; declared instrument vs price level mismatch → refuse.
Writes out/gate_e.csv.
"""
import gzip
import json
import os
import shutil
import tempfile

import numpy as np
import pandas as pd

from pipeline import sessions, signals

CUT = pd.Timestamp("2019-06-01")


def make_synthetic(tmp):
    o = pd.read_parquet("data/raw/oanda_SPX500_USD.parquet")
    base_path = os.path.join(tmp, "oanda_trunc.parquet")
    o[o["ts_utc"] < CUT.tz_localize("UTC")].to_parquet(base_path, index=False)
    ext_dir = os.path.join(tmp, "ext")
    os.makedirs(ext_dir)
    e = o[o["ts_utc"] >= CUT.tz_localize("UTC")].copy()
    e["ts"] = e["ts_utc"].dt.tz_localize(None).dt.strftime("%Y-%m-%d %H:%M:%S")
    for c in ("open", "high", "low", "close"):
        e[c] = e[c] / 10.0
    with gzip.open(os.path.join(ext_dir, "spx_1min_2019-06_2020-05.csv.gz"), "wt") as f:
        e[["ts", "open", "high", "low", "close", "volume"]].to_csv(f, index=False)
    pd.DataFrame(columns=["ex_date", "amount"]).to_csv(os.path.join(ext_dir, "spy_dividends.csv"), index=False)
    json.dump({"instrument": "SPY", "source": "synthetic from Oanda (gate e)", "adjusted": False, "roll_dates": []},
              open(os.path.join(ext_dir, "ext_manifest.json"), "w"))
    return base_path, ext_dir


def main():
    os.makedirs("out", exist_ok=True)
    vix = pd.read_parquet("data/raw/vix_daily.parquet")
    td = sessions.trading_days_from_vix()
    results = []
    tmp = tempfile.mkdtemp(prefix="gate_e_")
    try:
        base_path, ext_dir = make_synthetic(tmp)
        native, _ = sessions.build("oanda", "data/raw/oanda_SPX500_USD.parquet", td)
        ext_frame, _, meta = sessions.build_extended(base_path, ext_dir, td)
        results.append(("ext feed loaded through the manifest as SPY and rescaled ×10", meta is not None and meta["instrument"] == "SPY"))
        dn = signals.day_table(native, vix, trading_days=td)
        de = signals.day_table(ext_frame, vix, dividends=meta["dividends"], trading_days=td, roll_dates=meta["roll_dates"])
        fixed_n = {e: signals.fixed_thresholds(dn, e) for e in (900, 930)}
        fixed_e = {e: signals.fixed_thresholds(de, e) for e in (900, 930)}
        results.append(("frozen thresholds identical on the extended frame", all(np.allclose(fixed_n[e], fixed_e[e]) for e in (900, 930))))
        tn = signals.all_candidates(dn, fixed_n)
        te = signals.all_candidates(de, fixed_e)
        w = lambda t: t[(t["date"] >= CUT) & (t["date"] <= "2020-05-13")].sort_values(["candidate", "date"]).reset_index(drop=True)  # noqa: E731
        a, b = w(tn), w(te)
        same_shape = len(a) == len(b) and (a["candidate"].to_numpy() == b["candidate"].to_numpy()).all() and (a["date"].to_numpy() == b["date"].to_numpy()).all()
        same_vals = same_shape and np.allclose(a[["entry_px", "exit_px", "ret_pct", "pts"]].to_numpy(), b[["entry_px", "exit_px", "ret_pct", "pts"]].to_numpy(), atol=1e-6)
        results.append((f"IDENTITY: {len(a)} native trades vs {len(b)} via the ext path on 2019-06→2020-05, all prices/returns equal", bool(same_vals)))
        # (2) dividend
        exd = de.loc[CUT:].index[10]
        dd = signals.day_table(ext_frame, vix, dividends=pd.Series([13.9], index=[exd]), trading_days=td)
        moved = np.isclose(dd.loc[exd, "prev_close"], de.loc[exd, "prev_close_raw"] - 13.9)
        others = np.allclose(dd["prev_close"].drop(exd).fillna(-1), de["prev_close"].drop(exd).fillna(-1))
        results.append(("DIVIDEND: reference close shifted by the dividend on the ex-date only", bool(moved and others)))
        # (3) roll
        rd = de.loc[CUT:].index[20]
        dr = signals.day_table(ext_frame, vix, trading_days=td, roll_dates=[rd])
        cr = signals.candidate(dr, 930, "both", "vixmove_lit")
        gr = signals.gap_up_call(dr)
        results.append(("ROLL: declared roll date excluded from prior-close signals", bool((cr["date"] != rd).all() and (gr["date"] != rd).all() and not dr.loc[rd, "ref_ok"])))
        # (4) refusal
        refused = False
        try:
            sessions.load_ext(os.path.join(tmp, "nowhere"))
        except FileNotFoundError:
            refused = True
        bad_dir = os.path.join(tmp, "bad")
        shutil.copytree(ext_dir, bad_dir)
        json.dump({"instrument": "ES"}, open(os.path.join(bad_dir, "ext_manifest.json"), "w"))
        mismatch = False
        try:
            sessions.load_ext(bad_dir)
        except ValueError:
            mismatch = True
        results.append(("REFUSAL: missing manifest refused; declared ES on SPY-level prices refused", refused and mismatch))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    for name, ok in results:
        print(f"[{'PASS' if ok else 'FAIL'}] {name}")
    print("GATE (e):", "PASS" if all(ok for _, ok in results) else "FAIL")
    pd.DataFrame(results, columns=["check", "ok"]).to_csv("out/gate_e.csv", index=False)


if __name__ == "__main__":
    main()
