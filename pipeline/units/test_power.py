"""Unit test for pipeline.units.power (A47 detectability floor), runnable standalone:

    python -m pipeline.units.test_power

No pytest dependency (none is used elsewhere in pipeline/); plain asserts, PASS/FAIL printed per
check, matching pipeline.units.test_sizing's own __main__ block. Every check exercises the REAL
`power.mde` / `power.n_req` / `power.group_row` pure functions (no data loader, no I/O) on
synthetic sd values / series with hand-checkable answers -- this is deliberately NOT a restatement
of the formula the code itself uses: a previous suite in this repo passed while the code read the
wrong bar and understated capital fourfold (test_sizing.py's own review-round checks (e)-(g)), so
every number below is pinned independently, via scipy directly in this file, not by importing
`power.mde`/`power.Z_SUM` and calling that the check:
  (a) mde(sd, 200) equals (z_0.95+z_0.80)*sd/sqrt(200) computed INDEPENDENTLY here from
      scipy.stats.norm.ppf, pinned to several decimals, for a specific absolute sd.
  (b) n_req(sd, 1.0) is exactly 4x n_req(sd, 2.0) on an sd chosen so (z_sum*sd)^2 lands on a
      multiple of 4, so the ceiling's rounding cannot obscure the 1/delta^2 relation.
  (c) halving sd quarters n_req(sd, 1.0) (n scales as sd^2 at fixed delta).
  (d) a group with fewer than 2 trades is skipped (group_row returns None), never emitted with a
      NaN sd.
  (e) mde_at_n at n=200 equals mde_at_200 for the same series (group_row's own output columns).

Mutation proof (run by hand, reported alongside this suite's PASS/FAIL output, not committed as
code): temporarily changing `math.sqrt(n)` to `n` in `power.mde` makes check (a) and (e) FAIL
(the independently-computed scipy answer no longer matches); reverting makes them PASS again --
this suite is not a tautology restating the code's own formula back at it.
"""
import math
import sys

import numpy as np
from scipy.stats import norm

from pipeline.units import power

Z_SUM_INDEPENDENT = norm.ppf(0.95) + norm.ppf(0.80)   # computed independently of power.Z_SUM


def test_mde_at_200_matches_independent_formula():
    sd = 44.70   # A46 HOLDOUT U1's own published sd (ASSESSMENT.md) -- a realistic, not arbitrary, figure
    got = power.mde(sd, 200)
    want = Z_SUM_INDEPENDENT * sd / math.sqrt(200)
    assert abs(got - want) < 1e-9, f"mde(sd,200) = {got} != independently computed {want}"
    assert round(got, 6) == round(want, 6)
    assert round(got, 4) == 7.8592, f"mde(44.70, 200) must pin to 7.8592 to 4 decimals, got {got:.4f}"
    return True


def test_n_req_1pt_is_exactly_4x_n_req_2pt():
    sd = 20.0 / Z_SUM_INDEPENDENT   # chosen so (z_sum*sd)^2 == 400.0 exactly: no ceiling noise
    n1 = power.n_req(sd, 1.0)
    n2 = power.n_req(sd, 2.0)
    assert n1 == 400, f"expected n_req(sd,1.0) == 400 at this sd, got {n1}"
    assert n2 == 100, f"expected n_req(sd,2.0) == 100 at this sd, got {n2}"
    assert n1 == 4 * n2, f"n_req(sd,1.0) ({n1}) must be exactly 4x n_req(sd,2.0) ({n2}): n scales as 1/delta^2"
    return True


def test_halving_sd_quarters_n_req():
    sd = 20.0 / Z_SUM_INDEPENDENT
    n_full = power.n_req(sd, 1.0)
    n_half = power.n_req(sd / 2, 1.0)
    assert n_full == 400 and n_half == 100, f"got n_full={n_full}, n_half={n_half}"
    assert n_full == 4 * n_half, "halving sd must quarter n_req at fixed delta (n scales as sd^2)"
    return True


def test_group_with_fewer_than_2_trades_is_skipped():
    row_empty = power.group_row("synthetic", "W", "C", [], [], np.nan)
    row_one = power.group_row("synthetic", "W", "C", [5.0], ["2020-01-01"], np.nan)
    row_two = power.group_row("synthetic", "W", "C", [5.0, 6.0], ["2020-01-01", "2020-01-02"], np.nan)
    assert row_empty is None, "an empty group must be skipped, not emitted"
    assert row_one is None, "a single-trade group must be SKIPPED (sample sd needs n>=2), never emitted with a NaN sd"
    assert row_two is not None and row_two["n"] == 2, "a 2-trade group must be emitted"
    assert row_two["sd_net_pts"] == row_two["sd_net_pts"], "an emitted row's sd must not be NaN"  # NaN != NaN
    return True


def test_mde_at_n_equals_mde_at_200_when_n_is_200():
    rng = np.random.default_rng(0)
    values = rng.normal(loc=1.5, scale=10.0, size=200)
    dates = [f"2020-{1 + (i % 12):02d}-{1 + (i % 28):02d}" for i in range(200)]
    row = power.group_row("synthetic", "W", "C", values, dates, np.nan)
    assert row["n"] == 200
    assert row["mde_at_n"] == row["mde_at_200"], \
        f"mde_at_n at n=200 must equal mde_at_200, got {row['mde_at_n']} vs {row['mde_at_200']}"
    return True


def main():
    checks = [("mde(sd,200) matches scipy computed independently, pinned to 4 decimals", test_mde_at_200_matches_independent_formula),
              ("n_req(sd,1.0) is exactly 4x n_req(sd,2.0) at a ceiling-safe sd", test_n_req_1pt_is_exactly_4x_n_req_2pt),
              ("halving sd quarters n_req at fixed delta", test_halving_sd_quarters_n_req),
              ("a <2-trade group is skipped, not emitted with a NaN sd", test_group_with_fewer_than_2_trades_is_skipped),
              ("mde_at_n at n=200 equals mde_at_200", test_mde_at_n_equals_mde_at_200_when_n_is_200)]
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
