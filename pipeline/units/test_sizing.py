"""Unit test for pipeline.units.sizing (A45 forward-sizing table), runnable standalone:

    python -m pipeline.units.test_sizing

No pytest dependency (none is used elsewhere in pipeline/); plain asserts, PASS/FAIL printed per
check, matching pipeline.units.test_flatten's own `__main__` block. All checks exercise the REAL
`sizing.build_rows` pure function (no data loader, no I/O), on a synthetic measured level:
  (a) A45 rows: x_pct == 1.0 always; attempts_per_day == 3/4/5 at the 3/4/5% daily limits.
  (b) pre_A45 rows: attempts_per_day == 1 always; x_pct == the row's own daily_limit_pct.
  (c) min_account_spx_usd == cost_spx_usd / (x_pct/100) for every row; the A45 4% row's minimum
      account is exactly 4x the pre_A45 4% row's (1% vs 4% of equity per trade, same cost).
  (d) cost_xsp_usd and cost_spy_usd are each exactly one tenth of cost_spx_usd, for every row.
"""
import sys

import numpy as np

from pipeline.units import sizing

LEVEL_DATE = "2026-09-11"
LEVEL_SPX_PTS = 7641.40
LEVEL_SPY_USD = 764.14


def _rows():
    return sizing.build_rows(LEVEL_DATE, LEVEL_SPX_PTS, LEVEL_SPY_USD)


def test_a45_x_pct_and_attempts():
    df = _rows()
    a45 = df[df["convention"] == "A45"].set_index("daily_limit_pct")
    assert (a45["x_pct"] == 1.0).all(), "A45 rows must all have x_pct == 1.0 (rule 1)"
    assert a45.loc[3.0, "attempts_per_day"] == 3, "A45 attempts_per_day at 3% limit must be 3"
    assert a45.loc[4.0, "attempts_per_day"] == 4, "A45 attempts_per_day at 4% limit must be 4"
    assert a45.loc[5.0, "attempts_per_day"] == 5, "A45 attempts_per_day at 5% limit must be 5"
    return True


def test_pre_a45_x_pct_and_attempts():
    df = _rows()
    pre = df[df["convention"] == "pre_A45"].set_index("daily_limit_pct")
    assert (pre["attempts_per_day"] == 1).all(), "pre_A45 rows must all have attempts_per_day == 1"
    for limit in (3.0, 4.0, 5.0):
        assert pre.loc[limit, "x_pct"] == limit, f"pre_A45 x_pct at {limit}% limit must equal the daily limit itself"
    return True


def test_min_account_arithmetic_and_a45_vs_pre_a45_ratio():
    df = _rows()
    computed = df["cost_spx_usd"] / (df["x_pct"] / 100)
    assert np.allclose(df["min_account_spx_usd"], computed), \
        "min_account_spx_usd must equal cost_spx_usd / (x_pct/100) for every row"
    pre4 = df[(df["convention"] == "pre_A45") & (df["daily_limit_pct"] == 4.0)].iloc[0]
    a4 = df[(df["convention"] == "A45") & (df["daily_limit_pct"] == 4.0)].iloc[0]
    assert np.isclose(a4["min_account_spx_usd"], 4 * pre4["min_account_spx_usd"]), \
        "A45's 4% row must need exactly 4x the pre_A45 4% row's minimum account (1% vs 4% per trade)"
    return True


def test_xsp_spy_one_tenth_of_spx():
    df = _rows()
    assert np.allclose(df["cost_xsp_usd"], df["cost_spx_usd"] / 10), "cost_xsp_usd must be exactly 1/10 of cost_spx_usd"
    assert np.allclose(df["cost_spy_usd"], df["cost_spx_usd"] / 10), "cost_spy_usd must be exactly 1/10 of cost_spx_usd"
    return True


def main():
    checks = [("A45 rows: x_pct == 1.0, attempts_per_day == 3/4/5", test_a45_x_pct_and_attempts),
              ("pre_A45 rows: attempts_per_day == 1, x_pct == the daily limit", test_pre_a45_x_pct_and_attempts),
              ("min_account_spx_usd arithmetic; A45 4% row == 4x pre_A45 4% row", test_min_account_arithmetic_and_a45_vs_pre_a45_ratio),
              ("cost_xsp_usd/cost_spy_usd are each exactly 1/10 of cost_spx_usd", test_xsp_spy_one_tenth_of_spx)]
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
