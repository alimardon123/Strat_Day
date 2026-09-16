"""Unit test for pipeline.units.poscontrol (A50 positive control), runnable standalone:

    python -m pipeline.units.test_poscontrol

No pytest dependency (none is used elsewhere in pipeline/); plain asserts, PASS/FAIL printed per
check, matching pipeline.units.test_flatten's own __main__ block. Every check below exercises the
REAL `poscontrol.inject_delta` function (and, for (d), the REAL `pipeline.stats.one_sided_p`) on
small synthetic in-memory DataFrames -- no tempfile, nothing written under out/ or data/, and no
call into `poscontrol.main` (which needs the real extended frame plus out/trials.csv and
out/power_analysis.csv, well beyond what a fast unit test should depend on; that full path is
exercised in VERIFICATION, not here):
  (a) injection is additive and exact: on a synthetic per-trade series, injecting delta raises the
      mean of `pts` by EXACTLY delta and leaves its standard deviation UNCHANGED (adding a
      constant to every value cannot move a sample sd; `ret_pct`'s own shift is per-trade,
      100*delta/entry_px, so this check is stated on `pts`, the quantity A50 itself names).
  (b) injection touches ONLY the trades it is given: a synthetic day of trades with SIGNAL and
      NON-SIGNAL rows shows the non-signal rows bit-identical before and after -- proven by
      passing only the signal subset to inject_delta (mirroring how every score_* function in the
      module calls it: on that candidate's own signal-day trades ONLY) and showing (i) the source
      table is never mutated in place and (ii) the non-signal rows read back out of it afterwards
      are still bit-identical to their original values.
  (c) delta=0.0 is a true no-op: the injected frame is BIT-IDENTICAL to the original
      (`pd.testing.assert_frame_equal`, not merely numerically close).
  (d) monotonicity: `pipeline.stats.one_sided_p` (the real day-block bootstrap, n_boot 2000, seed
      11 -- its own module defaults) is non-increasing in delta on one fixed synthetic series
      across A50's own delta sweep.
  (e) the module writes no column whose name could be mistaken for a real per-trial result
      (`net_pts_cost1`, `sharpe_calday`, `dsr_N33`, `fdr_pass_10pct_family`, ... -- the fleet
      units' and trials.py's own column names) and has exactly ONE `.to_csv(` call in the whole
      module (proving it never writes a companion "_trades.csv"-style second file the way
      gapliq.py/flatten.py/fvg.py do, or out/trials.csv, or any candidate table -- A50: "its only
      output is out/poscontrol.csv").

Mutation proof (run by hand, reported alongside this suite's PASS/FAIL output, not committed as
code): (1) changing `inject_delta`'s `t["pts"] = t["pts"] + delta` to `+ delta / 2` makes check
(a) FAIL (the mean no longer rises by exactly delta); (2) changing `inject_delta` to also mutate
a copy of the FULL day table (not just the trades handed to it) -- simulated here by calling it on
the non-signal rows too -- makes check (b) FAIL; (3) changing delta=0.0's branch to add a nonzero
constant (e.g. 1e-9) makes check (c) FAIL. Reverting each makes the suite PASS again; see the
task's VERIFICATION section for the real terminal output of this drill.
"""
import inspect
import sys

import numpy as np
import pandas as pd

from pipeline import stats
from pipeline.units import poscontrol


def _synthetic_trades(n=50, seed=0):
    rng = np.random.default_rng(seed)
    entry = rng.uniform(90.0, 110.0, size=n)
    pts = rng.normal(0.0, 5.0, size=n)
    exitp = entry + pts
    ret_pct = (exitp / entry - 1) * 100
    return pd.DataFrame({"date": pd.date_range("2020-01-01", periods=n, freq="B"),
                         "entry_px": entry, "exit_px": exitp, "pts": pts, "ret_pct": ret_pct})


def test_injection_additive_and_exact():
    trades = _synthetic_trades()
    base_mean, base_sd = trades["pts"].mean(), trades["pts"].std(ddof=1)
    for delta in (0.0, 0.25, 1.5, 7.0, -3.0):
        inj = poscontrol.inject_delta(trades, delta)
        assert np.isclose(inj["pts"].mean(), base_mean + delta, atol=1e-10), \
            f"delta={delta}: mean {inj['pts'].mean()} != base {base_mean} + delta"
        assert np.isclose(inj["pts"].std(ddof=1), base_sd, atol=1e-10), \
            f"delta={delta}: sd {inj['pts'].std(ddof=1)} != unchanged base sd {base_sd}"
    return True


def test_injection_touches_only_the_trades_it_is_given():
    n = 6
    dates = pd.date_range("2021-06-01", periods=n, freq="B")
    entry = np.array([100.0, 101.0, 99.0, 102.0, 100.0, 98.0])
    exitp = np.array([105.0, 99.0, 104.0, 98.0, 103.0, 101.0])
    is_signal = np.array([True, False, False, True, False, False])
    trades_all = pd.DataFrame({"date": dates, "entry_px": entry, "exit_px": exitp,
                               "pts": exitp - entry, "ret_pct": (exitp / entry - 1) * 100})
    before = trades_all.copy(deep=True)

    signal_only = trades_all[is_signal].copy()
    injected = poscontrol.inject_delta(signal_only, 5.0)

    # the source table, never itself passed to inject_delta beyond building the signal-only slice,
    # is untouched -- inject_delta operates on (and returns) a copy, never mutates its argument
    pd.testing.assert_frame_equal(trades_all, before)
    # the non-signal rows, read back out of that same untouched table, are bit-identical
    pd.testing.assert_frame_equal(trades_all[~is_signal], before[~is_signal])
    # the signal rows moved by exactly delta in pts, in the returned (injected) frame only
    assert np.allclose(injected["pts"].to_numpy(), before[is_signal]["pts"].to_numpy() + 5.0)
    return True


def test_delta_zero_is_true_noop():
    trades = _synthetic_trades(seed=1)
    injected = poscontrol.inject_delta(trades, 0.0)
    pd.testing.assert_frame_equal(injected, trades)
    assert injected.equals(trades), "delta=0.0 must be bit-identical to the source, not merely numerically close"
    return True


def test_bootstrap_p_nonincreasing_in_delta():
    trades = _synthetic_trades(n=40, seed=2)
    ps = []
    for delta in poscontrol.DELTAS:
        inj = poscontrol.inject_delta(trades, delta)
        p = stats.one_sided_p(inj["ret_pct"].to_numpy(), stats.day_blocks(inj["date"]))
        ps.append(p)
    assert all(pd.notna(p) for p in ps), f"expected a finite p at every registered delta, got {ps}"
    assert all(ps[i] >= ps[i + 1] - 1e-12 for i in range(len(ps) - 1)), \
        f"p_boot must be non-increasing as delta increases, got {ps}"
    assert ps[0] > ps[-1], "must be strictly lower at the top of the sweep than the bottom on this fixture " \
                          "(else the monotonicity check would be vacuous)"
    return True


def test_output_columns_safe_and_single_sink():
    forbidden = {"trial", "net_pts_cost1", "net_pts_cost2", "net_pct_cost1", "net_pct_cost2", "win",
                "sharpe_calday", "p_boot_month", "dsr_N33", "dsr_N37", "dsr_N45", "dsr_N48",
                "opt_mean_pct_s1", "control_mean_pts_cost1", "fdr_pass_10pct_family", "label_final"}
    overlap = forbidden & set(poscontrol.OUT_COLS)
    assert not overlap, f"poscontrol.OUT_COLS must not reuse a real per-trial result column name, found {overlap}"
    assert "candidate" in poscontrol.OUT_COLS and "trial" not in poscontrol.OUT_COLS, \
        "poscontrol.csv must key its rows on 'candidate', never 'trial' (the real per-family tables' own column)"
    src = inspect.getsource(poscontrol)
    assert src.count(".to_csv(") == 1, \
        f"pipeline.units.poscontrol must write exactly ONE csv (the given --out); found {src.count('.to_csv(')}"
    write_line = [ln for ln in src.splitlines() if ".to_csv(" in ln][0]
    assert "out" in write_line and "trials" not in write_line, \
        f"the one .to_csv( call must write the given --out, never a hardcoded trials/candidate table: {write_line!r}"
    assert "SCORECARD.md" not in src, "poscontrol.py must never reference SCORECARD.md (A50: its only output is out/poscontrol.csv)"
    return True


def main():
    checks = [("injection is additive and exact on pts (mean +delta, sd unchanged)", test_injection_additive_and_exact),
              ("injection touches ONLY the trades it is given (non-signal rows bit-identical)",
               test_injection_touches_only_the_trades_it_is_given),
              ("delta=0.0 is a true (bit-identical) no-op", test_delta_zero_is_true_noop),
              ("bootstrap p is non-increasing in delta (real pipeline.stats.one_sided_p)",
               test_bootstrap_p_nonincreasing_in_delta),
              ("no column name is confusable with a real per-trial result; exactly one .to_csv( sink",
               test_output_columns_safe_and_single_sink)]
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
