"""Unit test for pipeline.units.flatten (A46/A46a), runnable standalone:

    python -m pipeline.units.test_flatten

No pytest dependency (none is used elsewhere in pipeline/); plain asserts, PASS/FAIL printed per
check, matching pipeline.units.test_letf's own `__main__` block and tempfile usage. Two checks,
per the task, both exercised through the REAL functions in flatten.py (compute_thresholds,
compute_bands, build_trades, summarize), never a reimplementation of their logic:
  (a) the band logic (flatten.compute_thresholds / flatten.compute_bands) is disjoint and causal
      on a synthetic 300-session fixture where the expanding 10th/30th/90th percentiles at one
      chosen row are known independently (np.quantile on that row's own strictly-prior window):
      (i) no session is flagged by more than one of U1/U2/U3 (checked over the whole fixture, and
      by construction at the chosen row using values placed exactly relative to the known
      thresholds); (ii) perturbing a session's OWN value never changes its OWN threshold (only
      later thresholds move -- checked both ways, so the test cannot pass on a no-op
      perturbation); (iii) the first MIN_PRIOR_SESSIONS-1 sessions carry no signal at all.
  (b) a trade table built by flatten.summarize's real path (build_trades -> the net-of-cost
      columns) has every entry bar (11:00, mod 660) strictly before its exit bar (the session's
      last bar) and its net_pts_cost1/net_pts_cost2/net_pct_cost1/net_pct_cost2 columns equal the
      gross pts/ret_pct columns minus the registered COST1/COST2.
Neither check writes anything under out/ or data/ (no tempfile is even needed: both fixtures are
plain in-memory DataFrames).
"""
import sys

import numpy as np
import pandas as pd

from pipeline.units import flatten


def test_bands_disjoint_and_causal():
    """300 sessions of small synthetic noise (seed 42); K=260 is the first row comfortably past
    the MIN_PRIOR_SESSIONS=250 warm-up (thr at row K depends only on rows 0..K-1, 260 values)."""
    n = 300
    dates = pd.date_range("2000-01-03", periods=n, freq="B")
    rng = np.random.default_rng(42)
    base = pd.Series(rng.normal(loc=0.0, scale=0.01, size=n), index=dates)
    k = 260

    # --- known thresholds at row k, computed independently of flatten's own quantile call ---
    prior_window = base.iloc[:k].to_numpy()                     # rows 0..k-1, exactly what
                                                                  # signals.expanding_threshold's
                                                                  # shift(1) exposes at row k
    expected_lo = np.quantile(prior_window, flatten.Q_LO)
    expected_mild = np.quantile(prior_window, flatten.Q_MILD)
    expected_hi = np.quantile(prior_window, flatten.Q_HI)
    thr_lo, thr_mild, thr_hi = flatten.compute_thresholds(base)
    assert np.isclose(thr_lo.iloc[k], expected_lo), f"thr_lo[{k}] {thr_lo.iloc[k]} != known {expected_lo}"
    assert np.isclose(thr_mild.iloc[k], expected_mild), f"thr_mild[{k}] {thr_mild.iloc[k]} != known {expected_mild}"
    assert np.isclose(thr_hi.iloc[k], expected_hi), f"thr_hi[{k}] {thr_hi.iloc[k]} != known {expected_hi}"
    assert expected_lo < expected_mild < expected_hi, "fixture degenerate: thresholds not ordered"

    # --- (i) disjointness, both generically (whole fixture) and by known construction at k ---
    sig_u1, sig_u2, sig_u3 = flatten.compute_bands(base)
    assert not (sig_u1 & sig_u2).any(), "U1/U2 overlap somewhere in the fixture"
    assert not (sig_u1 & sig_u3).any(), "U1/U3 overlap somewhere in the fixture"
    assert not (sig_u2 & sig_u3).any(), "U2/U3 overlap somewhere in the fixture"

    ret_u1 = base.copy(); ret_u1.iloc[k] = expected_lo - 0.001          # strictly below 10th pct
    ret_u2 = base.copy(); ret_u2.iloc[k] = (expected_lo + expected_mild) / 2  # strictly inside (10th,30th]
    ret_u3 = base.copy(); ret_u3.iloc[k] = expected_hi + 0.001          # at/above 90th pct
    s1u1, s1u2, s1u3 = flatten.compute_bands(ret_u1)
    s2u1, s2u2, s2u3 = flatten.compute_bands(ret_u2)
    s3u1, s3u2, s3u3 = flatten.compute_bands(ret_u3)
    assert bool(s1u1.iloc[k]) and not s1u2.iloc[k] and not s1u3.iloc[k], "known below-10th-pct value did not land in U1 alone"
    assert bool(s2u2.iloc[k]) and not s2u1.iloc[k] and not s2u3.iloc[k], "known mild-decline value did not land in U2 alone"
    assert bool(s3u3.iloc[k]) and not s3u1.iloc[k] and not s3u2.iloc[k], "known at/above-90th-pct value did not land in U3 alone"

    # --- (ii) causal: a session's OWN value never moves its OWN threshold ---
    for perturbed in (ret_u1, ret_u2, ret_u3):
        p_lo, p_mild, p_hi = flatten.compute_thresholds(perturbed)
        assert np.isclose(p_lo.iloc[k], thr_lo.iloc[k]), "perturbing row k's own value moved thr_lo at row k"
        assert np.isclose(p_mild.iloc[k], thr_mild.iloc[k]), "perturbing row k's own value moved thr_mild at row k"
        assert np.isclose(p_hi.iloc[k], thr_hi.iloc[k]), "perturbing row k's own value moved thr_hi at row k"
    # the perturbation is not a no-op: it DOES move thresholds at LATER rows (proves the test is live)
    later_lo, _, _ = flatten.compute_thresholds(ret_u1)
    assert not np.isclose(later_lo.iloc[k + 5], thr_lo.iloc[k + 5]), \
        "perturbation had no effect anywhere -- the causal check above would be vacuous"

    # --- (iii) the warm-up: no signal in the first MIN_PRIOR_SESSIONS-1 sessions ---
    warm = flatten.MIN_PRIOR_SESSIONS - 1
    assert not sig_u1.iloc[:warm].any(), "U1 fired inside the warm-up window"
    assert not sig_u2.iloc[:warm].any(), "U2 fired inside the warm-up window"
    assert not sig_u3.iloc[:warm].any(), "U3 fired inside the warm-up window"
    return True


def test_trade_entry_before_exit_and_net_of_cost():
    """A tiny 5-session inline 'day' table (bypassing build_day_table -- no frame/vix needed),
    with U1 signalled on two of the five sessions. summarize() is called exactly as main() calls
    it, and the returned trades frame (built by the real build_trades -> net-of-cost path) is
    checked for bar ordering and the net-of-cost arithmetic."""
    dates = pd.date_range("2021-03-01", periods=5, freq="B")
    day = pd.DataFrame({
        "px_1100": [100.0, 101.0, 99.0, 102.0, 100.0],
        "close": [105.0, 99.0, 104.0, 98.0, 103.0],
        "last_mod": [960, 960, 960, 960, 960],          # 16:00 close bar, strictly after 11:00 (660)
        "vix_prev": [15.0, 16.0, 14.0, 18.0, 15.5],
        "elig": [True, True, True, True, True],
        "sig_u1": [False, True, False, True, False],
        "sig_u2": [False, False, False, False, False],
        "sig_u3": [False, False, False, False, False],
    }, index=dates)
    # a couple of minute bars so the timing control has something to draw from (not asserted on)
    frame = pd.DataFrame({
        "date": [dates[1], dates[3]],
        "mod": [700, 700],
        "close": [100.5, 101.8],
    })
    start_ts, end_ts = dates[0], dates[-1]
    row, trades, _net_pct1 = flatten.summarize("TEST", "U1", "call", "11:00", day, start_ts, end_ts,
                                               "sig_u1", 1.0, "c", frame, list(dates))

    assert row["n"] == 2, f"expected 2 matched trades (sig_u1 on 2 of 5 sessions), got {row['n']}"
    assert len(trades) == 2
    assert (trades["entry_mod"] < trades["exit_mod"]).all(), "entry bar (11:00) is not strictly before the exit bar"
    assert (trades["entry_mod"] == flatten.MOD_1100).all()
    assert (trades["exit_mod"] == 960).all()

    expected_pts = trades["exit_px"] - trades["entry_px"]           # direction=+1 (call)
    expected_ret_pct = (trades["exit_px"] / trades["entry_px"] - 1) * 100
    assert np.allclose(trades["pts"], expected_pts)
    assert np.allclose(trades["ret_pct"], expected_ret_pct)
    assert np.allclose(trades["net_pts_cost1"], trades["pts"] - flatten.COST1), \
        "net_pts_cost1 != gross pts - COST1"
    assert np.allclose(trades["net_pts_cost2"], trades["pts"] - flatten.COST2), \
        "net_pts_cost2 != gross pts - COST2"
    assert np.allclose(trades["net_pct_cost1"], trades["ret_pct"] - 100 * flatten.COST1 / trades["entry_px"]), \
        "net_pct_cost1 != gross ret_pct - 100*COST1/entry_px"
    assert np.allclose(trades["net_pct_cost2"], trades["ret_pct"] - 100 * flatten.COST2 / trades["entry_px"]), \
        "net_pct_cost2 != gross ret_pct - 100*COST2/entry_px"
    return True


def main():
    checks = [("band logic disjoint and causal on the 300-session fixture", test_bands_disjoint_and_causal),
              ("trade entry strictly before exit; net columns = gross - registered cost", test_trade_entry_before_exit_and_net_of_cost)]
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
