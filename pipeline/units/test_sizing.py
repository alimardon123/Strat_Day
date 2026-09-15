"""Unit test for pipeline.units.sizing (A45 forward-sizing table), runnable standalone:

    python -m pipeline.units.test_sizing

No pytest dependency (none is used elsewhere in pipeline/); plain asserts, PASS/FAIL printed per
check, matching pipeline.units.test_flatten's own `__main__` block. Checks (a)-(d) exercise the
REAL `sizing.build_rows` pure function (no data loader, no I/O), on a synthetic measured level;
checks (e)-(g) were added to kill three mutants a ratio-only test suite cannot catch (review
round: idxmax->idxmin, ITM_PCT/CONTRACT_MULT scaled together, and a truncated-session level
silently accepted) -- (e) and (f)/(g) exercise the REAL `sizing.measure_level` pure function on
synthetic session frames, and (f) pins an ABSOLUTE dollar figure rather than a ratio:
  (a) A45 rows: x_pct == 1.0 always; attempts_per_day == 3/4/5 at the 3/4/5% daily limits.
  (b) pre_A45 rows: attempts_per_day == 1 always; x_pct == the row's own daily_limit_pct.
  (c) min_account_spx_usd == cost_spx_usd / (x_pct/100) for every row; the A45 4% row's minimum
      account is exactly 4x the pre_A45 4% row's (1% vs 4% of equity per trade, same cost).
  (d) cost_xsp_usd and cost_spy_usd are each exactly one tenth of cost_spx_usd, for every row.
  (e) measure_level returns the LAST bar of a session (highest mod), not the first -- kills the
      `day["mod"].idxmax()` -> `idxmin()` mutant, which a ratio check can never see because both
      readings still satisfy every ratio in (a)-(d).
  (f) at a level of exactly 7641.40 SPX points, cost_spx_usd and the A45 min_account_spx_usd are
      pinned to the cent -- kills the `ITM_PCT`/`CONTRACT_MULT` mutants (e.g. 0.02->0.05 with
      100->10 nets out to the same ratios as the original but a 4x-wrong absolute minimum
      account).
  (g) measure_level rejects a session truncated before the close (bars < sessions.FULL_BARS or
      max mod < sessions.RTH_END - 5) in favour of the most recent COMPLETE prior session.
"""
import sys

import numpy as np
import pandas as pd

from pipeline import sessions
from pipeline.units import sizing

LEVEL_DATE = "2026-09-11"
LEVEL_SPX_PTS = 7641.40
LEVEL_SPY_USD = 764.14
LEVEL_SESSION_BARS = 390


def _rows():
    return sizing.build_rows(LEVEL_DATE, LEVEL_SPX_PTS, LEVEL_SPY_USD, LEVEL_SESSION_BARS)


def _session(date, mods, closes):
    """A synthetic session frame with only the columns measure_level touches."""
    return pd.DataFrame({"date": [pd.Timestamp(date)] * len(mods), "mod": mods, "close": closes})


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


def test_measure_level_picks_last_bar_not_first():
    mods = list(range(sessions.RTH_START, sessions.RTH_END))   # 570..959: a full RTH session
    closes = [float(m) for m in mods]                          # close == mod, so first/last bars differ
    frame = _session("2026-02-02", mods, closes)
    got = sizing.measure_level(frame)
    assert got is not None, "a full-length complete session must be measured, not rejected"
    level_date, level_spx_pts, level_session_bars = got
    assert level_spx_pts == closes[-1], "measure_level must take the close of the HIGHEST-mod (last) bar"
    assert level_spx_pts != closes[0], "measure_level must not take the close of the lowest-mod (first) bar"
    assert level_session_bars == len(mods)
    return True


def test_absolute_cost_and_min_account_at_known_level():
    df = sizing.build_rows(LEVEL_DATE, 7641.40, 764.14, LEVEL_SESSION_BARS)
    cost_spx = df["cost_spx_usd"].iloc[0]
    assert round(float(cost_spx), 2) == 15282.80, \
        f"2% ITM cost at S=7641.40 must be $15,282.80 to the cent, got {cost_spx}"
    a45_min = df[df["convention"] == "A45"]["min_account_spx_usd"].iloc[0]
    assert round(float(a45_min), 2) == 1528280.00, \
        f"A45 (x=1%) minimum account at S=7641.40 must be $1,528,280.00 to the cent, got {a45_min}"
    return True


def test_measure_level_rejects_truncated_session_for_prior_complete_one():
    complete_mods = list(range(sessions.RTH_START, sessions.RTH_END))   # a full RTH session
    complete_closes = [7600.0] * len(complete_mods)
    complete = _session("2026-09-10", complete_mods, complete_closes)
    # 2026-09-11 truncated at 14:35 ET (mod 875), sessions.MIN_BARS + 6 = 306 bars -- the
    # reviewer's own reproduction of defect 2 (bars < FULL_BARS AND max mod < RTH_END - 5).
    trunc_bars = sessions.MIN_BARS + 6
    trunc_mods = list(range(sessions.RTH_START, sessions.RTH_START + trunc_bars))
    trunc_closes = [7653.95] * len(trunc_mods)
    truncated = _session("2026-09-11", trunc_mods, trunc_closes)
    frame = pd.concat([complete, truncated], ignore_index=True)
    got = sizing.measure_level(frame)
    assert got is not None, "the frame has one complete session; measure_level must not reject the whole frame"
    level_date, level_spx_pts, level_session_bars = got
    assert level_date == pd.Timestamp("2026-09-10"), \
        f"a truncated latest session must be REJECTED in favour of the prior complete session, got {level_date}"
    assert level_spx_pts == 7600.0
    assert level_session_bars == len(complete_mods)
    return True


def main():
    checks = [("A45 rows: x_pct == 1.0, attempts_per_day == 3/4/5", test_a45_x_pct_and_attempts),
              ("pre_A45 rows: attempts_per_day == 1, x_pct == the daily limit", test_pre_a45_x_pct_and_attempts),
              ("min_account_spx_usd arithmetic; A45 4% row == 4x pre_A45 4% row", test_min_account_arithmetic_and_a45_vs_pre_a45_ratio),
              ("cost_xsp_usd/cost_spy_usd are each exactly 1/10 of cost_spx_usd", test_xsp_spy_one_tenth_of_spx),
              ("measure_level takes the last (highest-mod) bar of a session, not the first", test_measure_level_picks_last_bar_not_first),
              ("cost_spx_usd and A45 min_account_spx_usd pinned to the cent at S=7641.40", test_absolute_cost_and_min_account_at_known_level),
              ("measure_level rejects a truncated latest session for the prior complete one", test_measure_level_rejects_truncated_session_for_prior_complete_one)]
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
