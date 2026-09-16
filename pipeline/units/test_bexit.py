"""Unit test for pipeline.units.bexit (A48 bounded-exit detectability), runnable standalone:

    python -m pipeline.units.test_bexit

No pytest dependency (none is used elsewhere in pipeline/); plain asserts, PASS/FAIL printed per
check, matching pipeline.units.test_power's own style. A48 explicitly REQUIRES two checks -- the
output carries no forbidden column, and the module computes no forbidden statistic -- plus a
synthetic path check, a direction-mirror check and a monotonicity sanity check:
  (a) the emitted column set is EXACTLY `bexit.OUT_COLS` (family, candidate, window, exit_rule, n,
      sd_net_pts_cost1, sd_net_pts_cost2, mde_at_n, mde_at_200, answerable_at_n), and no column
      name matches a forbidden-statistic substring (mean, median, avg, win, sharpe, pnl, p_val,
      ret, profit, total, cum). Checked against a REAL run of `bexit.main` (real extended data),
      not just the constant, so a future change that silently widens the output is caught.
  (b) `pipeline/units/bexit.py`'s own source contains no call to `.mean(`/`.cumsum(`, nor the
      identifiers `win_rate`/`sharpe`/`pnl` -- the exact targeted scan ACCEPTANCE.md amendment A48
      asks for (and `pipeline/run_all.py`'s own verification step runs the identical grep).
  (c) a synthetic path check on `bexit.walk_bounded_exit` directly (a tiny hand-built bar frame,
      not a reimplementation of the walk): a trade whose path touches the target before the stop
      exits at the target; one that touches the stop first exits at the stop; one whose range on a
      SINGLE bar contains BOTH exits at the STOP (the fvg.py tie convention this module reuses);
      one that touches neither exits at the registered exit.
  (d) direction is respected: the SAME price path gives the mirrored net-points result for a put
      versus a call (same magnitude, opposite sign) -- checked on the touches-target-then-mirror
      case from (c).
  (e) monotonicity sanity: on a REAL candidate/window with an available ATR proxy
      (flatten HOLDOUT U1, the same real run (a) already produced), sd is non-increasing as the ATR
      multiple m tightens across {2.0, 1.5, 1.0, 0.5} -- a tighter stop can only truncate the same
      per-trade distribution further, never widen it.

Mutation proof (run by hand, reported alongside this suite's PASS/FAIL output, not committed as
code): (1) swapping the tie precedence in `walk_bounded_exit` (`exit_px = tp_px if stop_hit[pos]
else stop_px`, i.e. target wins a same-bar tie) makes check (c)'s tie case FAIL; reverting makes it
PASS again. (2) breaking the direction mirror (hard-coding `direction=1.0` inside
`walk_bounded_exit` regardless of the caller's own `direction` argument) makes check (d) FAIL;
reverting makes it PASS again. (3) adding a forbidden column (e.g. `mean_net_pts_cost1`) to
`bexit.OUT_COLS` and to the dict `_dispersion_row` returns makes check (a) FAIL on both the exact-
column-set assertion and the forbidden-substring assertion; reverting makes it PASS again.
"""
import os
import re
import sys
import tempfile

import numpy as np
import pandas as pd

from pipeline.units import bexit

FORBIDDEN_COL_PATTERNS = ("mean", "median", "avg", "win", "sharpe", "pnl", "p_val", "ret",
                          "profit", "total", "cum")
# A48's own required OUT_COLS legitimately contains "window", which contains "win" as a plain
# substring but is not a win-rate column -- the one known, deliberate exception to the substring
# scan below (every genuinely forbidden column this suite's mutation proof adds, e.g.
# "mean_net_pts_cost1", is still caught: the exception list names one exact column, not a pattern).
ALLOWED_SUBSTRING_COLLISIONS = {"window"}
# The exact targeted scan A48 asks for (and pipeline/run_all.py's own VERIFY step 7 greps for);
# deliberately narrower than FORBIDDEN_COL_PATTERNS above -- a source-level call/identifier scan,
# not a column-name substring scan (bexit.py's own column names, e.g. "candidate", legitimately
# contain no such substrings, but its PROSE legitimately discusses the very words being banned).
FORBIDDEN_SOURCE_RE = re.compile(r"\.mean\(|\.cumsum\(|win_rate|sharpe|pnl")

_CACHE = {}


def _real_run():
    """`bexit.main` on the real extended frame, cached across checks in this module (a real run
    takes several seconds; every check that needs real data reuses the same one)."""
    if "df" not in _CACHE:
        fd, path = tempfile.mkstemp(suffix=".csv")
        os.close(fd)
        try:
            bexit.main("extended", path)
            _CACHE["df"] = pd.read_csv(path)
        finally:
            os.remove(path)
    return _CACHE["df"]


def test_output_columns_exact_and_no_forbidden_pattern():
    df = _real_run()
    assert list(df.columns) == bexit.OUT_COLS, f"emitted columns {list(df.columns)} != {bexit.OUT_COLS}"
    assert len(df) > 0, "a real run must emit at least one row (nothing to check column shape on otherwise)"
    for c in df.columns:
        if c in ALLOWED_SUBSTRING_COLLISIONS:
            continue
        lc = c.lower()
        hits = [p for p in FORBIDDEN_COL_PATTERNS if p in lc]
        assert not hits, f"column {c!r} matches forbidden pattern(s) {hits}"
    return True


def test_source_has_no_forbidden_calls():
    src_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bexit.py")
    src = open(src_path).read()
    hits = FORBIDDEN_SOURCE_RE.findall(src)
    assert not hits, f"forbidden pattern(s) found in bexit.py source: {hits}"
    return True


def _synthetic_bars(mods, highs, lows):
    return dict(mod=np.asarray(mods), high=np.asarray(highs, dtype=float), low=np.asarray(lows, dtype=float))


def test_target_before_stop_exits_at_target():
    # call, entry 100, dist 5 -> stop 95 / target 105. bar1 stays inside; bar2 touches target only.
    bars = _synthetic_bars([1, 2, 3], [101.0, 108.0, 90.0], [99.0, 102.0, 80.0])
    net = bexit.walk_bounded_exit(bars, 1, 3, 100.0, 1.0, 5.0, registered_exit_px=102.0)
    assert net == 5.0, f"expected +5.0 (target hit at bar2, bar3's later stop-range must never be reached), got {net}"
    return True


def test_stop_before_target_exits_at_stop():
    # call, entry 100, dist 5 -> stop 95 / target 105. bar1 stays inside; bar2 touches stop only.
    bars = _synthetic_bars([1, 2, 3], [101.0, 94.0, 120.0], [99.0, 90.0, 110.0])
    net = bexit.walk_bounded_exit(bars, 1, 3, 100.0, 1.0, 5.0, registered_exit_px=102.0)
    assert net == -5.0, f"expected -5.0 (stop hit at bar2, bar3's later target-range must never be reached), got {net}"
    return True


def test_same_bar_both_touched_stop_wins():
    # call, entry 100, dist 5 -> stop 95 / target 105. bar1's own range [90,110] contains BOTH.
    bars = _synthetic_bars([1], [110.0], [90.0])
    net = bexit.walk_bounded_exit(bars, 1, 1, 100.0, 1.0, 5.0, registered_exit_px=102.0)
    assert net == -5.0, f"a bar touching both stop and target must resolve to the STOP (fvg.py's own tie convention), got {net}"
    return True


def test_neither_touched_exits_at_registered():
    # call, entry 100, dist 5 -> stop 95 / target 105. Every bar stays strictly inside [95,105].
    bars = _synthetic_bars([1, 2, 3], [101.0, 103.0, 100.5], [99.0, 98.0, 99.5])
    net = bexit.walk_bounded_exit(bars, 1, 3, 100.0, 1.0, 5.0, registered_exit_px=102.0)
    assert net == 2.0, f"expected +2.0 (registered exit at 102, never touched), got {net}"
    return True


def test_direction_mirrors_the_same_path():
    # Same monotonically rising path for both: call touches target at bar2 (+5); the mirrored put
    # on the IDENTICAL path touches its stop at bar2 instead (-5) -- same magnitude, opposite sign.
    bars = _synthetic_bars([1, 2], [103.0, 108.0], [99.0, 102.0])
    call_net = bexit.walk_bounded_exit(bars, 1, 2, 100.0, 1.0, 5.0, registered_exit_px=100.0)
    put_net = bexit.walk_bounded_exit(bars, 1, 2, 100.0, -1.0, 5.0, registered_exit_px=100.0)
    assert call_net == 5.0, f"call on the rising path must hit its target (+5.0), got {call_net}"
    assert put_net == -5.0, f"put on the SAME rising path must hit its (mirrored) stop (-5.0), got {put_net}"
    assert call_net == -put_net, f"direction must exactly mirror the outcome on the same path: {call_net} != {-put_net}"
    return True


def test_tighter_atr_stop_never_widens_dispersion_real_candidate():
    df = _real_run()
    sub = df[(df["family"] == "flatten") & (df["candidate"] == "U1") & (df["window"] == "HOLDOUT")]
    sds = {}
    for m in ("2.0", "1.5", "1.0", "0.5"):
        row = sub[sub["exit_rule"] == f"atr{m}x"]
        assert len(row) == 1, f"expected exactly one atr{m}x row for flatten/U1/HOLDOUT, got {len(row)}"
        sds[m] = float(row["sd_net_pts_cost1"].iloc[0])
    ordered = [sds["2.0"], sds["1.5"], sds["1.0"], sds["0.5"]]
    assert all(ordered[i] >= ordered[i + 1] for i in range(len(ordered) - 1)), \
        f"sd must be non-increasing as the ATR multiple tightens (2.0->0.5), got {ordered}"
    assert ordered[0] > ordered[-1], "test candidate must show a genuinely non-flat monotonic range, not a tie throughout"
    return True


def main():
    checks = [("(a) output columns are exactly OUT_COLS, no forbidden pattern", test_output_columns_exact_and_no_forbidden_pattern),
              ("(b) source has no .mean(/.cumsum(/win_rate/sharpe/pnl", test_source_has_no_forbidden_calls),
              ("(c1) target touched before stop exits at target", test_target_before_stop_exits_at_target),
              ("(c2) stop touched before target exits at stop", test_stop_before_target_exits_at_stop),
              ("(c3) a bar touching both resolves to the stop (fvg.py tie convention)", test_same_bar_both_touched_stop_wins),
              ("(c4) neither touched exits at the registered exit", test_neither_touched_exits_at_registered),
              ("(d) direction mirrors the same price path", test_direction_mirrors_the_same_path),
              ("(e) tighter ATR stop never widens sd (flatten HOLDOUT U1, real data)", test_tighter_atr_stop_never_widens_dispersion_real_candidate)]
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
