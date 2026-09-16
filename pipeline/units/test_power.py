"""Unit test for pipeline.units.power (A47 detectability floor), runnable standalone:

    python -m pipeline.units.test_power

No pytest dependency (none is used elsewhere in pipeline/); plain asserts, PASS/FAIL printed per
check, matching pipeline.units.test_sizing's own __main__ block. Checks (a)-(e) exercise the REAL
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

Mutation proof for (a)-(e) (run by hand, reported alongside this suite's PASS/FAIL output, not
committed as code): temporarily changing `math.sqrt(n)` to `n` in `power.mde` makes check (a) and
(e) FAIL (the independently-computed scipy answer no longer matches); reverting makes them PASS
again -- this suite is not a tautology restating the code's own formula back at it.

Review-round checks (f)-(k), added after a mutation-testing pass found (a)-(e) above pin the core
MDE formula but let six other mutants survive, each silently changing a PUBLISHED number:
  (f) `std(ddof=1)` -> `ddof=0`: sd pinned against an independent `np.std(..., ddof=1)` call on a
      series chosen so ddof=0 and ddof=1 give visibly different answers.
  (g) `ceil` -> `int`: (b) above deliberately lands on an exact square and so can never see a
      broken ceiling; this adds an sd where `(z_sum*sd/delta)^2` is genuinely fractional, so
      truncating instead of rounding up changes the answer.
  (h) `se = sd/sqrt(n)` -> `sd/n`, and `t = mean/se` -> `mean/sd`: both pinned independently on a
      4-trade series (n != 1, so sqrt(n) and n actually differ).
  (i) `/365.25` -> `/365.0`, and `signals_per_year = n/span` -> `2*n/span`: pinned independently
      on a decade-long synthetic span, long enough that 365.0 vs 365.25 is detectable.
  (j) `ITM_PCT 0.02` -> `0.05`: `_read_premium_pts()` pinned against `out/sizing_forward.csv`'s own
      `level_spx_pts` times a HARD-CODED 2% (never `power.ITM_PCT`, or the mutation would move both
      sides of the comparison together and never be caught). SKIPS if the file is absent.
  (k) the cost convention -- `net_pts = pts - COST1` -> gross `pts` or double-costed
      `pts - 2*COST1` -- the most important survivor, and exactly the failure class this suite
      exists to prevent. The strongest guard is a real regression against numbers this programme
      has already published OUTSIDE this module: `out/fvg_candidates.csv`'s `net_pts_cost1` (A36,
      all 24 window/trial groups) and `out/holdout_pooled.csv`'s `net_pts` for the two
      pre-registered signals (-0.143431 at n=274, -1.903650 at n=452, pinned literally per A47a).
      SKIPS with a clear message, rather than failing, when the underlying `out/` files are absent
      (a no-run checkout).
"""
import math
import os
import sys

import numpy as np
import pandas as pd
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
    row_empty = power.group_row("fam", "synthetic", "W", "C", [], [], np.nan)
    row_one = power.group_row("fam", "synthetic", "W", "C", [5.0], ["2020-01-01"], np.nan)
    row_two = power.group_row("fam", "synthetic", "W", "C", [5.0, 6.0], ["2020-01-01", "2020-01-02"], np.nan)
    assert row_empty is None, "an empty group must be skipped, not emitted"
    assert row_one is None, "a single-trade group must be SKIPPED (sample sd needs n>=2), never emitted with a NaN sd"
    assert row_two is not None and row_two["n"] == 2, "a 2-trade group must be emitted"
    assert row_two["sd_net_pts"] == row_two["sd_net_pts"], "an emitted row's sd must not be NaN"  # NaN != NaN
    return True


def test_mde_at_n_equals_mde_at_200_when_n_is_200():
    rng = np.random.default_rng(0)
    values = rng.normal(loc=1.5, scale=10.0, size=200)
    dates = [f"2020-{1 + (i % 12):02d}-{1 + (i % 28):02d}" for i in range(200)]
    row = power.group_row("fam", "synthetic", "W", "C", values, dates, np.nan)
    assert row["n"] == 200
    assert row["mde_at_n"] == row["mde_at_200"], \
        f"mde_at_n at n=200 must equal mde_at_200, got {row['mde_at_n']} vs {row['mde_at_200']}"
    return True


def test_sd_uses_sample_ddof1_not_population_ddof0():
    values = [10.0, 12.0, 9.0, 15.0, 11.0, 8.0]
    dates = [f"2020-01-{i + 1:02d}" for i in range(6)]
    row = power.group_row("fam", "synthetic", "W", "C", values, dates, np.nan)
    want = float(np.std(values, ddof=1))          # independent of power.group_row's own call
    wrong = float(np.std(values, ddof=0))
    assert abs(row["sd_net_pts"] - want) < 1e-9, f"sd_net_pts must be ddof=1, got {row['sd_net_pts']} != {want}"
    assert abs(row["sd_net_pts"] - wrong) > 1e-3, "test series must make ddof=1 and ddof=0 visibly differ"
    return True


def test_n_req_rounds_up_a_genuinely_fractional_square():
    sd = 5.3   # chosen so (z_sum*sd/1.0)^2 is NOT an integer: the ceiling actually has work to do
    raw = (Z_SUM_INDEPENDENT * sd / 1.0) ** 2
    assert raw != int(raw), "test sd must land on a fractional square, not an exact one"
    want = math.ceil(raw)
    got = power.n_req(sd, 1.0)
    assert got == want, f"n_req must ceil, got {got} != ceil({raw}) = {want}"
    assert got == int(raw) + 1, f"n_req must round UP {raw} to {int(raw) + 1}, got {got}"
    return True


def test_se_and_t_use_sqrt_n_not_n():
    values = [10.0, -6.0, 14.0, -2.0]   # n=4 (n != 1, so sqrt(n) and n actually differ), mean=4.0
    dates = [f"2020-02-{i + 1:02d}" for i in range(4)]
    row = power.group_row("fam", "synthetic", "W", "C", values, dates, np.nan)
    sd = float(np.std(values, ddof=1))
    se_want = sd / math.sqrt(4)
    t_want = (sum(values) / 4) / se_want
    assert abs(row["se_net_pts"] - se_want) < 1e-9, f"se_net_pts must be sd/sqrt(n), got {row['se_net_pts']} != {se_want}"
    assert abs(row["t"] - t_want) < 1e-9, f"t must be mean/se, got {row['t']} != {t_want}"
    assert abs(row["se_net_pts"] - sd / 4) > 1e-3, "test series must make sd/sqrt(n) and sd/n visibly differ"
    assert abs(row["t"] - (sum(values) / 4) / sd) > 1e-3, "test series must make mean/se and mean/sd visibly differ"
    return True


def test_span_years_uses_365_25_and_rate_is_n_over_span_not_2n():
    import datetime
    start, end = datetime.date(2010, 1, 1), datetime.date(2020, 1, 1)   # a decade: 365.0 vs 365.25 is detectable
    days = (end - start).days
    dates = [start.isoformat(), end.isoformat()] + [start.isoformat()] * 8   # n=10; only min/max matter for span
    values = [float(i) for i in range(10)]
    row = power.group_row("fam", "synthetic", "W", "C", values, dates, np.nan)
    span_want = days / 365.25       # independent of power.group_row's own literal
    span_wrong = days / 365.0
    assert abs(row["span_years"] - span_want) < 1e-9, f"span_years must use /365.25, got {row['span_years']} != {span_want}"
    assert abs(row["span_years"] - span_wrong) > 1e-4, "test span must be long enough that 365.0 vs 365.25 is detectable"
    rate_want = 10 / span_want
    assert abs(row["signals_per_year"] - rate_want) < 1e-6, \
        f"signals_per_year must be n/span_years, got {row['signals_per_year']} != {rate_want}"
    assert abs(row["signals_per_year"] - 2 * rate_want) > 1e-3, "n/span_years and 2*n/span_years must be visibly different here"
    return True


def test_premium_uses_2pct_itm_not_another_pct():
    if not os.path.exists("out/sizing_forward.csv"):
        print("[SKIP] test_premium_uses_2pct_itm_not_another_pct: out/sizing_forward.csv absent")
        return True
    sf = pd.read_csv("out/sizing_forward.csv")
    level = float(sf["level_spx_pts"].iloc[0])
    want = 0.02 * level   # hard-coded 2%, deliberately NOT power.ITM_PCT (a mutated constant would move both sides)
    got = power._read_premium_pts()
    assert abs(got - want) < 1e-6, f"_read_premium_pts() must be 2% of level_spx_pts, got {got} != {want}"
    return True


def test_cost_convention_matches_published_fvg_and_preregistered():
    required = ["out/fvg_candidates.csv", "out/fvg_candidates_trades.csv", "out/holdout_pooled.csv",
                "out/holdout_d4_1300_call_gapgt0.3pct_s1_cash_k1.0.csv",
                "out/holdout_d4_1500_both_vixmove_exp_s1_cash_k1.0.csv"]
    missing = [p for p in required if not os.path.exists(p)]
    if missing:
        print(f"[SKIP] test_cost_convention_matches_published_fvg_and_preregistered: missing {missing}")
        return True
    long = power._long_rows()

    # FVG: every one of the 24 published (window, trial) groups, dynamically, from out/fvg_candidates.csv.
    fvg_pub = pd.read_csv("out/fvg_candidates.csv").set_index(["window", "trial"])
    fvg_got = long[long["family"] == "fvg"].groupby(["window", "candidate"])["net_pts"].agg(["count", "mean"])
    assert len(fvg_got) == 24, f"expected 24 FVG (window, trial) groups, got {len(fvg_got)}"
    for (window, trial), r in fvg_got.iterrows():
        want_n = int(fvg_pub.loc[(window, trial), "n"])
        want_mean = float(fvg_pub.loc[(window, trial), "net_pts_cost1"])
        assert int(r["count"]) == want_n, f"{window}/{trial}: n {int(r['count'])} != published {want_n}"
        assert round(float(r["mean"]), 6) == round(want_mean, 6), \
            f"{window}/{trial}: mean {r['mean']} != published net_pts_cost1 {want_mean} (net_pts = pts - COST1 broken?)"

    # The two pre-registered signals, pinned literally per A47a (belt-and-suspenders on top of the file read).
    pre_got = long[long["family"] == "pre_registered"].groupby("candidate")["net_pts"].agg(["count", "mean"])
    literal = {"13:00|call|gap>0.3%": (452, -1.903650), "15:00|both|vixmove_exp": (274, -0.143431)}
    for candidate, (want_n, want_mean) in literal.items():
        r = pre_got.loc[candidate]
        assert int(r["count"]) == want_n, f"{candidate}: n {int(r['count'])} != {want_n}"
        assert round(float(r["mean"]), 6) == round(want_mean, 6), \
            f"{candidate}: mean {r['mean']} != {want_mean} (net_pts = pts - COST1 broken?)"
    pooled = pd.read_csv("out/holdout_pooled.csv").set_index("signal")
    for candidate, (want_n, want_mean) in literal.items():
        assert int(pooled.loc[candidate, "n"]) == want_n
        assert round(float(pooled.loc[candidate, "net_pts"]), 6) == round(want_mean, 6)
    return True


def main():
    checks = [("mde(sd,200) matches scipy computed independently, pinned to 4 decimals", test_mde_at_200_matches_independent_formula),
              ("n_req(sd,1.0) is exactly 4x n_req(sd,2.0) at a ceiling-safe sd", test_n_req_1pt_is_exactly_4x_n_req_2pt),
              ("halving sd quarters n_req at fixed delta", test_halving_sd_quarters_n_req),
              ("a <2-trade group is skipped, not emitted with a NaN sd", test_group_with_fewer_than_2_trades_is_skipped),
              ("mde_at_n at n=200 equals mde_at_200", test_mde_at_n_equals_mde_at_200_when_n_is_200),
              ("(f) sd uses ddof=1, not ddof=0", test_sd_uses_sample_ddof1_not_population_ddof0),
              ("(g) n_req ceils a genuinely fractional square", test_n_req_rounds_up_a_genuinely_fractional_square),
              ("(h) se uses sqrt(n) and t uses se, not n / sd", test_se_and_t_use_sqrt_n_not_n),
              ("(i) span_years uses /365.25 and rate is n/span, not 2n/span", test_span_years_uses_365_25_and_rate_is_n_over_span_not_2n),
              ("(j) premium uses 2% ITM, pinned against sizing_forward.csv directly", test_premium_uses_2pct_itm_not_another_pct),
              ("(k) cost convention reproduces published FVG and pre-registered net_pts", test_cost_convention_matches_published_fvg_and_preregistered)]
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
