"""Unit test for pipeline.units.letf (A38), runnable standalone:

    python -m pipeline.units.test_letf

No pytest dependency (none is used elsewhere in pipeline/); plain asserts, PASS/FAIL printed per
check, matching pipeline.sessions's own gate()-style `__main__` block. Two checks, per the task:
  (a) the demand formula on a 5-row inline fixture (two funds, one day) equals the hand-computed
      value -- exercised through the REAL ingestion path (letf.load_assets -> letf.build_asset_
      features), not a reimplementation of the formula, so a regression in either function fails
      this test.
  (b) the skip path (assets file missing) writes a header-only CSV, never touching out/ or data/.
Both checks write their temporary file(s), if any, under the system temporary directory and remove them
immediately after use -- no fixture is left anywhere persistent (never under out/ or data/).
"""
import os
import shutil
import sys
import tempfile

import numpy as np
import pandas as pd

from pipeline.units import letf



def test_demand_formula():
    """5 rows, two funds (SSO coef=2, SDS coef=6), one unknown ticker (ZZZ, must be ignored):
    prior trading day 2024-01-02 carries the net_assets that feed the demand formula; 2024-01-03
    rows are present (one row per fund per trading day, as DATA.md specifies) but unused by the
    prior-day lookup -- included so the fixture looks like a real slice of the file, not a
    contrived pair. Hand computation: W_prior = 2*1,000,000,000 + 6*400,000,000 = 4,400,000,000;
    D_t = W_prior * r_t = 4,400,000,000 * 0.01 = 44,000,000."""
    fixture = pd.DataFrame([
        ("SSO", "2024-01-02", 100_000_000.0, 10.00, 1_000_000_000.0),
        ("SSO", "2024-01-03", 101_000_000.0, 10.10, 1_020_100_000.0),
        ("SDS", "2024-01-02", 50_000_000.0, 8.00, 400_000_000.0),
        ("SDS", "2024-01-03", 49_000_000.0, 8.20, 401_800_000.0),
        ("ZZZ", "2024-01-02", 1_000_000.0, 5.00, 5_000_000.0),
    ], columns=["ticker", "date", "shares_outstanding", "nav", "net_assets"])
    tmp_dir = tempfile.mkdtemp()
    path = os.path.join(tmp_dir, "letf_demand_fixture.csv")
    try:
        fixture.to_csv(path, index=False)
        known = letf.load_assets(path)
        assert set(known["ticker"]) == {"SSO", "SDS"}, f"unknown ticker not dropped: {sorted(set(known['ticker']))}"

        td = [pd.Timestamp("2024-01-02"), pd.Timestamp("2024-01-03")]
        day_index = pd.DatetimeIndex([pd.Timestamp("2024-01-03")])
        w_prior, has_assets = letf.build_asset_features(day_index, known, td)
        w_expected = 2 * 1_000_000_000.0 + 6 * 400_000_000.0   # 4,400,000,000.0
        assert bool(has_assets.iloc[0]) is True, "has_assets should be True (both funds present on the prior day)"
        assert np.isclose(w_prior.iloc[0], w_expected), f"W_prior {w_prior.iloc[0]} != expected {w_expected}"

        r_t = 0.01
        d_t = float(w_prior.iloc[0] * r_t)
        d_expected = w_expected * r_t   # 44,000,000.0
        assert np.isclose(d_t, d_expected), f"D_t {d_t} != hand-computed {d_expected}"
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)
    return True


def test_skip_path():
    """main() with a deliberately-missing assets_path writes both output files with a header row
    only (matching OUT_COLS/TRADE_COLS exactly) and returns normally (no exception, no out/ or
    data/ writes)."""
    tmp_dir = tempfile.mkdtemp()
    out_path = os.path.join(tmp_dir, "letf_candidates.csv")
    trades_path = os.path.join(tmp_dir, "letf_candidates_trades.csv")
    missing_assets = os.path.join(tmp_dir, "does_not_exist_letf_aum.csv")
    try:
        assert not os.path.exists(missing_assets)
        letf.main("extended", out_path, assets_path=missing_assets)
        assert os.path.exists(out_path), "main() did not write the output CSV on the skip path"
        assert os.path.exists(trades_path), "main() did not write the trades CSV on the skip path"
        res = pd.read_csv(out_path)
        assert list(res.columns) == letf.OUT_COLS, f"header mismatch: {list(res.columns)}"
        assert len(res) == 0, f"expected header-only (0 rows), got {len(res)}"
        tr = pd.read_csv(trades_path)
        assert list(tr.columns) == letf.TRADE_COLS, f"trades header mismatch: {list(tr.columns)}"
        assert len(tr) == 0, f"expected header-only trades (0 rows), got {len(tr)}"
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)
    return True


def main():
    checks = [("demand formula on the 5-row inline fixture", test_demand_formula),
              ("skip path writes header-only outputs (assets file missing)", test_skip_path)]
    ok = True
    for name, fn in checks:
        try:
            fn()
            print(f"[PASS] {name}")
        except AssertionError as e:
            ok = False
            print(f"[FAIL] {name}: {e}")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
