"""Tests for pipeline.units.costs_reread (A51 M4: the 19 published HOLDOUT series re-read at the measured cost), runnable as

    python3 -m pytest pipeline/units/test_costs_reread.py -q -p no:cacheprovider
    python3 -m pipeline.units.test_costs_reread          # the same checks; exits non-zero on any failure

Plain asserts, no fixtures; nothing is written under out/ or data/. The module is exercised through its real functions on the
committed out/ files, and the expected numbers are read from those files HERE, not through the module's own loader (no
published number is pinned as a literal, so a regeneration of out/ such as A52.3's does not break them). Checks:
  (a) exactly 19 rows, the enumerated family/trial names, sorted by family then trial, columns == COLS, header-only output usable;
  (b) reread(1.0, 1.0) reproduces every published n, net, one-sided day-block p and DSR/PSR to the published 6 dp (the built-in
      self-check), and the gross series is published net + 1.0 (D1/D2 `pts` is gross, fvg `pts` is gross, the other three carry
      net_pts_cost1);
  (c) a uniform cost cut by d raises every net_at_cm by exactly d and leaves the published excess (condition 4) and n (condition 6)
      untouched;
  (d) gapliq and flatten never qualify at cm in {0, 0.5, 1.0}; their n are the published ones; and WHY (A51's two reasons: n < 200,
      or a negative published excess; flatten U2 has n = 299 so only the second stops it). An injected edge, which makes conditions
      1, 2, 3 and 5 pass everywhere, leaves exactly conditions 4 and 6 deciding the label;
  (e) BH-FDR is joint across the 19 rows: on the real p-values at cm = 0.6, where per-family flags differ, and on synthetic
      fixtures that pin alpha = 10%, the step-up and the one-test-per-row property;
  (f) at cm = 0 (and 0.5, 0.6, 1.0) the label logic matches the six conditions row by row; no market outcome is asserted, the
      qualifying rows, if any, are printed.
Also: an independent recomputation at an arbitrary cm (net, p, DSR with the shifted sibling pool, intraday columns), the boundary of
every condition, a NaN p never passing, `reproduces_published` flipping on a wrong published value, the DSR N's against the
units' own constants, a non-finite cm refused, and the enumeration guard.
"""
import io
import sys
from dataclasses import replace
from unittest import mock

import numpy as np
import pandas as pd

from pipeline import stats
from pipeline.units import costs_reread as cr

OUT = cr.ROOT / "out"
EXPECTED = [("flatten", "U1"), ("flatten", "U2"), ("flatten", "U3"),
            ("fvg", "long|R1|bos_off"), ("fvg", "long|R1|bos_on"), ("fvg", "long|R2|bos_off"), ("fvg", "long|R2|bos_on"),
            ("fvg", "short|R1|bos_off"), ("fvg", "short|R1|bos_on"), ("fvg", "short|R2|bos_off"), ("fvg", "short|R2|bos_on"),
            ("gapliq", "T1"), ("gapliq", "T2"), ("gapliq", "T3"),
            ("gapup", "13:00|call|gap>0.3%"), ("momentum", "15:00|both|vixmove_exp"),
            ("oflow", "T1"), ("oflow", "T2"), ("oflow", "T3")]
DSR_N = {"fvg": 33, "gapliq": 37, "flatten": 45, "oflow": 48, "momentum": 1, "gapup": 1}
INTRADAY = ("fvg", "oflow")
# (cm, cm_intraday) pairs used by several tests, so each is computed once per process (~9 s each)
CM_BASE, CM_ZERO, CM_HALF, CM_CUT, CM_ODD = (1.0, 1.0), (0.0, 0.0), (0.5, 0.5), (0.6, 0.7), (0.37, 0.81)

_CACHE, _SERIES = {}, []


def _reread(pair):
    if pair not in _CACHE:
        _CACHE[pair] = cr.reread(*pair)
    return _CACHE[pair].copy()


def _series():
    if not _SERIES:
        _SERIES.extend(cr.load_series())
    return list(_SERIES)


def _published():
    """{(family, trial): published n, net (pts), p_day, dsr, excess}, read straight from the committed files."""
    hs = pd.read_csv(OUT / "holdout_summary.csv").set_index("signal")
    pub = {}
    for fam, trial in (("momentum", "15:00|both|vixmove_exp"), ("gapup", "13:00|call|gap>0.3%")):
        r = hs.loc[trial]
        pub[(fam, trial)] = dict(n=int(r["n"]), net=r["net_pts"], p=r["p_day"], dsr=r["psr"], excess=r["excess_over_control_pct"])
    for fam in ("fvg", "gapliq", "flatten", "oflow"):
        c = pd.read_csv(OUT / f"{fam}_candidates.csv")
        for _, r in c[c["window"] == "HOLDOUT"].iterrows():
            pub[(fam, r["trial"])] = dict(n=int(r["n"]), net=r["net_pts_cost1"], p=r["p_boot_day"], dsr=r[f"dsr_N{DSR_N[fam]}"],
                                          excess=r["net_pts_cost1"] - r["control_mean_pts_cost1"])
    return pub


def _raw():
    """{(family, trial): (dates, gross pts, entry_px)} read straight from the per-trade files (A51 M4's enumeration)."""
    raw = {}
    for fam, trial, f in (("momentum", "15:00|both|vixmove_exp", "holdout_d4_1500_both_vixmove_exp_s1_cash_k1.0.csv"),
                          ("gapup", "13:00|call|gap>0.3%", "holdout_d4_1300_call_gapgt0.3pct_s1_cash_k1.0.csv")):
        t = pd.read_csv(OUT / f)
        raw[(fam, trial)] = (t["date"].to_numpy(), t["pts"].to_numpy(float), t["entry_px"].to_numpy(float))
    for fam in ("fvg", "gapliq", "flatten", "oflow"):
        t = pd.read_csv(OUT / f"{fam}_candidates_trades.csv")
        t = t[t["window"] == "HOLDOUT"]
        for trial in t["trial"].unique():
            g = t[t["trial"] == trial]
            if fam == "fvg":
                g = g[g["filled"]]
            gross = g["pts"] if fam == "fvg" else g["net_pts_cost1"] + 1.0
            raw[(fam, trial)] = (g["date"].to_numpy(), gross.to_numpy(float), g["entry_px"].to_numpy(float))
    return raw


def _fails(row):
    return [int(k) for k in row.cond_failed.split(",")] if row.cond_failed else []


def _assert_label_logic(df):
    """cond_failed / label recomputed from the row's own columns and an independent BH over its 19 p-values."""
    p = df["p_day_at_cm"].to_numpy(float)
    fdr = stats.bh_fdr(np.where(np.isnan(p), 1.0, p), alpha=0.10)
    assert list(df["fdr_pass_at_cm"]) == list(fdr), "fdr_pass_at_cm is not BH at 10% over the 19 p_day_at_cm values"
    for r, f in zip(df.itertuples(), fdr):
        want = []
        if not r.net_at_cm > 0:
            want.append(1)
        if not r.p_day_at_cm < 0.05:
            want.append(2)
        if not f:
            want.append(3)
        if not r.published_excess_over_control > 0:
            want.append(4)
        if not r.dsr_at_cm > 0.95:
            want.append(5)
        if not r.n >= 200:
            want.append(6)
        assert _fails(r) == want, f"{r.family} {r.trial}: cond_failed {r.cond_failed!r}, six conditions say {want}"
        assert (r.label == cr.LABEL_YES) == (not want), f"{r.family} {r.trial}: label {r.label!r} vs failing {want}"
        assert r.label in (cr.LABEL_YES, cr.LABEL_NO)


# ---------------------------------------------------------------- (a)
def test_a_nineteen_rows_expected_names_sorted_columns_header_only():
    df = _reread(CM_BASE)
    assert len(df) == 19 == cr.N_SERIES
    assert list(df.columns) == cr.COLS
    assert list(zip(df["family"], df["trial"])) == EXPECTED
    assert EXPECTED == sorted(EXPECTED), "EXPECTED must itself be in family-then-trial order"
    assert (df["window"] == "HOLDOUT").all()
    assert df.groupby("family").size().to_dict() == {"flatten": 3, "fvg": 8, "gapliq": 3, "gapup": 1, "momentum": 1, "oflow": 3}
    assert dict(zip(df["family"], df["dsr_N"])) == DSR_N
    src = dict(zip(df["family"], df["source_file"]))
    assert src["fvg"] == "out/fvg_candidates_trades.csv" and src["gapliq"] == "out/gapliq_candidates_trades.csv"
    assert src["flatten"] == "out/flatten_candidates_trades.csv" and src["oflow"] == "out/oflow_candidates_trades.csv"
    assert src["momentum"] == "out/holdout_d4_1500_both_vixmove_exp_s1_cash_k1.0.csv"
    assert src["gapup"] == "out/holdout_d4_1300_call_gapgt0.3pct_s1_cash_k1.0.csv"
    assert len(cr.COLS) == len(set(cr.COLS)) == 25
    assert cr.LABEL_YES == "QUALIFIES FOR A FORWARD TEST"       # A51 M4's literal label
    assert set(df["label"]) <= {cr.LABEL_YES, cr.LABEL_NO} and cr.LABEL_NO != cr.LABEL_YES
    buf = io.StringIO()
    pd.DataFrame(columns=cr.COLS).to_csv(buf, index=False, float_format="%.6f")
    assert buf.getvalue().strip() == ",".join(cr.COLS)
    assert len(pd.read_csv(io.StringIO(buf.getvalue()))) == 0


# ---------------------------------------------------------------- (b)
def test_b_reread_at_published_cost_reproduces_published_n_net_p_dsr():
    df, pub = _reread(CM_BASE), _published()
    assert df["reproduces_published"].all(), df.loc[~df["reproduces_published"], ["family", "trial", "note"]].to_string()
    for r in df.itertuples():
        p = pub[(r.family, r.trial)]
        assert r.n == p["n"], f"{r.family} {r.trial}: n {r.n} != published {p['n']}"
        for name, got, want in (("net", r.reread_net_at_1pt, p["net"]), ("p_day", r.reread_p_day_at_1pt, p["p"]),
                                ("dsr", r.reread_dsr_at_1pt, p["dsr"])):
            # the published values carry six decimals and the per-trade inputs are rounded to six too, so "to 6 dp" means within
            # one unit of the last published digit (observed: every residual <= 5e-7, i.e. the published value's own rounding)
            assert abs(got - want) <= 1e-6, f"{r.family} {r.trial}: {name} {got} != published {want}"
        # the published columns ARE the files' values (not something the module made up)
        assert r.published_net_1pt == p["net"] and r.published_p_day == p["p"] and r.published_dsr == p["dsr"]
        assert np.isclose(r.published_excess_over_control, p["excess"], rtol=0, atol=1e-12)
    # at cm = 1.0 the at-cm path and the 1-pt self-check path are the same numbers
    assert np.array_equal(df["net_at_cm"], df["reread_net_at_1pt"])
    assert np.array_equal(df["p_day_at_cm"], df["reread_p_day_at_1pt"])
    assert np.array_equal(df["dsr_at_cm"], df["reread_dsr_at_1pt"])
    # some published p's are below 1.0 (real bootstrap p-values), so the p reproduction is not vacuous
    assert (df["published_p_day"] < 1).any() and ((df["published_p_day"] < 1) == (df["reread_p_day_at_1pt"] < 1)).all()
    calls = []

    def fake(cm, cm_intraday=None):
        calls.append((cm, cm_intraday))
        return df

    with mock.patch.object(cr, "reread", fake):
        assert cr.self_check() is df
    assert calls == [(1.0, 1.0)], "self_check must re-read at the published 1.0-pt cost"


def test_b_gross_is_published_net_plus_one_and_pts_is_gross():
    pub, raw = _published(), _raw()
    assert len(raw) == 19
    for s in _series():
        want = pub[(s.family, s.trial)]["net"]
        assert abs(s.gross.mean() - 1.0 - want) <= 1e-6, f"{s.family} {s.trial}: mean(gross) - 1.0 != published net {want}"
        d, g, e = raw[(s.family, s.trial)]
        assert np.array_equal(s.gross, g) and np.array_equal(s.entry_px, e) and list(s.dates) == list(d)
    # D1/D2: `pts` is gross, so mean(pts) - 1.0 is the published holdout net_pts (insample.py:59), to six decimals
    for key in (("momentum", "15:00|both|vixmove_exp"), ("gapup", "13:00|call|gap>0.3%")):
        g = raw[key][1]
        assert len(g) == pub[key]["n"] and abs(g.mean() - 1.0 - pub[key]["net"]) <= 1e-6, key


def test_b_net_pct_is_the_units_own_series_ret_pct_minus_cost_over_entry():
    """Where a per-trade file also carries ret_pct (D1/D2, fvg) the module's net % must be the unit's formula
    ret_pct - 100*cost/entry_px; that is what justifies rebuilding it as 100*net pts/entry_px for gapliq/flatten/oflow."""
    by = {(s.family, s.trial): s for s in _series()}
    for fam, trial, f in (("momentum", "15:00|both|vixmove_exp", "holdout_d4_1500_both_vixmove_exp_s1_cash_k1.0.csv"),
                          ("gapup", "13:00|call|gap>0.3%", "holdout_d4_1300_call_gapgt0.3pct_s1_cash_k1.0.csv")):
        t = pd.read_csv(OUT / f)
        for cost in (1.0, 0.4):
            assert np.abs(cr.net_pct(by[(fam, trial)], cost) - (t["ret_pct"] - 100 * cost / t["entry_px"])).max() < 1e-6
    t = pd.read_csv(OUT / "fvg_candidates_trades.csv")
    t = t[(t["window"] == "HOLDOUT") & t["filled"]]
    for trial in ("short|R1|bos_off", "long|R2|bos_on"):
        g = t[t["trial"] == trial]
        for cost in (1.0, 0.4):
            assert np.abs(cr.net_pct(by[("fvg", trial)], cost) - (g["ret_pct"] - 100 * cost / g["entry_px"])).max() < 1e-6


# ---------------------------------------------------------------- (c)
def test_c_uniform_cost_cut_raises_net_by_exactly_d_and_leaves_conditions_4_and_6_inputs_alone():
    a, b = _reread(CM_BASE), _reread(CM_CUT)
    assert (a["cm"] == 1.0).all() and (b["cm"] == 0.6).all()
    assert np.allclose((b["net_at_cm"] - a["net_at_cm"]).to_numpy(), 1.0 - 0.6, rtol=0, atol=1e-9)
    intra = a["family"].isin(INTRADAY).to_numpy()
    assert np.allclose((b["net_at_cm_intraday"] - a["net_at_cm_intraday"]).to_numpy()[intra], 1.0 - 0.7, rtol=0, atol=1e-9)
    assert np.array_equal(a["published_excess_over_control"].to_numpy(), b["published_excess_over_control"].to_numpy()), \
        "the published excess over the control must not move with the cost"
    for col in ("n", "dsr_N", "published_net_1pt", "reread_net_at_1pt", "published_p_day", "reread_p_day_at_1pt",
                "published_dsr", "reread_dsr_at_1pt", "reproduces_published"):
        assert np.array_equal(a[col].to_numpy(), b[col].to_numpy(), equal_nan=a[col].dtype.kind == "f"), col
    for ra, rb in zip(a.itertuples(), b.itertuples()):
        assert (4 in _fails(ra)) == (4 in _fails(rb)), f"{ra.family} {ra.trial}: condition 4 moved with the cost"
        assert (6 in _fails(ra)) == (6 in _fails(rb)), f"{ra.family} {ra.trial}: condition 6 moved with the cost"


# ---------------------------------------------------------------- (d)
def test_d_gapliq_and_flatten_never_qualify_and_their_n_are_the_published_ones():
    """A51 R4: gapliq and flatten cannot qualify at any Cm. Its reasons: n < 200 (condition 6) and a negative published excess
    (condition 4); both are checked per row. On the committed files flatten U2 has n = 299, so only its negative excess stops it."""
    pub = _published()
    for pair in (CM_ZERO, CM_HALF, CM_BASE):
        df = _reread(pair)
        sub = df[df["family"].isin(["gapliq", "flatten"])]
        assert len(sub) == 6
        for r in sub.itertuples():
            assert r.n == pub[(r.family, r.trial)]["n"], f"{r.family} {r.trial}: n is not the published n"
            assert r.label != cr.LABEL_YES, f"{r.family} {r.trial} qualifies at cm={r.cm}"
            if r.n < 200:
                assert 6 in _fails(r), f"{r.family} {r.trial}: n {r.n} < 200 but condition 6 not listed"
            else:
                assert r.published_excess_over_control <= 0 and 4 in _fails(r), \
                    f"{r.family} {r.trial}: n {r.n} >= 200 and not blocked by a negative published excess"
                if pair == CM_BASE:
                    print(f"[info] {r.family} {r.trial}: n = {r.n} >= 200, blocked by condition 4 "
                          f"(published excess {r.published_excess_over_control:.6f}), not by condition 6")


def test_d_injected_edge_leaves_exactly_conditions_4_and_6_deciding_the_label():
    """Every series shifted to a net of +2 per-trade SDs at cm: conditions 1, 2, 3, 5 pass for all 19 rows, so the label is
    decided by the published excess (4) and n (6) alone. Catches a dropped or mis-wired condition 4 or 6, and shows the rule
    is not vacuous (rows qualify when the edge is there)."""
    edge = []
    for s in _series():
        edge.append(replace(s, gross=s.gross + (1.0 + 2.0 * s.gross.std(ddof=1) - s.gross.mean())))
    df = cr.score_trials(edge, 1.0, 1.0)
    qualifying = []
    for r in df.itertuples():
        assert not set(_fails(r)) & {1, 2, 3, 5}, f"{r.family} {r.trial}: injected edge did not clear {_fails(r)}"
        want = ([4] if not r.published_excess_over_control > 0 else []) + ([6] if r.n < 200 else [])
        assert _fails(r) == want, f"{r.family} {r.trial}: {_fails(r)} != {want}"
        assert (r.label == cr.LABEL_YES) == (not want)
        if not want:
            qualifying.append((r.family, r.trial))
    pub = _published()
    assert qualifying == [k for k in sorted(pub) if pub[k]["excess"] > 0 and pub[k]["n"] >= 200], \
        "exactly the rows with a positive published excess and n >= 200 qualify under an injected edge"
    assert qualifying, "no row qualifies under an injected edge: the rule would be vacuous"


# ---------------------------------------------------------------- (e)
def _synthetic(means, cost=0.0, n_days=220):
    """19 synthetic series with the real family structure (8 + 3 + 3 + 3 + 1 + 1), one trade a day, n = 220 >= 200, the same
    standardised unit-SD noise in each, series i netting exactly means[i] points per trade at `cost`. A published excess of +1.0
    (condition 4 passes); the other published values are NaN (nothing to reproduce)."""
    z = np.random.default_rng(5).normal(size=n_days)
    z = (z - z.mean()) / z.std(ddof=1)
    dates = pd.bdate_range("2021-01-04", periods=n_days).strftime("%Y-%m-%d").to_numpy()
    out, k = [], 0
    for fam, size, dsr_n, intraday in (("fvg", 8, 33, True), ("gapliq", 3, 37, False), ("flatten", 3, 45, False),
                                       ("oflow", 3, 48, True), ("momentum", 1, 1, False), ("gapup", 1, 1, False)):
        for j in range(size):
            out.append(cr.TradeSeries(family=fam, trial=f"S{j}", source_file="synthetic", dates=dates, gross=z + means[k] + cost,
                                      entry_px=np.full(n_days, 5000.0), dsr_n=dsr_n, intraday=intraday, pub_n=n_days,
                                      pub_net=np.nan, pub_p_day=np.nan, pub_dsr=np.nan, pub_excess=1.0, note="synthetic"))
            k += 1
    return out


def _mean_with_p(lo, hi):
    """A net mean whose one-sided day-block p (the real stats.one_sided_p, seed 11) lies in [lo, hi]. The noise is the same in every
    synthetic series and the centred bootstrap means do not move with the mean, so p is non-increasing in it: bisect."""
    s = _synthetic([0.0] * 19)[0]
    a, b = 0.0, 1.0
    for _ in range(60):
        mu = (a + b) / 2
        p = cr.p_day(replace(s, gross=s.gross + mu), 0.0)
        if p > hi:
            a = mu
        elif p < lo:
            b = mu
        else:
            return mu
    raise AssertionError(f"no synthetic net mean realises p in [{lo}, {hi}]")


def test_e_bh_fdr_is_joint_across_the_19_rows_on_the_real_p_values():
    """The module's flags are BH at 10% over all 19 real p-values. On the files committed with A51, at cm = 0.6 fvg short|R1|bos_off
    has the smallest p and BH over its own 8 rows would pass it while BH over all 19 does not, so this also tells the two apart."""
    df = _reread(CM_CUT)
    p = np.where(np.isnan(df["p_day_at_cm"].to_numpy(float)), 1.0, df["p_day_at_cm"].to_numpy(float))
    joint = stats.bh_fdr(p, alpha=0.10)
    per_family = np.zeros(len(df), bool)
    for fam in df["family"].unique():
        idx = np.flatnonzero((df["family"] == fam).to_numpy())
        per_family[idx] = stats.bh_fdr(p[idx], alpha=0.10)
    assert list(df["fdr_pass_at_cm"]) == list(joint)
    if (joint != per_family).any():
        assert list(df["fdr_pass_at_cm"]) != list(per_family)
    else:   # the synthetic test below is the one that pins the joint-vs-per-family property
        print("[info] cm = 0.6: joint and per-family BH agree on the committed p-values")
    _assert_label_logic(df)


def test_e_bh_fdr_synthetic_alpha_stepup_and_not_per_family():
    mu_pass = _mean_with_p(0.0028, 0.0050)     # below 10%/19 = 0.00526: passes BH over 19 rows
    mu_mid = _mean_with_p(0.0060, 0.0100)      # between 10%/19 and 2 x 10%/19 = 0.01053: alone it fails over 19 rows
    mu_edge = _mean_with_p(0.0054, 0.0070)     # between 10%/19 and 10%/14 = 0.00714: fails over 19 rows, would pass over 14
    last, prev = 18, 17                        # the one-row families gapup and momentum: per-family BH would give each alpha = 10%
    for what, targets, mu, want, thin in (
            ("p just under alpha/19 passes (alpha is 10%, not 5%)", [last], mu_pass, True, False),
            ("p between alpha/19 and 2 alpha/19 alone fails (joint over 19, not per family; alpha not 20%)", [last], mu_mid, False, False),
            ("two such p's pass together (BH step-up, not Bonferroni or rank-by-rank)", [last, prev], mu_mid, True, False),
            ("rows with n < 200 or a negative published excess still count in m = 19 (not 14)", [last], mu_edge, False, True)):
        means = [-1.0] * 19                    # net < 0 -> one-sided p is exactly 1.0, never passes
        for t in targets:
            means[t] = mu
        series = _synthetic(means)
        if thin:   # five rows too short to qualify (rows 0-4), five that can never beat their control (rows 5-9): 19 - 5 = 14
            for i in range(5):
                s = series[i]
                series[i] = replace(s, dates=s.dates[:150], gross=s.gross[:150], entry_px=s.entry_px[:150])
            for i in range(5, 10):
                series[i] = replace(series[i], pub_excess=-1.0)
        df = cr.score_trials(series, 0.0)
        assert (df["p_day_at_cm"] == 1.0).sum() == 19 - len(targets), what
        for t in targets:
            row = df[df["family"] == series[t].family].iloc[0]
            assert bool(row["fdr_pass_at_cm"]) is want, f"{what}: p = {row['p_day_at_cm']:.5f}, fdr_pass {row['fdr_pass_at_cm']}"
            # n = 220, excess +1.0, PSR on a ~0.17 SD mean over 220 trades > 0.95, p < 0.05: only condition 3 can fail, and
            # the label is QUALIFIES exactly when it passes (a real synthetic QUALIFIES: the rule is not vacuous)
            assert row["cond_failed"] == ("" if want else "3"), f"{what}: cond_failed {row['cond_failed']!r}"
            assert row["label"] == (cr.LABEL_YES if want else cr.LABEL_NO), what
            assert row["dsr_at_cm"] > 0.95 and row["net_at_cm"] > 0 and row["n"] == 220, what
        assert int(df["fdr_pass_at_cm"].sum()) == (len(targets) if want else 0), what


def test_e_nan_p_never_passes_condition_2_or_3():
    """Under 20 day blocks stats.one_sided_p is NaN: a NaN fails condition 2, and enters BH as 1.0 (never as 0)."""
    series = _synthetic([-1.0] * 18 + [0.5])
    s = series[18]
    series[18] = replace(s, dates=s.dates[:15], gross=s.gross[:15], entry_px=s.entry_px[:15])
    row = cr.score_trials(series, 0.0).set_index("family").loc["gapup"]
    assert np.isnan(row["p_day_at_cm"]) and row["net_at_cm"] > 0
    assert not row["fdr_pass_at_cm"] and row["label"] == cr.LABEL_NO
    assert set(row["cond_failed"].split(",")) >= {"2", "3"}, row["cond_failed"]


# ---------------------------------------------------------------- (f)
def test_f_label_logic_matches_the_six_conditions_row_by_row():
    """Consistency only; no market outcome is asserted. cm = 0 is the case the issue names; 0.5, 0.6 and 1.0 ride along."""
    for pair in (CM_ZERO, CM_HALF, CM_CUT, CM_BASE):
        _assert_label_logic(_reread(pair))
    df = _reread(CM_ZERO)
    q = df[df["label"] == cr.LABEL_YES]
    print(f"[info] cm = 0.0: {len(q)} of 19 rows carry the QUALIFIES label"
          + (": " + ", ".join(f"{f} {t}" for f, t in zip(q["family"], q["trial"])) if len(q) else ""))
    print("[info] cm = 0.0 failing conditions: "
          + "; ".join(f"{f} {t}: {c or '-'}" for f, t, c in zip(df["family"], df["trial"], df["cond_failed"])))


def test_f_every_condition_boundary():
    ok = dict(net=0.01, p=0.049, fdr_pass=True, excess=0.01, dsr=0.951, n=200)
    assert cr.failing_conditions(**ok) == []
    assert cr.failing_conditions(**{**ok, "net": 0.0}) == [1]                 # net > 0, strictly
    assert cr.failing_conditions(**{**ok, "net": -0.01}) == [1]
    assert cr.failing_conditions(**{**ok, "p": 0.05}) == [2]                  # p < 0.05, strictly
    assert cr.failing_conditions(**{**ok, "p": 0.0}) == []
    assert cr.failing_conditions(**{**ok, "fdr_pass": False}) == [3]
    assert cr.failing_conditions(**{**ok, "excess": 0.0}) == [4]              # excess > 0, strictly
    assert cr.failing_conditions(**{**ok, "excess": -0.01}) == [4]
    assert cr.failing_conditions(**{**ok, "dsr": 0.95}) == [5]                # DSR > 0.95, strictly
    assert cr.failing_conditions(**{**ok, "n": 199}) == [6]                   # n >= 200
    assert cr.failing_conditions(**{**ok, "n": 200}) == []
    for k, v in (("net", np.nan), ("p", np.nan), ("excess", np.nan), ("dsr", np.nan)):   # a NaN never passes
        assert cr.failing_conditions(**{**ok, k: v}) == [{"net": 1, "p": 2, "excess": 4, "dsr": 5}[k]]
    assert cr.failing_conditions(net=-1, p=1.0, fdr_pass=False, excess=-1, dsr=0.0, n=1) == [1, 2, 3, 4, 5, 6]
    assert cr.failing_conditions(net=-1, p=1.0, fdr_pass=np.False_, excess=1, dsr=0.0, n=500) == [1, 2, 3, 5]


# ---------------------------------------------------------------- independent recomputation, intraday, flags, guards
def test_independent_recomputation_at_an_arbitrary_cost():
    """Net, one-sided day-block p, DSR (SR0's pool = the siblings' net-% Sharpe at the SAME shifted cost, N = the family's own),
    and the intraday columns, recomputed here straight from the per-trade files at cm = 0.37 / cm_intraday = 0.81."""
    cm, ci = CM_ODD
    df = _reread(CM_ODD).set_index(["family", "trial"])
    raw = _raw()
    pct = {k: 100.0 * (g - cm) / e for k, (_, g, e) in raw.items()}
    for fam in DSR_N:
        keys = [k for k in raw if k[0] == fam]
        pool = [stats.per_trade_sharpe(pct[k]) for k in keys]
        for k in keys:
            d, g, e = raw[k]
            row = df.loc[k]
            assert np.isclose(row["net_at_cm"], (g - cm).mean(), rtol=0, atol=1e-9)
            assert row["p_day_at_cm"] == stats.one_sided_p(pct[k], stats.day_blocks(d))
            want = stats.deflated_sharpe(pct[k], sr_trials=pool, n=DSR_N[fam])[0]
            assert np.isclose(row["dsr_at_cm"], want, rtol=1e-9, atol=0), f"{k}: dsr {row['dsr_at_cm']} != {want}"
            if fam in INTRADAY:
                assert row["cm_intraday"] == ci
                assert np.isclose(row["net_at_cm_intraday"], (g - ci).mean(), rtol=0, atol=1e-9)
                assert row["p_day_at_cm_intraday"] == stats.one_sided_p(100.0 * (g - ci) / e, stats.day_blocks(d))
            else:
                assert np.isnan(row[["cm_intraday", "net_at_cm_intraday", "p_day_at_cm_intraday"]].to_numpy(float)).all()
    _assert_label_logic(_reread(CM_ODD))


def test_intraday_columns_are_blank_without_cm_intraday_and_for_other_families():
    sub = [s for s in _series() if s.family == "gapliq"] + [s for s in _series() if s.family == "oflow"]
    none = cr.score_trials(sub, 0.5, None)
    nan = cr.score_trials(sub, 0.5, float("nan"))
    for df in (none, nan):
        assert df[["cm_intraday", "net_at_cm_intraday", "p_day_at_cm_intraday"]].isna().all().all()
    both = cr.score_trials(sub, 0.5, 0.9)
    gl, of = both[both["family"] == "gapliq"], both[both["family"] == "oflow"]
    assert gl[["cm_intraday", "net_at_cm_intraday", "p_day_at_cm_intraday"]].isna().all().all()
    assert (of["cm_intraday"] == 0.9).all() and of["net_at_cm_intraday"].notna().all() and of["p_day_at_cm_intraday"].notna().all()
    assert (of["cm"] == 0.5).all() and np.allclose(of["net_at_cm_intraday"] - of["net_at_cm"], 0.5 - 0.9, atol=1e-9)


def test_reproduces_published_flips_on_a_wrong_published_value_and_ignores_unpublished():
    gl = [s for s in _series() if s.family == "gapliq"]
    base = cr.score_trials(gl, 1.0, 1.0)
    assert base["reproduces_published"].all()
    i = 0
    for field, bad, tag in (("pub_n", gl[i].pub_n + 1, "n"), ("pub_net", gl[i].pub_net + 1e-4, "net"),
                            ("pub_p_day", gl[i].pub_p_day + 1e-3, "p"), ("pub_dsr", gl[i].pub_dsr + 1e-4, "dsr")):
        df = cr.score_trials([replace(gl[i], **{field: bad})] + gl[1:], 1.0, 1.0).set_index("trial")
        assert not df.loc[gl[i].trial, "reproduces_published"], field
        assert df.loc[gl[i].trial, "note"].endswith(f"DOES NOT REPRODUCE PUBLISHED: {tag}"), df.loc[gl[i].trial, "note"]
        assert df.drop(index=gl[i].trial)["reproduces_published"].all(), "only the doctored row may flip"
    # 3e-7 stays inside the 1e-6 tolerance whatever the row's own rounding residual (|residual| <= ~5.5e-7), on any regeneration
    within = cr.score_trials([replace(gl[i], pub_net=gl[i].pub_net + 3e-7)] + gl[1:], 1.0, 1.0)
    assert within["reproduces_published"].all(), "an error inside the published precision is not a mismatch"
    unpublished = cr.score_trials([replace(gl[i], pub_p_day=np.nan, pub_dsr=np.nan)] + gl[1:], 1.0, 1.0)
    assert unpublished["reproduces_published"].all(), "NaN published = nothing to reproduce"
    broken = base.copy()
    broken.loc[0, "reproduces_published"] = False
    with mock.patch.object(cr, "reread", lambda cm, cm_intraday=None: broken):
        try:
            cr.self_check()
        except AssertionError as e:
            assert broken.loc[0, "trial"] in str(e)
        else:
            raise AssertionError("self_check passed a frame with a non-reproducing row")


def test_dsr_n_matches_the_units_own_constants():
    from pipeline.units import flatten, fvg, gapliq, oflow
    assert (fvg.DSR_N, gapliq.DSR_N, flatten.DSR_N, oflow.DSR_N) == (33, 37, 45, 48)
    assert {f: n for f, (_, _, n, _, _) in cr.FAMILIES.items()} == {"fvg": 33, "gapliq": 37, "flatten": 45, "oflow": 48}
    assert (fvg.COST1, gapliq.COST1, flatten.COST1, oflow.COST1) == (cr.BASE_COST,) * 4
    assert {s.family: s.dsr_n for s in _series()} == DSR_N
    assert {s.family: s.intraday for s in _series()} == {f: f in INTRADAY for f in DSR_N}


def test_cm_must_be_finite_and_the_enumeration_is_guarded():
    gl = [s for s in _series() if s.family == "gapliq"]
    for bad in (float("nan"), float("inf"), None):
        try:
            cr.score_trials(gl, bad, 0.5)
        except (ValueError, TypeError):
            pass
        else:
            raise AssertionError(f"cm={bad!r} accepted")
    try:
        cr.score_trials(gl, 0.5, float("inf"))
    except ValueError:
        pass
    else:
        raise AssertionError("cm_intraday=inf accepted")
    assert cr.score_trials([], 0.5, 0.5).columns.tolist() == cr.COLS
    with mock.patch.object(cr, "N_SERIES", 20):
        try:
            cr.load_series()
        except AssertionError:
            pass
        else:
            raise AssertionError("load_series did not assert the enumerated count")
    for trials in (("T1", "T2"), ("T1", "T2", "T3", "T4")):    # fewer / more trials than the HOLDOUT files hold
        wrong = dict(cr.FAMILIES)
        wrong["gapliq"] = wrong["gapliq"][:4] + (trials,)
        with mock.patch.object(cr, "FAMILIES", wrong):
            try:
                cr.load_series()
            except AssertionError:
                pass
            else:
                raise AssertionError(f"load_series accepted the enumerated trial set {trials}")


def main():
    checks = [(name, fn) for name, fn in list(globals().items()) if name.startswith("test_") and callable(fn)]
    ok = True
    for name, fn in checks:
        try:
            fn()
            print(f"[PASS] {name}")
        except Exception as e:  # noqa: BLE001 -- report every failing check, then exit non-zero
            ok = False
            print(f"[FAIL] {name}: {type(e).__name__}: {e}")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
