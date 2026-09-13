"""Unit test for pipeline.units.realopt (A41), runnable standalone:

    python -m pipeline.units.test_realopt

No pytest dependency (none is used elsewhere in pipeline/); plain asserts, PASS/FAIL printed per
check, matching pipeline.units.test_letf's own `__main__` block. Three checks, per the task:
  (a) implied_k arithmetic on a 3-row inline fixture with a hand-computed model premium --
      exercised through the REAL functions (`realopt.model_premium` / `realopt.implied_k`), not a
      reimplementation, so a regression in either fails this test. Every row uses
      mins_to_close=0 (last-minute expiry) so the Black-Scholes premium reduces EXACTLY to
      intrinsic value (`research/thread_B_inversion/step15_odte.py`'s bs_call/bs_put both special-
      case T<=1e-9 to `max(S-K, 0.0)` / `max(K-S, 0.0)`) -- a model premium computable by hand
      without reimplementing the normal CDF.
  (b) strike selection (`realopt.nearest_listed`) picks the nearest LISTED strike to the unrounded
      2% ITM target (`realopt.target_strike`), including a case where the target lands well
      outside the listed range.
  (c) the skip path (option file missing) writes header-only outputs to a temp dir (no `out/` or
      `data/` path is ever touched).
All three checks write their temporary file(s), if any, under the system temporary directory and
remove them immediately after use -- no fixture is left anywhere persistent.
"""
import os
import shutil
import sys
import tempfile

import numpy as np
import pandas as pd

from pipeline.units import realopt


def test_implied_k_arithmetic():
    """3 rows, S=500 dollars throughout, mins_to_close=0 on every row so the model premium is
    exactly intrinsic (hand-computed): row 1 a 2% ITM call (K=490, intrinsic 10.0) with a real
    close of 12.0 -> implied_k = 1.2; row 2 a 2% ITM put (K=510, intrinsic 10.0) with a real close
    of 8.0 -> implied_k = 0.8; row 3 the same call with NO real bar (missing) -> implied_k must be
    NaN, never a crash or a fabricated number."""
    fixture = [
        dict(S=500.0, K=490.0, mins_to_close=0, vix_prev=20.0, kind="c", real_close=12.0, expected_k=1.2),
        dict(S=500.0, K=510.0, mins_to_close=0, vix_prev=20.0, kind="p", real_close=8.0, expected_k=0.8),
        dict(S=500.0, K=490.0, mins_to_close=0, vix_prev=15.0, kind="c", real_close=None, expected_k=None),
    ]
    for row in fixture:
        model = realopt.model_premium(row["S"], row["K"], row["mins_to_close"], row["vix_prev"], row["kind"])
        assert np.isclose(model, 10.0), f"hand-computed model premium at mins_to_close=0 is intrinsic (10.0), got {model}"
        k = realopt.implied_k(row["real_close"], model)
        if row["expected_k"] is None:
            assert np.isnan(k), f"expected NaN implied_k for a missing real close, got {k}"
        else:
            assert np.isclose(k, row["expected_k"]), f"implied_k {k} != hand-computed {row['expected_k']}"
    return True


def test_strike_selection():
    """`realopt.nearest_listed` picks the nearest LISTED strike to `realopt.target_strike`'s
    unrounded 2% ITM target, both when the target is itself listed and when it falls well outside
    the listed range (must still return the closest available, not None or a crash)."""
    target_c = realopt.target_strike(500.0, "c")   # 500 * 0.98 = 490.0 exactly
    assert np.isclose(target_c, 490.0), f"2% ITM call target should be 490.0, got {target_c}"
    K = realopt.nearest_listed([480.0, 485.0, 490.0, 495.0, 500.0], target_c)
    assert K == 490.0, f"nearest listed strike to an exactly-listed target should be itself, got {K}"

    target_p = realopt.target_strike(503.0, "p")   # 503 * 1.02 = 513.06
    assert np.isclose(target_p, 513.06), f"2% ITM put target should be 513.06, got {target_p}"
    K2 = realopt.nearest_listed([480.0, 486.0, 493.0, 500.0], target_p)   # nearest to 513.06 is 500.0
    assert K2 == 500.0, f"nearest listed strike to a target outside the range should be the closest end, got {K2}"

    assert realopt.nearest_listed([], target_c) is None, "no listed strikes at all must return None, not crash"
    return True


def test_skip_path():
    """main() with a deliberately-missing option file writes all three output files with a header
    row only (matching OUT_COLS/TRADE_COLS/CALIB_COLS exactly) and returns normally (no exception,
    no out/ or data/ writes)."""
    tmp_dir = tempfile.mkdtemp()
    out_path = os.path.join(tmp_dir, "realopt_reeval.csv")
    trades_path = os.path.join(tmp_dir, "realopt_reeval_trades.csv")
    calib_path = os.path.join(tmp_dir, "realopt_calibration.csv")
    missing_ext = os.path.join(tmp_dir, "does_not_exist_spy_0dte.csv.gz")
    try:
        assert not os.path.exists(missing_ext)
        realopt.main("extended", out_path, ext_path=missing_ext, calib_out=calib_path)
        assert os.path.exists(out_path), "main() did not write the re-evaluation CSV on the skip path"
        assert os.path.exists(trades_path), "main() did not write the trades CSV on the skip path"
        assert os.path.exists(calib_path), "main() did not write the calibration CSV on the skip path"
        res = pd.read_csv(out_path)
        assert list(res.columns) == realopt.OUT_COLS, f"header mismatch: {list(res.columns)}"
        assert len(res) == 0, f"expected header-only (0 rows), got {len(res)}"
        tr = pd.read_csv(trades_path)
        assert list(tr.columns) == realopt.TRADE_COLS, f"trades header mismatch: {list(tr.columns)}"
        assert len(tr) == 0, f"expected header-only trades (0 rows), got {len(tr)}"
        cal = pd.read_csv(calib_path)
        assert list(cal.columns) == realopt.CALIB_COLS, f"calibration header mismatch: {list(cal.columns)}"
        assert len(cal) == 0, f"expected header-only calibration (0 rows), got {len(cal)}"
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)
    return True


def main():
    checks = [("implied_k arithmetic on the 3-row inline fixture", test_implied_k_arithmetic),
              ("strike selection picks the nearest listed strike", test_strike_selection),
              ("skip path writes header-only outputs (option file missing)", test_skip_path)]
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
