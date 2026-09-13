"""Unit test for pipeline.units.eventvol (A42), runnable standalone:

    python -m pipeline.units.test_eventvol

No pytest dependency (none is used elsewhere in pipeline/); plain asserts, PASS/FAIL printed per
check, matching pipeline.sessions's own gate()-style `__main__` block and pipeline.units.
test_letf's structure. Three checks, per the task:
  (a) P&L arithmetic on a 2-leg inline fixture -- exercised through the REAL ingestion path
      (eventvol.load_0dte -> eventvol.pair_trade -> eventvol.with_costs), including the
      next-bar-open entry fallback and the "either leg missing -> whole day skipped" rule, not a
      reimplementation of the formula, so a regression in any of the three functions fails this
      test.
  (b) FOMC date membership: every ACCEPTANCE A42 date parses and is a weekday.
  (c) the skip path (0DTE file missing) writes header-only CSVs under tempfile.mkdtemp().
Both (a) and (c) write their temporary file(s) under the system temporary directory and remove
them immediately after use -- nothing is left anywhere persistent (never under out/ or data/).
"""
import os
import shutil
import sys
import tempfile

import numpy as np
import pandas as pd

from pipeline.units import eventvol


def test_pnl_arithmetic():
    """One session, strike 100 nearest a 100.0 reference (two decoy strikes, 99/101, present so
    the fixture looks like a real slice of the file, not a contrived pair -- must NOT be picked).
    Call has an exact 09:31 bar (entry close 2.10) and an exact 15:59 bar (exit close 2.60). Put
    has NO exact 09:31 bar -- its next available bar is at 09:35 (open 1.75, module docstring
    point 2: entry = the NEXT bar's OPEN, not its close) -- and an exact 15:59 bar (exit close
    1.35). Hand computation: premium_total = 2.10 + 1.75 = 3.85; exit_total = 2.60 + 1.35 = 3.95;
    gross_usd = 0.10; gross_pct = 0.10 / 3.85 * 100 = 2.597402597...%; net_usd/net_pct at cost
    0/0.10/0.20 subtract that ONE flat amount once from the pair (module docstring point 6), never
    split across the two legs."""
    fixture = pd.DataFrame([
        ("2024-02-01 14:31:00", "2024-02-01", 100, "C", 2.00, 2.15, 1.95, 2.10, 50),
        ("2024-02-01 20:59:00", "2024-02-01", 100, "C", 2.55, 2.65, 2.45, 2.60, 40),
        ("2024-02-01 14:35:00", "2024-02-01", 100, "P", 1.75, 1.85, 1.70, 1.85, 30),
        ("2024-02-01 20:59:00", "2024-02-01", 100, "P", 1.45, 1.50, 1.30, 1.35, 20),
        ("2024-02-01 14:31:00", "2024-02-01", 99, "C", 3.00, 3.10, 2.90, 3.05, 10),
        ("2024-02-01 14:31:00", "2024-02-01", 101, "P", 1.00, 1.05, 0.95, 1.02, 10),
    ], columns=["ts", "expiry", "strike", "right", "open", "high", "low", "close", "volume"])
    tmp_dir = tempfile.mkdtemp()
    path = os.path.join(tmp_dir, "eventvol_pnl_fixture.csv")
    try:
        fixture.to_csv(path, index=False)
        odte = eventvol.load_0dte(path)
        assert set(odte["strike"]) == {99.0, 100.0, 101.0}
        groups = dict(tuple(odte.groupby("expiry")))
        options_day = groups["2024-02-01"]

        trade = eventvol.pair_trade(options_day, 100.0, eventvol.MOD_0931)
        assert trade is not None, "pair_trade returned None on a fully-priceable fixture"
        assert trade["strike"] == 100.0, f"picked strike {trade['strike']} != nearest 100.0 (decoys 99/101 present)"
        assert np.isclose(trade["call_entry_px"], 2.10) and trade["call_entry_mod"] == eventvol.MOD_0931, \
            "call should use the EXACT 09:31 bar close"
        assert np.isclose(trade["put_entry_px"], 1.75) and trade["put_entry_mod"] == 575, \
            f"put should use the NEXT bar's OPEN (1.75 at mod 575), got {trade['put_entry_px']} at {trade['put_entry_mod']}"
        assert np.isclose(trade["call_exit_px"], 2.60) and np.isclose(trade["put_exit_px"], 1.35)

        premium_expected, exit_expected = 2.10 + 1.75, 2.60 + 1.35
        gross_usd_expected = exit_expected - premium_expected
        gross_pct_expected = gross_usd_expected / premium_expected * 100
        assert np.isclose(trade["premium_total"], premium_expected)
        assert np.isclose(trade["exit_total"], exit_expected)
        assert np.isclose(trade["gross_usd"], gross_usd_expected), f"{trade['gross_usd']} != {gross_usd_expected}"
        assert np.isclose(trade["gross_pct"], gross_pct_expected), f"{trade['gross_pct']} != {gross_pct_expected}"

        trade["date"] = pd.Timestamp("2024-02-01")
        trades = pd.DataFrame([trade], columns=eventvol.TRADE_RAW_COLS)
        priced = eventvol.with_costs(trades).iloc[0]
        for i, cost in enumerate(eventvol.COSTS):
            net_usd_expected = gross_usd_expected - cost
            net_pct_expected = gross_pct_expected - 100 * cost / premium_expected
            assert np.isclose(priced[f"net_usd_cost{i}"], net_usd_expected), \
                f"cost {cost}: net_usd {priced[f'net_usd_cost{i}']} != {net_usd_expected}"
            assert np.isclose(priced[f"net_pct_cost{i}"], net_pct_expected), \
                f"cost {cost}: net_pct {priced[f'net_pct_cost{i}']} != {net_pct_expected}"

        # A day where the put leg has NO bars at all (neither an exact entry nor a next bar, nor an
        # exit) is skipped whole -- never a lone naked call (module docstring point 2/3).
        call_only = options_day.loc[options_day["right"] == "C"]
        assert eventvol.pair_trade(call_only, 100.0, eventvol.MOD_0931) is None, \
            "a day with only a call leg must be skipped (None), not returned as a partial trade"
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)
    return True


def test_fomc_dates():
    """Every ACCEPTANCE A42 FOMC date parses to a real calendar date and falls on a weekday
    (Monday-Friday); 21 dates total (8 in 2024, 8 in 2025, 5 in 2026), no duplicates."""
    assert len(eventvol.FOMC_DATES) == 21, f"expected 21 FOMC dates, got {len(eventvol.FOMC_DATES)}"
    assert len(set(eventvol.FOMC_DATES)) == 21, "duplicate FOMC dates"
    parsed = eventvol.fomc_dates()
    assert len(parsed) == len(eventvol.FOMC_DATES)
    for raw, ts in zip(eventvol.FOMC_DATES, parsed):
        assert isinstance(ts, pd.Timestamp), f"{raw!r} did not parse to a Timestamp"
        assert ts.weekday() < 5, f"{raw} is a weekend day (weekday={ts.weekday()})"
    by_year = {2024: 8, 2025: 8, 2026: 5}
    for year, expected_n in by_year.items():
        n = sum(1 for ts in parsed if ts.year == year)
        assert n == expected_n, f"expected {expected_n} FOMC dates in {year}, got {n}"
    return True


def test_skip_path():
    """main() with a deliberately-missing 0DTE path writes both output files with a header row
    only (matching OUT_COLS/TRADE_COLS exactly, `out/eventvol_trades.csv`'s own fixed name --
    module docstring on `_trades_path`) and returns normally (no exception, no out/ or data/
    writes)."""
    tmp_dir = tempfile.mkdtemp()
    out_path = os.path.join(tmp_dir, "eventvol_candidates.csv")
    trades_path = os.path.join(tmp_dir, "eventvol_trades.csv")
    missing_data = os.path.join(tmp_dir, "does_not_exist_spy_0dte.csv.gz")
    try:
        assert not os.path.exists(missing_data)
        eventvol.main("extended", out_path, data_path=missing_data)
        assert os.path.exists(out_path), "main() did not write the output CSV on the skip path"
        assert os.path.exists(trades_path), "main() did not write the trades CSV on the skip path"
        res = pd.read_csv(out_path)
        assert list(res.columns) == eventvol.OUT_COLS, f"header mismatch: {list(res.columns)}"
        assert len(res) == 0, f"expected header-only (0 rows), got {len(res)}"
        tr = pd.read_csv(trades_path)
        assert list(tr.columns) == eventvol.TRADE_COLS, f"trades header mismatch: {list(tr.columns)}"
        assert len(tr) == 0, f"expected header-only trades (0 rows), got {len(tr)}"
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)
    return True


def main():
    checks = [("P&L arithmetic on the 2-leg inline fixture", test_pnl_arithmetic),
              ("FOMC date membership (parses, weekday, 21 dates)", test_fomc_dates),
              ("skip path writes header-only outputs (0DTE file missing)", test_skip_path)]
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
