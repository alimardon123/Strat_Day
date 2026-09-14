"""Unit test for pipeline.units.sellvol (A43), runnable standalone:

    python -m pipeline.units.test_sellvol

No pytest dependency (none is used elsewhere in pipeline/); plain asserts, PASS/FAIL printed per
check, matching pipeline.units.test_eventvol's/test_realopt's own `__main__` block. Four checks,
per the task:
  (a) credit/max_loss/P&L arithmetic on an inline 4-leg fixture with hand-computed values --
      exercised through the REAL ingestion path (eventvol.load_0dte -> sellvol.build_structure ->
      sellvol.with_costs_and_sizing), including the causal strike-availability rule (a decoy
      strike that only prints AFTER the entry minute must be rejected in favour of the next-
      nearest strike that was actually tradable), not a reimplementation of the formulas, so a
      regression in any of the three functions fails this test.
  (b) the sizing rule (contracts = floor(4000 / (max_loss x 100))) on two cases.
  (c) the MAE computation (sellvol.compute_mae) on a 3-minute inline path: the worst mark, the
      "all four legs must have a print at that minute" rule (one leg's print removed at the worst
      minute must exclude that minute, not silently substitute a partial mark), and the floor-at-0
      convention (pipeline.playbook.mae's own convention) on an all-favourable path.
  (d) the skip path (0DTE file missing) writes header-only CSVs for all four output files under
      tempfile.mkdtemp().
All four checks write their temporary file(s), if any, under the system temporary directory and
remove them immediately after use -- nothing is left anywhere persistent (never under out/ or
data/).
"""
import os
import shutil
import sys
import tempfile

import numpy as np
import pandas as pd

from pipeline.units import eventvol, sellvol


def test_credit_maxloss_pnl_arithmetic():
    """One session, S1-shaped iron butterfly (ref_px=500.0, wing_pct=0.01, ATM shared body).
    Short legs at strike 500 (call and put); long put at 495 (1% below); long call: the THEORETICAL
    +1% target is 505, but strike 505/C only prints at mod 580 -- AFTER the 571 entry minute -- so
    the causal-availability rule must reject it and fall back to 506/C (which has an exact 571
    print), the next-nearest strike that was actually tradable at entry. Hand computation: credit =
    (2.50+2.30)-(1.80+1.60) = 1.40; call_wing_width = 506-500 = 6, put_wing_width = 500-495 = 5,
    wing_width = max(6,5) = 6; max_loss = 6-1.40 = 4.60; exit_debit = (1.20+1.00)-(0.60+0.50) =
    1.10; gross_pnl = 1.40-1.10 = 0.30."""
    fixture = pd.DataFrame([
        ("2024-02-01 14:31:00", "2024-02-01", 500, "C", 2.45, 2.55, 2.40, 2.50, 50),
        ("2024-02-01 20:59:00", "2024-02-01", 500, "C", 1.15, 1.25, 1.10, 1.20, 40),
        ("2024-02-01 14:31:00", "2024-02-01", 500, "P", 2.25, 2.35, 2.20, 2.30, 50),
        ("2024-02-01 20:59:00", "2024-02-01", 500, "P", 0.95, 1.05, 0.90, 1.00, 40),
        ("2024-02-01 14:31:00", "2024-02-01", 495, "P", 1.55, 1.65, 1.50, 1.60, 30),
        ("2024-02-01 20:59:00", "2024-02-01", 495, "P", 0.45, 0.55, 0.40, 0.50, 20),
        ("2024-02-01 14:31:00", "2024-02-01", 506, "C", 1.75, 1.85, 1.70, 1.80, 30),
        ("2024-02-01 20:59:00", "2024-02-01", 506, "C", 0.55, 0.65, 0.50, 0.60, 20),
        ("2024-02-01 14:40:00", "2024-02-01", 505, "C", 1.70, 1.80, 1.65, 1.75, 10),   # decoy: prints AFTER entry
        ("2024-02-01 14:31:00", "2024-02-01", 480, "C", 5.00, 5.10, 4.90, 5.00, 10),   # far decoy
        ("2024-02-01 14:31:00", "2024-02-01", 520, "P", 0.05, 0.06, 0.04, 0.05, 10),   # far decoy
    ], columns=["ts", "expiry", "strike", "right", "open", "high", "low", "close", "volume"])
    tmp_dir = tempfile.mkdtemp()
    path = os.path.join(tmp_dir, "sellvol_pnl_fixture.csv")
    try:
        fixture.to_csv(path, index=False)
        odte = eventvol.load_0dte(path)
        options_day = dict(tuple(odte.groupby("expiry")))["2024-02-01"]

        st = sellvol.build_structure(options_day, 500.0, eventvol.MOD_0931, 0.01, None)
        assert st is not None, "build_structure returned None on a fully-priceable fixture"
        assert st["short_call_strike"] == 500.0 and st["short_put_strike"] == 500.0, \
            "iron butterfly's short call/put must share ONE ATM strike"
        assert st["long_put_strike"] == 495.0
        assert st["long_call_strike"] == 506.0, \
            f"causal rule should reject strike 505 (prints only after entry) and fall back to 506, got {st['long_call_strike']}"

        credit_expected = (2.50 + 2.30) - (1.80 + 1.60)
        assert np.isclose(st["credit"], credit_expected), f"{st['credit']} != {credit_expected}"
        assert np.isclose(st["call_wing_width"], 6.0) and np.isclose(st["put_wing_width"], 5.0)
        assert np.isclose(st["wing_width"], 6.0), "wing_width must be the WIDER of the two sides"
        max_loss_expected = 6.0 - credit_expected
        assert np.isclose(st["max_loss"], max_loss_expected), f"{st['max_loss']} != {max_loss_expected}"
        exit_debit_expected = (1.20 + 1.00) - (0.60 + 0.50)
        gross_pnl_expected = credit_expected - exit_debit_expected
        assert np.isclose(st["gross_pnl"], gross_pnl_expected), f"{st['gross_pnl']} != {gross_pnl_expected}"

        trades = pd.DataFrame([dict(st, date=pd.Timestamp("2024-02-01"))], columns=sellvol.TRADE_RAW_COLS)
        priced = sellvol.with_costs_and_sizing(trades).iloc[0]
        for i, cost in enumerate(sellvol.COST_PER_LEG):
            net_pnl_expected = gross_pnl_expected - 4 * cost
            net_pct_expected = net_pnl_expected / max_loss_expected * 100
            assert np.isclose(priced[f"net_pnl_cost{i}"], net_pnl_expected), \
                f"cost {cost}: net_pnl {priced[f'net_pnl_cost{i}']} != {net_pnl_expected}"
            assert np.isclose(priced[f"net_pct_maxloss_cost{i}"], net_pct_expected), \
                f"cost {cost}: net_pct {priced[f'net_pct_maxloss_cost{i}']} != {net_pct_expected}"
        contracts_expected = np.floor(4000.0 / (max_loss_expected * 100.0))
        assert priced["contracts"] == contracts_expected, f"{priced['contracts']} != {contracts_expected}"

        # A day with NO put contract listed at all (both put legs unresolvable) is skipped whole,
        # never a 2-leg (calls only) structure.
        no_puts = options_day.loc[options_day["right"] != "P"]
        assert sellvol.build_structure(no_puts, 500.0, eventvol.MOD_0931, 0.01, None) is None, \
            "a structure missing both put legs entirely must be skipped (None), not returned partial"
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)
    return True


def test_sizing_rule():
    """contracts = floor(4000 / (max_loss x 100)) (ACCEPTANCE A43's own numbers: 4% of a $100,000
    account), on two hand-picked cases: max_loss=2.00 -> floor(4000/200) = 20; max_loss=3.33 ->
    floor(4000/333) = 12 (12.012... truncates down, not rounds)."""
    df = pd.DataFrame({"max_loss": [2.00, 3.33], "gross_pnl": [0.0, 0.0]})
    priced = sellvol.with_costs_and_sizing(df)
    assert priced["contracts"].iloc[0] == 20.0, priced["contracts"].iloc[0]
    assert priced["contracts"].iloc[1] == 12.0, priced["contracts"].iloc[1]
    return True


def test_mae_three_minute_path():
    """Two interior minutes (572, 573) between a 571 entry and a 574 window edge; credit=1.40,
    max_loss=4.60 (this module's own S1-shaped numbers, see test_credit_maxloss_pnl_arithmetic).
    At 572: debit=(3.20+2.10)-(1.95+1.55)=1.80 -> mark = credit-debit = -0.40 (the worst mark). At
    573: debit=(2.80+2.00)-(1.85+1.50)=1.45 -> mark = -0.05. MAE = the worst mark, floored at 0 ->
    mae_dollar=0.40, mae_pct_credit=0.40/1.40*100, mae_pct_maxloss=0.40/4.60*100. Removing the long
    put's OWN print at minute 572 must exclude that minute from the marks entirely (not substitute
    a partial 3-leg mark), leaving only minute 573's -0.05 -> mae_dollar=0.05. An all-favourable
    path (debit=0 throughout) must floor at exactly 0.0, never a positive number."""
    credit, max_loss = 1.40, 4.60
    strikes = {"short_call": ("C", 500.0), "short_put": ("P", 500.0),
              "long_call": ("C", 506.0), "long_put": ("P", 495.0)}
    rows = [
        ("C", 500.0, 572, 3.20), ("P", 500.0, 572, 2.10), ("C", 506.0, 572, 1.95), ("P", 495.0, 572, 1.55),
        ("C", 500.0, 573, 2.80), ("P", 500.0, 573, 2.00), ("C", 506.0, 573, 1.85), ("P", 495.0, 573, 1.50),
    ]
    options_day = pd.DataFrame(rows, columns=["right", "strike", "mod", "close"])

    mae_dollar, mae_pct_credit, mae_pct_maxloss = sellvol.compute_mae(options_day, 571, 574, strikes, credit, max_loss)
    assert np.isclose(mae_dollar, 0.40), mae_dollar
    assert np.isclose(mae_pct_credit, 0.40 / 1.40 * 100), mae_pct_credit
    assert np.isclose(mae_pct_maxloss, 0.40 / 4.60 * 100), mae_pct_maxloss

    missing_leg = options_day.loc[~((options_day["mod"] == 572) & (options_day["right"] == "P")
                                     & (options_day["strike"] == 495.0))]
    mae2_dollar, _, _ = sellvol.compute_mae(missing_leg, 571, 574, strikes, credit, max_loss)
    assert np.isclose(mae2_dollar, 0.05), \
        f"minute 572 (one leg missing) must be excluded from the marks, expected 0.05 got {mae2_dollar}"

    favourable = pd.DataFrame([("C", 500.0, 572, 1.00), ("P", 500.0, 572, 1.00),
                               ("C", 506.0, 572, 1.00), ("P", 495.0, 572, 1.00)],
                              columns=["right", "strike", "mod", "close"])
    mae_fav, _, _ = sellvol.compute_mae(favourable, 571, 574, strikes, credit, max_loss)
    assert mae_fav == 0.0, f"an all-favourable path must floor MAE at exactly 0.0, got {mae_fav}"

    no_common = sellvol.compute_mae(options_day.iloc[:0], 571, 574, strikes, credit, max_loss)
    assert all(np.isnan(x) for x in no_common), "no common minute across all four legs must be NaN, never 0"
    return True


def test_skip_path():
    """main() with a deliberately-missing 0DTE path writes all FOUR output files with a header row
    only (matching OUT_COLS/TRADE_COLS/EQUITY_COLS/BY_YEAR_COLS exactly) and returns normally (no
    exception, no out/ or data/ writes) -- `by_year_out` is redirected into the same tempdir so the
    fixed-name `out/sellvol_by_year.csv` is never touched by this test."""
    tmp_dir = tempfile.mkdtemp()
    out_path = os.path.join(tmp_dir, "sellvol_candidates.csv")
    trades_path = os.path.join(tmp_dir, "sellvol_trades.csv")
    equity_path = os.path.join(tmp_dir, "sellvol_equity.csv")
    by_year_path = os.path.join(tmp_dir, "sellvol_by_year.csv")
    missing_data = os.path.join(tmp_dir, "does_not_exist_spy_0dte.csv.gz")
    try:
        assert not os.path.exists(missing_data)
        sellvol.main("extended", out_path, data_path=missing_data, by_year_out=by_year_path)
        for path, cols in ((out_path, sellvol.OUT_COLS), (trades_path, sellvol.TRADE_COLS),
                           (equity_path, sellvol.EQUITY_COLS), (by_year_path, sellvol.BY_YEAR_COLS)):
            assert os.path.exists(path), f"main() did not write {path} on the skip path"
            res = pd.read_csv(path)
            assert list(res.columns) == cols, f"{path} header mismatch: {list(res.columns)}"
            assert len(res) == 0, f"{path}: expected header-only (0 rows), got {len(res)}"
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)
    return True


def main():
    checks = [("credit/max_loss/P&L arithmetic on the 4-leg fixture (causal strike rule included)",
              test_credit_maxloss_pnl_arithmetic),
              ("sizing rule (contracts = floor(4000 / (max_loss x 100)))", test_sizing_rule),
              ("MAE on a 3-minute inline path (worst mark, all-four-legs rule, floor at 0)", test_mae_three_minute_path),
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
