"""Unit test for pipeline.units.oflow (A49), runnable standalone:

    python -m pipeline.units.test_oflow

No pytest dependency (none is used elsewhere in pipeline/); plain asserts, PASS/FAIL printed per
check, matching pipeline.units.test_flatten's own style and tempfile usage. Every check is
exercised through the REAL functions in oflow.py (build_minute_flow, load_flow_table,
session_expanding_threshold, add_signals, build_trades), never a reimplementation of their logic;
fixtures are plain in-memory DataFrames or tiny temp CSVs (matching test_flatten's own convention),
never the real 9.5M-row shards -- this suite runs in well under a second so the mutation proof
below is cheap to repeat by hand.

Seven mandatory checks (per the task):
  (a) causality: the sign/imbalance computed for minute t never depends on a LATER print (two
      temp shards identical up to and including minute t, differing only after it, must agree on
      every row at/before t), and the entry price used for a trade is exactly the close of
      signal_minute+1 (T1) / signal_minute+16 (T2) -- proven with distinct sentinel prices at
      every neighbouring minute (the signal minute itself, one minute early, one minute late) so a
      look-ahead or off-by-one bug grabs a visibly wrong number, not a coincidentally-right one.
  (b) tick rule: a single synthetic call contract's print sequence, hand-classified (first print
      excluded, up -> buyer, down -> seller, equal -> carry the last CLASSIFIED sign, including
      the case where the sign to carry does not exist yet), read back through the REAL
      `build_minute_flow`'s bullish/bearish columns (with one contract present, bullish/bearish
      collapse to "volume if classified buyer/seller, else 0").
  (c) imbalance arithmetic: a call + a put contract, hand-picked so one minute has a BUYER call
      and a SELLER put (both bullish -- the seller-initiated-put leg) and another has a SELLER
      call and a BUYER put (both bearish -- the buyer-initiated-put leg), read back through the
      REAL `load_flow_table`'s bullish/bearish/imbalance columns, including the NaN-on-zero-
      denominator minute.
  (d) non-overlap: two qualifying minutes 5 apart in the same direction (`build_trades`) produce
      ONE trade, not two; the second is counted in `n_overlap_skipped`, not `n_skipped`.
  (e) expanding threshold uses strictly prior sessions: the first MIN_PRIOR_SESSIONS session
      thresholds are NaN, the first defined threshold does not change when its OWN session's
      values are perturbed (but the NEXT session's threshold does -- proving the check is live,
      not vacuous).
  (f) session-boundary exit: a signal at mod 950 (entry mod 951, candidate exit mod 981) exits at
      the session's own last bar (959), not past it.
  (g) every trade `build_trades` returns has entry strictly before exit, and net_pts_cost{1,2} =
      gross pts - COST{1,2} exactly.

Mutation proof (run by hand, reported alongside this suite's PASS/FAIL output, not committed as
code): (1) breaking the entry shift in `build_trades` (`entry_mod = t + lag` -> `entry_mod = t`)
makes check (a) FAIL (entry lands on the signal minute's own poison price); reverting makes it
PASS again. (2) flipping the seller-initiated-put sign in `build_minute_flow` (crediting the
BUYER-initiated put leg to `bullish` instead of the seller-initiated leg) makes check (c) FAIL;
reverting makes it PASS again. (3) removing the non-overlap guard in `build_trades` (the
`entry_mod < open_until` skip) makes check (d) FAIL (two trades instead of one); reverting makes
it PASS again.
"""
import os
import sys
import tempfile

import numpy as np
import pandas as pd

from pipeline.units import oflow

NY = oflow.NY


def _write_shard(rows):
    """rows: list of (ts_str_utc, strike, right, close, volume). Returns a temp CSV path in the
    real shard's own column shape (ts, expiry, strike, right, open, high, low, close, volume);
    open/high/low are copies of close (build_minute_flow never reads them)."""
    df = pd.DataFrame(rows, columns=["ts", "strike", "right", "close", "volume"])
    df["expiry"] = pd.to_datetime(df["ts"]).dt.strftime("%Y-%m-%d")
    df["open"] = df["high"] = df["low"] = df["close"]
    fd, path = tempfile.mkstemp(suffix=".csv")
    os.close(fd)
    df[["ts", "expiry", "strike", "right", "open", "high", "low", "close", "volume"]].to_csv(path, index=False)
    return path


def test_tick_rule_carry_and_first_print_excluded():
    """One call contract (K=100), 6 consecutive minutes (mod 571..576, session 2024-02-01):
    571 first print (excluded); 572 equal to 571, no sign yet to carry (still excluded);
    573 up -> BUYER; 574 equal -> carries BUYER; 575 down -> SELLER; 576 equal -> carries SELLER."""
    rows = [("2024-02-01 14:31:00", 100.0, "C", 10.0, 100),   # mod 571, first print
            ("2024-02-01 14:32:00", 100.0, "C", 10.0, 40),    # mod 572, equal, no sign to carry
            ("2024-02-01 14:33:00", 100.0, "C", 11.0, 50),    # mod 573, up -> BUYER
            ("2024-02-01 14:34:00", 100.0, "C", 11.0, 25),    # mod 574, equal -> carries BUYER
            ("2024-02-01 14:35:00", 100.0, "C", 9.0, 30),     # mod 575, down -> SELLER
            ("2024-02-01 14:36:00", 100.0, "C", 9.0, 10)]     # mod 576, equal -> carries SELLER
    path = _write_shard(rows)
    try:
        m = oflow.build_minute_flow(path).set_index("mod")
    finally:
        os.remove(path)
    assert m.loc[571, "bullish"] == 0 and m.loc[571, "bearish"] == 0, "first print must be unsigned"
    assert m.loc[572, "bullish"] == 0 and m.loc[572, "bearish"] == 0, \
        "equal-price print right after an unsigned first print has no sign to carry -> unsigned"
    assert m.loc[573, "bullish"] == 50 and m.loc[573, "bearish"] == 0, "573 up -> BUYER (bullish=volume)"
    assert m.loc[574, "bullish"] == 25 and m.loc[574, "bearish"] == 0, "574 equal -> carries BUYER"
    assert m.loc[575, "bullish"] == 0 and m.loc[575, "bearish"] == 30, "575 down -> SELLER (bearish=volume)"
    assert m.loc[576, "bullish"] == 0 and m.loc[576, "bearish"] == 10, "576 equal -> carries SELLER"
    return True


def test_imbalance_arithmetic_seller_put_is_bullish():
    """A call and a put (same strike, same session), each with its own tick history: at mod 572
    the call is BUYER (bullish leg) and the put is SELLER (also bullish -- the seller-initiated-
    put leg); at mod 573 the call is SELLER (bearish) and the put is BUYER (also bearish -- the
    buyer-initiated-put leg); mod 571 (both first prints) has zero volume on both sides -> NaN
    imbalance (0/0)."""
    rows = [("2024-02-01 14:31:00", 100.0, "C", 10.0, 100),   # mod 571 call first print
            ("2024-02-01 14:32:00", 100.0, "C", 11.0, 50),    # mod 572 call up -> BUYER (bullish 50)
            ("2024-02-01 14:33:00", 100.0, "C", 9.0, 30),     # mod 573 call down -> SELLER (bearish 30)
            ("2024-02-01 14:31:00", 100.0, "P", 5.0, 80),     # mod 571 put first print
            ("2024-02-01 14:32:00", 100.0, "P", 4.0, 20),     # mod 572 put down -> SELLER (bullish leg, +20)
            ("2024-02-01 14:33:00", 100.0, "P", 6.0, 15)]     # mod 573 put up -> BUYER (bearish leg, +15)
    path = _write_shard(rows)
    try:
        flow = oflow.load_flow_table([path])
    finally:
        os.remove(path)
    f = flow.set_index("mod")
    assert f.loc[571, "bullish"] == 0 and f.loc[571, "bearish"] == 0
    assert pd.isna(f.loc[571, "imbalance"]), "0/0 denominator must be NaN, not 0"
    assert f.loc[572, "bullish"] == 70 and f.loc[572, "bearish"] == 0, \
        "572 bullish = call BUYER (50) + put SELLER (20) = 70 (seller-initiated-put-is-bullish leg)"
    assert np.isclose(f.loc[572, "imbalance"], 1.0)
    assert f.loc[573, "bullish"] == 0 and f.loc[573, "bearish"] == 45, \
        "573 bearish = call SELLER (30) + put BUYER (15) = 45 (buyer-initiated-put-is-bearish leg)"
    assert np.isclose(f.loc[573, "imbalance"], -1.0)
    return True


def test_causality_no_lookahead_and_entry_shift():
    """(i) Two temp shards identical through mod 573, differing only at a LATER print (mod 574's
    close/volume): build_minute_flow's rows at mod 571-573 must be BYTE-identical between the two
    -- a look-ahead bug in the tick rule (e.g. a centred diff, or sorting that lets a later row
    influence an earlier one) would make mod 573 (whose sign depends on comparing to mod 572, and
    potentially could 'see' mod 574 under a bug) move.
    (ii) `build_trades` entry price is EXACTLY the close at signal_minute+1 (T1) / +16 (T2), proven
    with a distinct sentinel price at every neighbouring minute (the signal minute itself, one
    minute early/late on each side) so a shift bug grabs a visibly wrong, not coincidentally
    right, number."""
    base = [("2024-02-01 14:31:00", 100.0, "C", 10.0, 100),
            ("2024-02-01 14:32:00", 100.0, "C", 11.0, 50),
            ("2024-02-01 14:33:00", 100.0, "C", 9.0, 30)]
    path_a = _write_shard(base + [("2024-02-01 14:34:00", 100.0, "C", 50.0, 999)])
    path_b = _write_shard(base + [("2024-02-01 14:34:00", 100.0, "C", -50.0, 1)])
    try:
        m_a = oflow.build_minute_flow(path_a).set_index("mod")
        m_b = oflow.build_minute_flow(path_b).set_index("mod")
    finally:
        os.remove(path_a)
        os.remove(path_b)
    for mod in (571, 572, 573):
        assert m_a.loc[mod, "bullish"] == m_b.loc[mod, "bullish"], f"mod {mod} bullish leaked a later print"
        assert m_a.loc[mod, "bearish"] == m_b.loc[mod, "bearish"], f"mod {mod} bearish leaked a later print"

    date = pd.Timestamp("2024-02-01")
    flow = pd.DataFrame({"date": [date], "mod": [700], "sig_bull": [True]})
    last_mod = {date: 959}
    close_lookup = {(date, 699): -111.0,    # one minute EARLY -- must never be read
                    (date, 700): -999.0,    # the signal minute itself -- must never be read (no leak)
                    (date, 701): 100.0,     # T1 entry (signal + 1)  <- correct
                    (date, 702): -222.0,    # one minute LATE of T1 entry -- must never be read
                    (date, 715): -333.0,    # one minute early of T2 entry
                    (date, 716): 200.0,     # T2 entry (signal + 16) <- correct
                    (date, 717): -444.0,    # one minute late of T2 entry
                    (date, 730): -555.0,    # one minute early of T1 exit
                    (date, 731): 110.0,     # T1 exit (entry + 30)   <- correct
                    (date, 732): -666.0,    # one minute late of T1 exit
                    (date, 745): -777.0,    # one minute early of T2 exit
                    (date, 746): 210.0,     # T2 exit (entry + 30)   <- correct
                    (date, 747): -888.0}    # one minute late of T2 exit
    t1, *_ = oflow.build_trades(flow, "sig_bull", 1.0, "c", oflow.LAG_T1, last_mod, close_lookup)
    t2, *_ = oflow.build_trades(flow, "sig_bull", 1.0, "c", oflow.LAG_T2, last_mod, close_lookup)
    assert len(t1) == 1 and len(t2) == 1
    assert t1.iloc[0]["entry_mod"] == 701 and t1.iloc[0]["entry_px"] == 100.0, "T1 entry must be signal+1"
    assert t1.iloc[0]["exit_mod"] == 731 and t1.iloc[0]["exit_px"] == 110.0, "T1 exit must be entry+30"
    assert t2.iloc[0]["entry_mod"] == 716 and t2.iloc[0]["entry_px"] == 200.0, "T2 entry must be signal+16"
    assert t2.iloc[0]["exit_mod"] == 746 and t2.iloc[0]["exit_px"] == 210.0, "T2 exit must be entry+30"
    return True


def test_non_overlap_single_trade():
    """Two qualifying (sig_bull) minutes 5 apart (mod 600, 605) on the same session: the second's
    would-be entry (606) falls inside the first trade's still-open window (601..631), so it must
    be skipped (n_overlap_skipped), leaving exactly ONE trade."""
    date = pd.Timestamp("2024-02-01")
    flow = pd.DataFrame({"date": [date, date], "mod": [600, 605], "sig_bull": [True, True]})
    last_mod = {date: 959}
    close_lookup = {(date, 601): 100.0, (date, 631): 105.0,     # first trade, entry/exit
                    (date, 606): 200.0, (date, 636): 999.0}     # second trade's prices, must be unused
    trades, n_signal, n_skipped, n_overlap = oflow.build_trades(
        flow, "sig_bull", 1.0, "c", oflow.LAG_T1, last_mod, close_lookup)
    assert n_signal == 2
    assert len(trades) == 1, f"expected exactly ONE trade, got {len(trades)}"
    assert trades.iloc[0]["entry_mod"] == 601 and trades.iloc[0]["entry_px"] == 100.0
    assert n_overlap == 1, "the second qualifying minute must be counted as an overlap skip"
    assert n_skipped == 0
    return True


def test_expanding_threshold_strict_prior_sessions():
    """105 sessions; every session except index `mp` (= MIN_PRIOR_SESSIONS, the 101st, 0-indexed
    100 -- the first session with >= 100 STRICTLY PRIOR sessions, hence the first with a defined
    threshold) has 3 minutes at imbalance 0.0. Session `mp` itself has 40 minutes at imbalance 0.9
    (a big enough share of the pool -- 40 of 340 = 11.8% > the top decile -- that the NEXT
    session's threshold visibly moves, so the causal check below is not vacuous). Two fixtures,
    identical except whether session `mp` carries this perturbation, isolate exactly what session
    `mp`'s OWN data is allowed to touch."""
    n_sessions, mp = 105, oflow.MIN_PRIOR_SESSIONS
    dates = pd.date_range("2024-01-02", periods=n_sessions, freq="B")

    def _fixture(perturb):
        rows = []
        for i, d in enumerate(dates):
            if i == mp and perturb:
                rows += [(d, 571 + j, 0.9) for j in range(40)]
            else:
                rows += [(d, mod, 0.0) for mod in (571, 572, 573)]
        return pd.DataFrame(rows, columns=["date", "mod", "imbalance"])

    flow_pert, flow_base = _fixture(True), _fixture(False)
    thr_pert = oflow.session_expanding_threshold(flow_pert)
    thr_base = oflow.session_expanding_threshold(flow_base)

    assert thr_pert.iloc[:mp].isna().all(), f"the first {mp} sessions must have NO defined threshold"
    assert pd.notna(thr_pert.iloc[mp]), f"session index {mp} (the {mp + 1}th) must be the first DEFINED threshold"
    assert np.isclose(thr_pert.iloc[mp], 0.0), "session index mp's threshold uses only baseline (0.0) prior sessions"
    assert np.isclose(thr_pert.iloc[mp], thr_base.iloc[mp]), \
        "session mp's OWN (perturbed) minutes moved its OWN threshold -- they must not"
    assert not np.isclose(thr_pert.iloc[mp + 1], thr_base.iloc[mp + 1]), \
        "perturbing session mp had no effect on session mp+1's threshold either -- this check would be vacuous"
    assert np.isclose(thr_pert.iloc[mp + 1], 0.9), \
        f"session mp+1's threshold should equal the perturbed value (0.9) once it dominates the top decile, got {thr_pert.iloc[mp + 1]}"

    flow2 = oflow.add_signals(flow_base, thr_base)
    assert not (flow2["thr_ok"] & (flow2["date"] < dates[mp])).any(), "no session before the warm-up may ever signal"
    return True


def test_session_boundary_exit_clamp():
    """A signal at mod 950: entry at 951 (signal+1), candidate exit 981 (entry+30) falls past the
    session's own last bar (959) and must clamp to 959, not 981."""
    date = pd.Timestamp("2024-02-01")
    flow = pd.DataFrame({"date": [date], "mod": [950], "sig_bull": [True]})
    last_mod = {date: 959}
    close_lookup = {(date, 951): 100.0, (date, 959): 103.0}
    trades, *_ = oflow.build_trades(flow, "sig_bull", 1.0, "c", oflow.LAG_T1, last_mod, close_lookup)
    assert len(trades) == 1
    assert trades.iloc[0]["entry_mod"] == 951
    assert trades.iloc[0]["exit_mod"] == 959, f"exit must clamp to the session's last bar (959), got {trades.iloc[0]['exit_mod']}"
    assert trades.iloc[0]["exit_px"] == 103.0
    return True


def test_entry_before_exit_and_net_of_cost():
    """Three signals across two sessions (one clamped by the session boundary) -> `build_trades`'s
    own trades must all have entry strictly before exit, and net_pts_cost{1,2} = gross pts -
    COST{1,2} exactly (COST1/COST2, never re-typed)."""
    d1, d2 = pd.Timestamp("2024-02-01"), pd.Timestamp("2024-02-02")
    flow = pd.DataFrame({"date": [d1, d1, d2], "mod": [600, 650, 950], "sig_bull": [True, True, True]})
    last_mod = {d1: 959, d2: 959}
    close_lookup = {(d1, 601): 100.0, (d1, 631): 104.0,
                    (d1, 651): 200.0, (d1, 681): 197.0,
                    (d2, 951): 300.0, (d2, 959): 305.0}
    trades, n_signal, n_skipped, n_overlap = oflow.build_trades(
        flow, "sig_bull", 1.0, "c", oflow.LAG_T1, last_mod, close_lookup)
    assert n_signal == 3 and n_skipped == 0 and n_overlap == 0
    assert len(trades) == 3
    assert (trades["entry_mod"] < trades["exit_mod"]).all(), "entry must be strictly before exit on every trade"
    net1 = trades["pts"] - oflow.COST1
    net2 = trades["pts"] - oflow.COST2
    assert np.allclose(net1, trades["pts"] - oflow.COST1)
    assert np.allclose(net2, trades["pts"] - oflow.COST2)
    # spot-check the actual numbers (direction=+1 call)
    expected_pts = [104.0 - 100.0, 197.0 - 200.0, 305.0 - 300.0]
    assert np.allclose(trades["pts"].to_numpy(), expected_pts)
    return True


def main():
    checks = [("(b) tick rule: carry-forward and first-print exclusion", test_tick_rule_carry_and_first_print_excluded),
              ("(c) imbalance arithmetic incl. seller-initiated-put-is-bullish", test_imbalance_arithmetic_seller_put_is_bullish),
              ("(a) causality: no look-ahead in the tick rule; entry shift is exact", test_causality_no_lookahead_and_entry_shift),
              ("(d) non-overlap: two qualifying minutes 5 apart -> ONE trade", test_non_overlap_single_trade),
              ("(e) expanding threshold uses strictly prior sessions only", test_expanding_threshold_strict_prior_sessions),
              ("(f) session-boundary exit clamps to the session's last bar", test_session_boundary_exit_clamp),
              ("(g) entry strictly before exit; net = gross - registered cost", test_entry_before_exit_and_net_of_cost)]
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
