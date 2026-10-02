"""Tests for pipeline.units.costs (A51 + A51a, the real cost of the 0DTE instrument from quotes), runnable both ways:

    python3 -m pytest pipeline/units/test_costs.py -q -p no:cacheprovider
    python3 -m pipeline.units.test_costs

Plain asserts, every test returns None. Everything runs on SYNTHETIC data written to a temp dir (nothing under
data/raw or out/ is read or written; the M4 module is mocked, never imported by the measurement tests). The
fixtures are built independently of costs.py: instants are hard-coded ET minutes, ET->UTC goes through pandas' tz
database in this file, and every expected number below was derived by hand (the arithmetic is in the comments) or by
an independent computation here (pipeline.options' Black-Scholes, numpy's seeded generator), not by asking the
function under test. A previous suite in this repo passed while the code was wrong
(test_sizing / test_power review rounds), so the design rule here is: each assertion pins a number or a
behaviour that a plausible one-line bug would change; MUTATION_PROOF at the bottom lists the mutants this suite
was run against.

Required by the brief: (1) known spreads recovered exactly; (2) zero spread -> Cm == 0 and every M3 RT == 0;
(3) prevailing-quote rule; (4) A8 rounding; (5) DST; (6) V1 scale/swap and V2 timestamp shifts; (7) coverage
gate vs run_reread; (8) skip path and missing manifest; (9) M3 delta and TC; (10) M5 hand-built day. Added for
A51a: staleness limit as a function of rows_on_change, empty-book rows, manifest-excluded sessions.
"""
import contextlib
import io
import json
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile
import traceback
import types

import numpy as np
import pandas as pd

from pipeline import options
from pipeline.units import costs, sellvol

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
NY = "America/New_York"
# 09:32 10:01 11:01 13:01 13:31 15:01 15:31 15:55 16:00 ET as minutes of the day; hard-coded on purpose
INSTANT_MODS = [572, 601, 661, 781, 811, 901, 931, 955, 960]
ENTRY_MODS = [601, 661, 781, 901, 931]
_MISSING = object()
_UTC = {}


# ---------------------------------------------------------------------------------------------
# Fixture machinery
# ---------------------------------------------------------------------------------------------

def et_utc(date, mod):
    """ET wall-clock minute `mod` on `date` as a UTC Timestamp, by pandas' tz database (independent of costs.py)."""
    key = (date, int(mod))
    if key not in _UTC:
        _UTC[key] = pd.Timestamp(f"{date} {int(mod) // 60:02d}:{int(mod) % 60:02d}", tz=NY).tz_convert("UTC")
    return _UTC[key]


def ndays(date):
    return int(pd.Timestamp(date).value // (86400 * 10 ** 9))


def canon(rows):
    """(date, et_mod, right, strike, bid, ask) tuples -> the canonical quote frame costs.prepare_quotes returns."""
    return pd.DataFrame([dict(date_days=ndays(d), is_put=int(r == "P"), strike=float(k),
                              tsec=int(et_utc(d, m).value // 10 ** 9), mod=int(m), bid=b, ask=a)
                         for d, m, r, k, b, a in rows])


@contextlib.contextmanager
def patched(obj, name, value):
    old = getattr(obj, name)
    setattr(obj, name, value)
    try:
        yield
    finally:
        setattr(obj, name, old)


@contextlib.contextmanager
def fake_reread_module(reread):
    """Install a stand-in for pipeline.units.costs_reread (the real one may not exist yet)."""
    import pipeline.units as pkg
    name = "pipeline.units.costs_reread"
    mod = types.ModuleType(name)
    mod.reread = reread
    old_sys, old_attr = sys.modules.get(name, _MISSING), getattr(pkg, "costs_reread", _MISSING)
    sys.modules[name] = mod
    pkg.costs_reread = mod
    try:
        yield
    finally:
        for restore, key, old in ((sys.modules, name, old_sys), (pkg.__dict__, "costs_reread", old_attr)):
            if old is _MISSING:
                restore.pop(key, None)
            else:
                restore[key] = old


@contextlib.contextmanager
def tmpdir():
    d = tempfile.mkdtemp(prefix="costs_test_")
    try:
        yield d
    finally:
        shutil.rmtree(d, ignore_errors=True)


@contextlib.contextmanager
def quiet():
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        yield


def fake_reread_frame(calls):
    def fake(cm, cm_intraday):
        calls.append((cm, cm_intraday))
        return pd.DataFrame([{c: 0 for c in costs.REREAD_COLS}], columns=costs.REREAD_COLS)
    return fake


def make_frame(dates, S_fn):
    """Canonical minute frame (SPX points = 10 x SPY dollars) with the 390 RTH bars of every date."""
    parts = []
    mods = np.arange(570, 960)
    for date in dates:
        s = np.asarray(S_fn(date, mods), float) * 10.0
        ts = [pd.Timestamp(f"{date} {m // 60:02d}:{m % 60:02d}").tz_localize(NY) for m in mods]
        parts.append(pd.DataFrame({"ts_ny": ts, "date": pd.Timestamp(date), "mod": mods, "open": s, "high": s,
                                   "low": s, "close": s, "volume": 100.0, "feed": "ext"}))
    return pd.concat(parts, ignore_index=True)


def default_S(base_of):
    """SPY dollars of the bar starting at each `mod`: the day's base, +0.4 on the bar that ENDS at an instant (the
    bar the unit must read) and +1.6 on the bar that STARTS at it (the wrong bar), so a one-bar error moves S."""
    def S_fn(date, mods):
        mods = np.asarray(mods)
        return (np.full(mods.shape, float(base_of(date))) + 0.4 * np.isin(mods, [m - 1 for m in INSTANT_MODS])
                + 1.6 * np.isin(mods, INSTANT_MODS))
    return S_fn


def default_mid(S_fn):
    """Quote mid at ET minute `mods`: intrinsic at the bar ending there + a time value of 0.03..0.15 that changes
    every minute (so the V2 alignments differ) + a small extra near the money."""
    def mid(date, right, K, mods):
        mods = np.asarray(mods)
        S = S_fn(date, mods - 1)
        intrinsic = np.maximum(S - K, 0.0) if right == "C" else np.maximum(K - S, 0.0)
        return intrinsic + 0.03 * (1 + (mods * 13) % 5) + np.maximum(0.0, 0.6 - 0.1 * np.abs(K - S))
    return mid


def const_hs(h):
    return lambda date, right, K, mods: np.full(len(mods), float(h))


class World:
    """A synthetic ext directory: monthly quote shards, one trade shard, the manifest, and the matching frame."""

    def __init__(self, inp, frame, dates, base_of):
        self.inp, self.frame, self.dates, self.base_of = inp, frame, dates, base_of


def make_world(root, dates, base_of, hs_fn=None, mid_fn=None, drop_fn=None, manifest=None, trades=True,
               price_scale=None, no_quote_dates=()):
    """Write the world under `root`. Every strike within +-14 of the day's base, both rights; quotes at the nine
    instants for every strike, at EVERY minute 09:30-16:00 for the five strikes nearest the base (the trade-bar
    contracts V2 needs). `hs_fn(date, right, K, mods)` = half-spreads, `drop_fn(...)` = rows to omit,
    `price_scale` = {date: factor} multiplies that day's prices, `no_quote_dates` = days in the frame with no
    quote rows at all."""
    os.makedirs(root, exist_ok=True)
    S_fn = default_S(base_of)
    mid_fn = mid_fn or default_mid(S_fn)
    hs_fn = hs_fn or const_hs(0.03)
    scale = price_scale or {}
    qparts, tparts = [], []
    for date in dates:
        if date in no_quote_dates:
            continue
        s0 = base_of(date)
        near = set(np.arange(round(s0) - 2, round(s0) + 3))
        for right in ("C", "P"):
            for K in np.arange(np.floor(s0) - 14, np.ceil(s0) + 15):
                dense = K in near
                mods = np.arange(570, 961) if dense else np.array(INSTANT_MODS)
                f = scale.get(date, 1.0)
                mid = mid_fn(date, right, K, mods) * f
                hs = hs_fn(date, right, K, mods)
                keep = np.ones(len(mods), bool) if drop_fn is None else ~drop_fn(date, right, K, mods)
                qparts.append(pd.DataFrame({"date": date, "right": right, "strike": float(K), "mod": mods[keep],
                                            "bid": np.round(np.maximum(mid - hs, 0.0), 6)[keep],
                                            "ask": np.round(mid + hs, 6)[keep]}))
                if dense and trades:
                    bm = np.arange(570, 960)
                    tparts.append(pd.DataFrame({"date": date, "right": right, "strike": float(K), "mod": bm,
                                                "close": np.round(mid_fn(date, right, K, bm + 1) * f, 6)}))
    q = pd.concat(qparts, ignore_index=True)
    q["ts"] = [et_utc(d, m).strftime("%Y-%m-%d %H:%M:%S") for d, m in zip(q["date"], q["mod"])]
    q["expiry"], q["bid_size"], q["ask_size"] = q["date"], 10, 10
    for month, g in q.groupby(q["date"].str[:7]):
        g[costs.QUOTE_FILE_COLS].to_csv(os.path.join(root, f"spy_0dte_quotes_1min_{month}.csv.gz"), index=False)
    if trades:
        t = pd.concat(tparts, ignore_index=True)
        t["ts"] = [et_utc(d, m).strftime("%Y-%m-%d %H:%M:%S") for d, m in zip(t["date"], t["mod"])]
        t["expiry"], t["open"], t["high"], t["low"], t["volume"] = t["date"], t["close"], t["close"], t["close"], 5
        t[costs.TRADE_FILE_COLS].to_csv(os.path.join(root, "spy_0dte_1min_2026.csv.gz"), index=False)
    man = {"vendor": "synthetic", "dataset": "synthetic", "schema": "bbo-1m", "ts_semantics": "end of interval",
           "band": 0.04, "window": costs.WINDOW_TEXT, "rows_on_change": False, "excluded_sessions": []}
    man.update(manifest or {})
    with open(os.path.join(root, "quotes_manifest.json"), "w") as f:
        json.dump(man, f)
    return World(root, make_frame(dates, S_fn), dates, base_of)


def run_unit(world, out_dir, reread="fake"):
    """costs.run_unit on `world` with the M4 module mocked; returns (exit code, reread calls)."""
    out = os.path.join(out_dir, "costs_decision.csv")
    calls = []
    fake = fake_reread_frame(calls) if reread == "fake" else reread
    code = None
    with patched(costs, "run_reread", fake), quiet():
        try:
            costs.run_unit(world.inp, out, frame=world.frame)
        except SystemExit as e:
            code = e.code
    return code, calls


def read(out_dir, name):
    return pd.read_csv(os.path.join(out_dir, name))


def load(world, manifest=None):
    """(quote frame, Manifest, trade shard paths) of a world, through the unit's own readers."""
    import glob
    q = costs.read_quote_shards(costs.quote_shard_paths(world.inp))
    man, problems = costs.read_manifest(world.inp)
    assert man is not None, problems
    return q, man, sorted(glob.glob(os.path.join(world.inp, costs.TRADE_GLOB)))


# --- the Test-1 world: five sessions with hand-designed half-spreads --------------------------------------------
D1 = ["2026-03-04", "2026-03-05", "2026-03-06", "2026-03-09", "2026-03-10"]     # 03-08 is the spring-forward Sunday
BASE1 = {d: 500.0 + i for i, d in enumerate(D1)}
# S at every instant of session i is 500.4 + i, so (A8, by hand): K_call = floor(0.98 S), K_put = ceil(1.02 S)
K_C1 = [490.0, 491.0, 492.0, 493.0, 494.0]      # 0.98 x [500.4, 501.4, 502.4, 503.4, 504.4] = 490.392 .. 494.312
K_P1 = [511.0, 512.0, 513.0, 514.0, 515.0]      # 1.02 x the same = 510.408 .. 514.488
A_ENTRY = [0.02, 0.04, 0.01, 0.10, 0.03]        # entry half-spread of the first entry instant (10:01), calls
X_EXIT = [0.03, 0.05, 0.02, 0.12, 0.03]         # exit (15:55) half-spread, calls


def hs_designed(date, right, K, mods):
    """Half-spread (dollars) = a_i + 0.01 j at entry instant j (+0.02 for puts, and another +0.10 for the put of the
    LAST entry instant, an outlier leg that separates a mean over legs from a median), x_i (+0.01 for puts) at 15:55,
    on the contract the unit must pick; 0.5 on every other strike, so a wrong strike changes RT visibly."""
    i = D1.index(date) if date in D1 else None
    mods = np.asarray(mods)
    if i is None or K != (K_C1[i] if right == "C" else K_P1[i]):
        return np.full(len(mods), 0.5)
    out = np.full(len(mods), 0.03)
    for j, m in enumerate(ENTRY_MODS):
        out[mods == m] = A_ENTRY[i] + 0.01 * j + (0.0 if right == "C" else 0.02 + (0.10 if j == 4 else 0.0))
    out[mods == 955] = X_EXIT[i] + (0.0 if right == "C" else 0.01)
    return out


# Hand-computed: RT(leg) = 10 x (entry half-spread + exit half-spread), calls then puts, instants 10:01..15:31.
# Session 0: calls 10(0.02+0.01j+0.03) = 0.50 0.60 0.70 0.80 0.90; puts +10(0.02+0.01) = +0.30 and the last put
# another +10 x 0.10 = +1.0: 0.80 0.90 1.00 1.10 2.20.
EXPECTED_RT = {
    "2026-03-04": ([0.50, 0.60, 0.70, 0.80, 0.90], [0.80, 0.90, 1.00, 1.10, 2.20]),
    "2026-03-05": ([0.90, 1.00, 1.10, 1.20, 1.30], [1.20, 1.30, 1.40, 1.50, 2.60]),
    "2026-03-06": ([0.30, 0.40, 0.50, 0.60, 0.70], [0.60, 0.70, 0.80, 0.90, 2.00]),
    "2026-03-09": ([2.20, 2.30, 2.40, 2.50, 2.60], [2.50, 2.60, 2.70, 2.80, 3.90]),
    "2026-03-10": ([0.60, 0.70, 0.80, 0.90, 1.00], [0.90, 1.00, 1.10, 1.20, 2.30]),
}
EXPECTED_CS = [0.95, 1.35, 0.75, 2.65, 1.05]            # mean of the ten RT of each session (e.g. (3.5 + 6.0) / 10)
EXPECTED_CM, EXPECTED_CS_MEAN = 1.05, 1.35              # median of EXPECTED_CS (sorted .75 .95 1.05 1.35 2.65); mean 6.75/5
EXPECTED_LEG_MEDIAN_CM = 1.0                            # median of the 50 leg RTs (25th and 26th sorted are both 1.0): NOT Cm
EXPECTED_INTRADAY_S = [1.2, 1.6, 1.0, 2.8, 1.4]         # mean full entry spread x10 = 20 a_i + 0.6 + 0.2 (the outlier leg)
EXPECTED_CM_INTRADAY = 1.4                              # median; their mean is 1.6


def world1(root, **kw):
    kw.setdefault("hs_fn", hs_designed)
    return make_world(root, D1, lambda d: BASE1[d], **kw)


# ---------------------------------------------------------------------------------------------
# 1. Known spreads recovered exactly (RT, c_s, Cm, Cm_intraday)
# ---------------------------------------------------------------------------------------------

def test_known_spreads_recovered_exactly():
    with tmpdir() as tmp:
        w = world1(os.path.join(tmp, "ext"))
        out = os.path.join(tmp, "out")
        code, calls = run_unit(w, out)
        assert code == 0, f"unit exited {code}"
        sess = read(out, "costs_sessions.csv")
        assert list(sess.columns) == costs.SESSIONS_COLS
        assert list(sess["date"]) == D1 and list(sess["n_legs"]) == [10] * 5
        assert list(sess["n_legs_locked_crossed"]) == [0] * 5
        for _, row in sess.iterrows():
            calls_rt, puts_rt = EXPECTED_RT[row["date"]]
            for j, lbl in enumerate(["1001", "1101", "1301", "1501", "1531"]):
                assert abs(row[f"rt_{lbl}_C"] - calls_rt[j]) < 1e-6, (row["date"], lbl, "C", row[f"rt_{lbl}_C"])
                assert abs(row[f"rt_{lbl}_P"] - puts_rt[j]) < 1e-6, (row["date"], lbl, "P", row[f"rt_{lbl}_P"])
        assert np.allclose(sess["c_s"], EXPECTED_CS, atol=1e-6), list(sess["c_s"])
        assert np.allclose(sess["c_intraday"], EXPECTED_INTRADAY_S, atol=1e-6), list(sess["c_intraday"])
        dec = read(out, "costs_decision.csv").iloc[0]
        assert abs(dec["cm"] - EXPECTED_CM) < 1e-6, dec["cm"]
        assert abs(dec["mean"] - EXPECTED_CS_MEAN) < 1e-6        # the mean differs from the median: Cm is the MEDIAN
        assert abs(dec["cm_intraday"] - EXPECTED_CM_INTRADAY) < 1e-6, dec["cm_intraday"]
        assert dec["n_sessions"] == 5 and dec["n_leg_slots"] == 50 and dec["n_legs_missing"] == 0
        assert dec["label"] == "COMPLETE" and dec["band"] == ">=1.0" and "Cm >= 1.0 pt" in dec["meaning"]
        assert dec["min"] == 0.75 and dec["max"] == 2.65 and dec["median"] == 1.05
        assert abs(dec["p10"] - 0.83) < 1e-6 and abs(dec["p90"] - 2.13) < 1e-6
        assert dec["share_one_cent"] == 0.0 and dec["share_locked_crossed"] == 0.0 and dec["share_legs_locked_crossed"] == 0.0
        pooled = [x for calls_rt, puts_rt in EXPECTED_RT.values() for x in calls_rt + puts_rt]
        assert abs(np.median(pooled) - EXPECTED_LEG_MEDIAN_CM) < 1e-12 and dec["cm"] != EXPECTED_LEG_MEDIAN_CM, \
            "Cm is the median over sessions of the per-session mean, not the median over legs"
        assert dec["vendor"] == "synthetic" and dec["schema"] == "bbo-1m" and dec["ts_semantics"] == "end of interval"
        assert dec["cm_lo"] <= dec["cm"] <= dec["cm_hi"] and 0.75 <= dec["cm_lo"] and dec["cm_hi"] <= 2.65
        assert len(calls) == 1 and abs(calls[0][0] - EXPECTED_CM) < 1e-6 and abs(calls[0][1] - EXPECTED_CM_INTRADAY) < 1e-6, calls
        # the strikes the unit used are the hand-derived A8 strikes (S from the bar ENDING at the instant)
        q, man, _ = load(w)
        legs = costs.decision_legs(costs.QuoteBook(q, 300), costs.underlying_lookup(w.frame, costs.MOD.values()),
                                   [ndays(d) for d in D1])
        for i, d in enumerate(D1):
            g = legs[legs["date_days"] == ndays(d)]
            assert set(g.loc[g["right"] == "C", "K"]) == {K_C1[i]} and set(g.loc[g["right"] == "P", "K"]) == {K_P1[i]}
            assert np.allclose(g["S"], 500.4 + i)


# ---------------------------------------------------------------------------------------------
# 2. Zero spread -> Cm == 0 exactly and every M3 RT == 0
# ---------------------------------------------------------------------------------------------

def test_zero_spread_gives_zero_cm_and_zero_rt():
    with tmpdir() as tmp:
        w = world1(os.path.join(tmp, "ext"), hs_fn=const_hs(0.0))
        out = os.path.join(tmp, "out")
        code, _calls = run_unit(w, out)
        assert code == 0
        dec = read(out, "costs_decision.csv").iloc[0]
        assert dec["cm"] == 0.0 and dec["cm_lo"] == 0.0 and dec["cm_hi"] == 0.0 and dec["cm_intraday"] == 0.0
        assert dec["share_locked_crossed"] == 1.0 and dec["share_one_cent"] == 1.0   # c_s = 0 <= 0 and <= 0.1
        assert dec["share_legs_locked_crossed"] == 1.0
        assert "locked_crossed_share=1.000000" in read(out, "costs_validation.csv")["detail"][0]
        sess = read(out, "costs_sessions.csv")
        assert (sess["c_s"] == 0.0).all() and (sess["c_intraday"] == 0.0).all()
        assert (sess["n_legs_locked_crossed"] == 10).all(), "bid == ask on every leg: all ten are locked"
        depth = read(out, "costs_depth.csv")
        live = depth[depth["n"] > 0]
        assert len(live) >= 10, "the zero-spread check would be vacuous"
        assert (live["rt_mean"] == 0.0).all() and (live["rt_median"] == 0.0).all()
        surf = read(out, "costs_surface.csv")
        assert (surf.loc[surf["n"] > 0, "max"] == 0.0).all() and (surf["share_locked_crossed"].dropna() == 1.0).all()


# ---------------------------------------------------------------------------------------------
# 3. Prevailing-quote rule (look-ahead, 5-minute limit, session and contract isolation)
# ---------------------------------------------------------------------------------------------

def _q(book, date, mod, right, K):
    t = int(et_utc(date, mod).value // 10 ** 9)
    bid, ask = book.lookup([ndays(date)], [int(right == "P")], [float(K)], [t])
    return None if np.isnan(bid[0]) else (round(float(bid[0]), 6), round(float(ask[0]), 6))


def test_prevailing_quote_rule():
    d, prev = "2026-03-04", "2026-03-03"
    q = canon([
        (d, 598, "C", 490, 10.00, 10.10),       # 09:58, three minutes before t = 10:01
        (d, 602, "C", 490, 99.0, 99.5),         # 10:02, AFTER t: must never be used
        (d, 601, "C", 491, 9.00, 9.20),         # exactly at t
        (d, 596, "C", 492, 8.00, 8.10),         # 09:56 = exactly 5 minutes old: still valid ("no older than")
        (d, 595, "C", 493, 7.00, 7.10),         # 09:55 = 6 minutes old
        (d, 598, "P", 490, 1.00, 1.10),         # the put of the same strike must not leak into the call
        (d, 602, "C", 495, 5.00, 5.10),         # only a future row
        (prev, 959, "C", 494, 6.00, 6.10),      # the previous session's last quote
    ])
    book = costs.QuoteBook(q, costs.MAX_AGE_S)
    assert _q(book, d, 601, "C", 490) == (10.00, 10.10), "the latest row <= t must win, never the 10:02 row"
    assert _q(book, d, 601, "C", 491) == (9.00, 9.20), "a row exactly at t is the prevailing quote"
    assert _q(book, d, 601, "C", 492) == (8.00, 8.10), "exactly 5 minutes old is valid"
    assert _q(book, d, 601, "C", 493) is None, "6 minutes old with a 5-minute limit is missing, never filled"
    assert _q(book, d, 601, "P", 490) == (1.00, 1.10)
    assert _q(book, d, 601, "C", 495) is None, "a row stamped after t is invisible (no look-ahead)"
    assert _q(book, d, 572, "C", 494) is None, "yesterday's quote is not the prevailing quote of today's session"
    assert _q(book, d, 601, "C", 496) is None, "no row for the contract"
    assert math.isnan(book.lookup([ndays(d)], [0], [float("nan")], [int(et_utc(d, 601).value // 10 ** 9)])[0][0]), \
        "a NaN strike (no strike resolved) is a missing leg"
    dup = costs.QuoteBook(canon([(d, 600, "C", 490, 1.0, 1.1), (d, 600, "C", 490, 2.0, 2.1), (d, 599, "C", 490, 3.0, 3.1)]), 300)
    assert dup.n_duplicates == 1 and _q(dup, d, 601, "C", 490) == (2.0, 2.1), "duplicate (contract, ts): the last row wins"


def test_staleness_limit_depends_on_rows_on_change():
    """A51a: 30 minutes when the manifest says rows_on_change, A51's 5 minutes otherwise; the limit is inclusive."""
    assert costs.max_age_seconds(True) == 1800 and costs.max_age_seconds(False) == 300
    d = "2026-03-04"
    ages = {500.0: 20, 501.0: 30, 502.0: 31}                  # minutes between the row and t = 10:01
    q = canon([(d, 601 - age, "C", k, 10.0 + i, 10.1 + i) for i, (k, age) in enumerate(ages.items())])
    on_change = costs.QuoteBook(q, costs.max_age_seconds(True))
    fixed = costs.QuoteBook(q, costs.max_age_seconds(False))
    assert _q(on_change, d, 601, "C", 500) == (10.0, 10.1), "20 minutes old is valid when rows_on_change is true"
    assert _q(fixed, d, 601, "C", 500) is None, "20 minutes old is missing when rows_on_change is false"
    assert _q(on_change, d, 601, "C", 501) == (11.0, 11.1), "exactly 30 minutes old is valid (inclusive)"
    assert _q(fixed, d, 601, "C", 501) is None
    assert _q(on_change, d, 601, "C", 502) is None, "31 minutes old is missing even when rows_on_change is true"
    assert _q(fixed, d, 601, "C", 502) is None, "31 minutes old is missing when rows_on_change is false"


def test_manifest_flag_reaches_every_lookup():
    """measure() builds its QuoteBook from the manifest: a 15:55 exit quote that is 24 minutes old (the 15:31 row is
    the last one) is missing under rows_on_change=false and used under true."""
    def drop_exit(date, right, K, mods):
        return (np.asarray(mods) == 955) & (date == D1[0]) & (K == K_C1[0]) & (right == "C")

    with tmpdir() as tmp:
        w = world1(os.path.join(tmp, "ext"), drop_fn=drop_exit)
        q, man, trades = load(w)
        base = dict(vendor="v", schema="s", ts_semantics="t", excluded=frozenset())
        res_fixed = costs.measure(q, w.frame, costs.Manifest(rows_on_change=False, **base), trades)
        res_change = costs.measure(q, w.frame, costs.Manifest(rows_on_change=True, **base), trades)
        s_fixed, s_change = res_fixed["sessions"], res_change["sessions"]
        assert list(s_fixed["n_legs"]) == [5, 10, 10, 10, 10], "the five call legs of session 0 lose their exit quote"
        assert list(s_change["n_legs"]) == [10] * 5, "30 minutes reaches back to the 15:31 row"
        d_fixed, d_change = res_fixed["decision"].iloc[0], res_change["decision"].iloc[0]
        assert d_fixed["n_legs_missing"] == 5 and d_change["n_legs_missing"] == 0
        assert d_fixed["quote_max_age_min"] == 5.0 and d_change["quote_max_age_min"] == 30.0
        assert bool(d_fixed["rows_on_change"]) is False and bool(d_change["rows_on_change"]) is True


def test_empty_book_row_is_missing_not_filled():
    """A51a: a row with an empty bid or ask means no quote at that instant. It stays the prevailing row; the leg is
    missing and is NOT filled from an older priced row, even one inside the staleness limit."""
    header = "ts,expiry,strike,right,bid,ask,bid_size,ask_size\n"
    rows = [
        "2026-03-04 14:50:00,2026-03-04,490.0,C,10.00,10.10,5,5",     # 09:50 ET, priced
        "2026-03-04 15:00:00,2026-03-04,490.0,C,,,0,0",               # 10:00 ET, empty book
        "2026-03-04 14:50:00,2026-03-04,491.0,C,9.00,9.10,5,5",
        "2026-03-04 15:00:00,2026-03-04,491.0,C,9.05,,5,0",           # empty ask only
        "2026-03-04 14:50:00,2026-03-04,492.0,C,,,0,0",               # empty first ...
        "2026-03-04 15:01:00,2026-03-04,492.0,C,8.00,8.10,5,5",       # ... priced again exactly at t
        "2026-03-04 14:50:00,2026-03-04,493.0,C,7.00,7.10,5,5",
        "2026-03-04 15:00:00,2026-03-04,493.0,C,7.20,7.30,5,5",       # a newer priced row replaces the older
    ]
    with tmpdir() as tmp:
        path = os.path.join(tmp, "spy_0dte_quotes_1min_2026-03.csv.gz")
        with open(path[:-3], "w") as f:
            f.write(header + "\n".join(rows) + "\n")
        import gzip
        with open(path[:-3], "rb") as src, gzip.open(path, "wb") as dst:
            dst.write(src.read())
        q = costs.read_quote_shards([path])
        assert len(q) == len(rows), "empty-book records must be kept, not dropped"
        book = costs.QuoteBook(q, costs.max_age_seconds(True))           # 30 minutes: the 09:50 row is in range
        d = "2026-03-04"
        assert _q(book, d, 601, "C", 490) is None, "empty book at 10:00: missing, not the priced 09:50 row"
        assert _q(book, d, 601, "C", 491) is None, "an empty ask is an empty book too"
        assert _q(book, d, 601, "C", 492) == (8.00, 8.10), "a priced row at t after an empty one is the quote"
        assert _q(book, d, 600, "C", 492) is None, "before it, only the empty record is in range"
        assert _q(book, d, 601, "C", 493) == (7.20, 7.30)


def test_empty_book_at_the_entry_instant_is_a_missing_leg_end_to_end():
    """A51a through the whole unit: with rows_on_change the 09:32 row is 29 minutes old at 10:01 and would pass the 30-minute
    limit, but the 10:01 record itself is an empty book (the vendor sent no bid and no ask), so those two legs are
    missing and are not filled from 09:32."""
    S_fn = default_S(lambda d: BASE1[d])

    def mid(date, right, K, mods):
        m = default_mid(S_fn)(date, right, K, mods)
        empty = (np.asarray(mods) == 601) & (date == D1[0]) & (K == (K_C1[0] if right == "C" else K_P1[0]))
        return np.where(empty, np.nan, m)
    with tmpdir() as tmp:
        w = world1(os.path.join(tmp, "ext"), mid_fn=mid, manifest={"rows_on_change": True}, trades=False)
        q, man, _ = load(w)
        assert man.rows_on_change is True and q["bid"].isna().sum() == 2, "two empty-book records, kept"
        sess = costs.measure(q, w.frame, man, [])["sessions"]
        assert list(sess["n_legs"]) == [8, 10, 10, 10, 10]
        assert np.isnan(sess.loc[0, "rt_1001_C"]) and np.isnan(sess.loc[0, "rt_1001_P"])
        assert abs(sess.loc[0, "rt_1101_C"] - 0.60) < 1e-6, "the other legs of the session are untouched"


def test_prepare_quotes_maps_utc_to_ny_session_and_guards_expiry():
    raw = pd.DataFrame({
        "ts": ["2026-01-15 15:01:00", "2026-07-15 14:01:00", "2026-07-15 14:01:00", "2026-07-15 20:00:00"],
        "expiry": ["2026-01-15", "2026-07-15", "2026-07-16", "2026-07-15"],      # third row: not a same-day contract
        "strike": [490.0, 490.0, 490.0, 490.0], "right": ["c", "P", "C", "C"],
        "bid": [1.0, np.nan, 1.0, 1.0], "ask": [1.1, np.nan, 1.1, 1.1]})
    with quiet():
        q = costs.prepare_quotes(raw)
    assert len(q) == 3, "the expiry != session-date row is dropped"
    assert list(q["mod"]) == [601, 601, 960], "10:01 ET is 15:01 UTC in January and 14:01 UTC in July; 16:00 EDT = 20:00 UTC"
    assert list(q["date_days"]) == [ndays("2026-01-15"), ndays("2026-07-15"), ndays("2026-07-15")]
    assert list(q["is_put"]) == [0, 1, 0], "right is case-insensitive"
    assert np.isnan(q["bid"].iloc[1]) and np.isnan(q["ask"].iloc[1]), "an empty-book record stays NaN"
    for bad in (raw.assign(right=["X", "P", "C", "C"]), raw.drop(columns=["ask"])):
        try:
            costs.prepare_quotes(bad)
        except ValueError:
            continue
        raise AssertionError("an invalid right or a missing column must raise, never be skipped")


# ---------------------------------------------------------------------------------------------
# 4. A8 rounding for M2
# ---------------------------------------------------------------------------------------------

def test_a8_rounding_away_from_spot():
    cases = [   # S, call K, put K  (by hand: 0.98 S and 1.02 S rounded away from spot)
        (500.0, 490.0, 510.0),     # exact integers stay: 0.98 x 500 = 490, 1.02 x 500 = 510
        (250.0, 245.0, 255.0),     # 245 and 255 exactly
        (500.5, 490.0, 511.0),     # 490.49 -> down 490 (toward spot would be 491); 510.51 -> up 511 (toward spot 510)
        (501.0, 490.0, 512.0),     # 490.98 -> 490; 511.02 -> 512
        (499.99, 489.0, 510.0),    # 489.9902 -> 489 (toward spot 490); 509.9898 -> 510 (toward spot 509)
    ]
    for S, kc, kp in cases:
        assert costs.a8_strike(S, "C") == kc, f"call S={S}: {costs.a8_strike(S, 'C')} != {kc}"
        assert costs.a8_strike(S, "P") == kp, f"put S={S}: {costs.a8_strike(S, 'P')} != {kp}"
    assert math.isnan(costs.a8_strike(float("nan"), "C"))


# ---------------------------------------------------------------------------------------------
# 5. DST
# ---------------------------------------------------------------------------------------------

def test_dst_same_et_instant_maps_to_different_utc():
    assert costs.et_to_utc("2026-01-15", 601) == pd.Timestamp("2026-01-15 15:01:00", tz="UTC")
    assert costs.et_to_utc("2026-07-15", 601) == pd.Timestamp("2026-07-15 14:01:00", tz="UTC")
    assert costs.et_to_utc("2026-03-06", 601) == pd.Timestamp("2026-03-06 15:01:00", tz="UTC")   # EST, before the change
    assert costs.et_to_utc("2026-03-09", 601) == pd.Timestamp("2026-03-09 14:01:00", tz="UTC")   # EDT, after it
    assert costs.et_to_utc("2026-11-02", 960) == pd.Timestamp("2026-11-02 21:00:00", tz="UTC")   # 16:00 EST
    a = costs.instant_seconds(ndays("2026-01-15"), 601) % 86400
    b = costs.instant_seconds(ndays("2026-07-15"), 601) % 86400
    assert a - b == 3600


def test_dst_end_to_end_instants_hit_the_right_quotes():
    """Every instant's half-spread is unique, so a quote read one instant (or one hour) off changes the answer."""
    hs_by_mod = dict(zip(INSTANT_MODS, [0.01, 0.02, 0.03, 0.04, 0.05, 0.06, 0.07, 0.08, 0.09]))

    def hs(date, right, K, mods):
        return np.array([hs_by_mod.get(int(m), 0.5) for m in mods])

    S_fn = default_S(lambda d: 500.0)

    def mid(date, right, K, mods):                       # mids >= 0.2 so that mid - 0.09 never clips at a zero bid
        return default_mid(S_fn)(date, right, K, mods) + 0.2

    with tmpdir() as tmp:
        dates = ["2026-01-15", "2026-07-15"]          # context (2026Q1, EST) and DECISION (EDT)
        w = make_world(os.path.join(tmp, "ext"), dates, lambda d: 500.0, hs_fn=hs, mid_fn=mid, trades=False)
        q, man, _ = load(w)
        S_of = costs.underlying_lookup(w.frame, costs.MOD.values())
        groups = costs.session_groups({ndays(d) for d in dates}, {ndays(d) for d in dates})
        assert [g[0] for g in groups] == ["DECISION", "2026Q1"]
        legs = costs.surface_legs(costs.QuoteBook(q, 300), costs.listed_strikes(q), S_of, groups)
        assert len(legs) == 2 * 9 * 2 * 9 and legs["bid"].notna().all()
        for _, g in legs.groupby(["window", "instant"]):
            spread = (g["ask"] - g["bid"]).to_numpy()
            want = 2 * hs_by_mod[int(g["mod"].iloc[0])]
            assert np.allclose(spread, want, atol=1e-9), (g["window"].iloc[0], g["instant"].iloc[0], set(spread), want)


# ---------------------------------------------------------------------------------------------
# 6. V1 (scale, mapping) and V2 (timestamp alignment)
# ---------------------------------------------------------------------------------------------

def _v1_of(q, w):
    S_of = costs.underlying_lookup(w.frame, costs.MOD.values())
    groups = costs.session_groups(set(q["date_days"]), costs.frame_days(w.frame))
    legs = costs.surface_legs(costs.QuoteBook(q, 300), costs.listed_strikes(q), S_of, groups)
    return costs.check_v1(legs)


def test_v1_catches_scale_error_swapped_right_and_threshold_edges():
    with tmpdir() as tmp:
        w = world1(os.path.join(tmp, "ext"), trades=False)
        q, _man, _ = load(w)
        ok = _v1_of(q, w)
        assert ok["pass"] and abs(ok["value_1"] - 0.12) < 1e-9 and abs(ok["value_2"] - 0.12) < 1e-9, ok   # the time value
        scaled = q.assign(bid=q["bid"] * 100.0, ask=q["ask"] * 100.0)
        r = _v1_of(scaled, w)
        assert not r["pass"] and r["value_1"] > 100 and r["value_2"] > 100, r
        swapped = q.assign(is_put=1 - q["is_put"])
        r = _v1_of(swapped, w)
        assert not r["pass"] and r["value_1"] < -5.0 and r["value_2"] < -5.0, \
            f"every swapped deep-ITM leg is an OTM option priced against ITM intrinsic: {r}"
        # additive shifts around the [-0.10, +0.25] band (median time value is 0.12)
        for shift, expect in ((0.10, True), (0.20, False), (-0.15, True), (-0.30, False)):
            r = _v1_of(q.assign(bid=q["bid"] + shift, ask=q["ask"] + shift), w)
            assert r["pass"] is expect, (shift, r)


def _legs_v1(call_excess, put_excess, extra=()):
    """Hand-built M1 legs: S = 500, call K = 490 (intrinsic 10), put K = 510 (intrinsic 10), mid = intrinsic + excess."""
    rows = []
    for right, K, exc in [("C", 490.0, call_excess), ("P", 510.0, put_excess)]:
        for e in exc:
            rows.append(("DECISION", 1, "10:01", 601, right, 2.0, 500.0, K, 10.0 + e - 0.005, 10.0 + e + 0.005))
    rows.extend(extra)
    return pd.DataFrame(rows, columns=["window", "date_days", "instant", "mod", "right", "m", "S", "K", "bid", "ask"])


def test_v1_pools_calls_and_puts_separately_deep_itm_decision_only():
    good = [-0.0999, 0.0, 0.2499]                                   # median 0.0
    assert costs.check_v1(_legs_v1(good, good))["pass"]
    edge_hi = costs.check_v1(_legs_v1([0.2499] * 3, good))
    edge_lo = costs.check_v1(_legs_v1(good, [-0.0999] * 3))
    assert edge_hi["pass"] and edge_lo["pass"] and abs(edge_hi["value_1"] - 0.2499) < 1e-9
    assert not costs.check_v1(_legs_v1([0.2501] * 3, good))["pass"], "calls above +0.25"
    assert not costs.check_v1(_legs_v1(good, [-0.1001] * 3))["pass"], "puts below -0.10, calls fine: puts are judged separately"
    assert not costs.check_v1(_legs_v1([], good))["pass"], "no calls at all cannot pass"
    skew = [0.0, 0.0, 0.0, 0.0, 5.0]                                  # median 0.0 passes, mean 1.0 would not
    r = costs.check_v1(_legs_v1(skew, skew))
    assert r["pass"] and r["value_1"] == r["value_2"] == 0.0, "V1 is the MEDIAN of (mid - intrinsic)"
    # legs that must NOT enter: shallower than 1.5 % ITM, and any window other than DECISION. Four wild puts
    # against three good ones would move the median if they were pooled.
    def wild_puts(window, m):
        return [(window, 1, "10:01", 601, "P", m, 500.0, 507.5, 99.0, 99.2)] * 4
    for window, m in (("DECISION", 1.0), ("DECISION", 0.5), ("DECISION", -1.0), ("2025Q4", 2.0)):
        r = costs.check_v1(_legs_v1(good, good, extra=wild_puts(window, m)))
        assert r["pass"] and r["n"] == 6, (window, m, r)
    r = costs.check_v1(_legs_v1(good, good, extra=wild_puts("DECISION", 1.5)))
    assert not r["pass"] and r["n"] == 10 and r["value_2"] > 50, "m = 1.5 is the first ITM depth that counts (>= 1.5)"
    assert costs.check_v1(_legs_v1(good, good, extra=wild_puts("DECISION", 2.5)))["pass"] is False


def _v2_fixture(shift_s=0, seed=7):
    """Quotes and trade bars for four contracts over one session. The BBO mid random-walks 0.10-0.20 a minute (half-
    spread 0.02), and the bar starting at minute k closes at the mid of the minute-(k+1) instant, i.e. the quote
    stamped at the bar END. `shift_s` mislabels the quote stamps by that many seconds."""
    rng = np.random.default_rng(seed)
    d, mods = "2026-03-04", np.arange(570, 961)
    qrows, brows = [], []
    for right, K in [("C", 500.0), ("P", 500.0), ("C", 501.0), ("P", 499.0)]:
        step = rng.choice([-1.0, 1.0], len(mods)) * (0.10 + 0.10 * rng.random(len(mods)))
        mid = 10.0 + np.cumsum(step)
        qrows += [(d, int(m), right, K, mid[i] - 0.02, mid[i] + 0.02) for i, m in enumerate(mods)]
        brows += [(ndays(d), int(right == "P"), K, int(et_utc(d, int(m)).value // 10 ** 9), mid[i + 1])
                  for i, m in enumerate(mods[:-1])]
    q = canon(qrows)
    q["tsec"] = q["tsec"] + shift_s
    bars = pd.DataFrame(brows, columns=["date_days", "is_put", "strike", "tsec", "close"])
    return costs.QuoteBook(q, 300), bars


def test_v2_catches_timestamp_shifts():
    book, bars = _v2_fixture(0)
    r = costs.check_v2(book, bars)
    assert r["pass"] and r["value_1"] == 1.0 and r["value_2"] == 0.0 and r["n"] == len(bars), r
    for shift, why in ((60, "+1 minute (stamps one minute late)"), (-60, "-1 minute: the START alignment scores higher"),
                       (3600, "+60 minutes"), (-3600, "-60 minutes"), (5 * 3600, "a five-hour timezone error")):
        r = costs.check_v2(*_v2_fixture(shift))
        assert not r["pass"], f"V2 must fail for a {why}: {r}"
    r = costs.check_v2(*_v2_fixture(-60))
    assert r["value_2"] > r["value_1"], "with stamps one minute EARLY the quote at the bar start matches the close"


def test_v2_decision_rule_boundaries_and_ties():
    d = "2026-03-04"
    t = int(et_utc(d, 601).value // 10 ** 9)
    # quotes: bid 9.99 / ask 10.01 at both 10:00 and 10:01 (identical), so start and end alignments always tie
    q = canon([(d, 600, "C", 500, 9.99, 10.01), (d, 601, "C", 500, 9.99, 10.01)])
    book = costs.QuoteBook(q, 300)

    def bars(closes):
        return pd.DataFrame({"date_days": ndays(d), "is_put": 0, "strike": 500.0, "tsec": t - 60,
                             "close": closes})
    r = costs.check_v2(book, bars([10.00, 10.019, 9.981, 10.021]))       # last one is 0.011 above ask: outside
    assert r["value_1"] == r["value_2"] == 0.75 and r["pass"], "a tie passes when the share is at least 0.25"
    r = costs.check_v2(book, bars([10.00, 10.03, 10.03, 10.03]))
    assert r["value_1"] == 0.25 and r["pass"], "exactly 25 % passes"
    r = costs.check_v2(book, bars([10.00, 10.03, 10.03, 10.03, 10.03]))
    assert r["value_1"] == 0.2 and not r["pass"], "20 % fails the floor"
    r = costs.check_v2(book, bars([10.02, 9.98]))                         # exactly ask+0.01 / bid-0.01: inside
    assert r["value_1"] == 1.0, "the [bid-0.01, ask+0.01] band is inclusive"
    assert not costs.check_v2(book, bars([]))["pass"], "no bars: cannot validate, fails visibly"
    # a second contract with ONLY an end-of-bar quote (nothing within 5 minutes before the bar start): its bars are not
    # scored at all, so both shares keep the same denominator
    lone = canon([(d, 600, "C", 500, 9.99, 10.01), (d, 601, "C", 500, 9.99, 10.01), (d, 601, "C", 501, 9.99, 10.01)])
    both = pd.concat([bars([10.00, 10.00]), bars([50.0, 50.0]).assign(strike=501.0)], ignore_index=True)
    r = costs.check_v2(costs.QuoteBook(lone, 300), both)
    assert r["n"] == 2 and r["value_1"] == 1.0, "bars of a contract without a start-of-bar quote leave the denominator alone"
    nobody = pd.DataFrame({"date_days": ndays(d), "is_put": 1, "strike": 500.0, "tsec": t - 60, "close": [10.0]})
    assert not costs.check_v2(book, nobody)["pass"], "bars without any quote cannot validate"


# ---------------------------------------------------------------------------------------------
# 7. Coverage gate and M4
# ---------------------------------------------------------------------------------------------

D10 = ["2026-03-02", "2026-03-03", "2026-03-04", "2026-03-05", "2026-03-06", "2026-03-09", "2026-03-10",
       "2026-03-11", "2026-03-12", "2026-03-13"]
BASE10 = {d: 500.0 + i for i, d in enumerate(D10)}


def _drop_entries(spec):
    """Drop the entry quote of the A8 contract for each (session index, right, entry mod) in `spec`."""
    def drop(date, right, K, mods):
        i = D10.index(date)
        kexp = math.floor(0.98 * (BASE10[date] + 0.4)) if right == "C" else math.ceil(1.02 * (BASE10[date] + 0.4))
        mods = np.asarray(mods)
        if K != kexp:
            return np.zeros(len(mods), bool)
        return np.isin(mods, [m for (si, r, m) in spec if si == i and r == right])
    return drop


def test_coverage_gate_and_reread_gating():
    twenty = [(i, r, 601) for i in range(10) for r in "CP"]               # 20 of 100 legs: exactly 20 %
    with tmpdir() as tmp:
        w = make_world(os.path.join(tmp, "a"), D10, lambda d: BASE10[d], drop_fn=_drop_entries(twenty))
        q, man, trades = load(w)
        res = costs.measure(q, w.frame, man, trades)
        dec = res["decision"].iloc[0]
        assert dec["n_leg_slots"] == 100 and dec["n_legs_missing"] == 20 and dec["missing_share"] == 0.2
        assert dec["label"] == "COMPLETE", "exactly 20 % missing is NOT more than 20 %"
        assert res["validation"][2]["pass"] is True
        out = os.path.join(tmp, "out_a")
        code, calls = run_unit(w, out)
        assert code == 0 and len(calls) == 1, (code, calls)
        assert abs(calls[0][0] - dec["cm"]) < 1e-9 and abs(calls[0][1] - dec["cm_intraday"]) < 1e-9
        assert len(read(out, "costs_reread.csv")) == 1 and list(read(out, "costs_reread.csv").columns) == costs.REREAD_COLS

        w2 = make_world(os.path.join(tmp, "b"), D10, lambda d: BASE10[d], drop_fn=_drop_entries(twenty + [(0, "C", 661)]))
        q, man, trades = load(w2)
        dec = costs.measure(q, w2.frame, man, trades)["decision"].iloc[0]
        assert dec["n_legs_missing"] == 21 and abs(dec["missing_share"] - 0.21) < 1e-12 and dec["label"] == "INCOMPLETE"
        assert "INCOMPLETE" in dec["meaning"] and dec["band"] != "n/a"
        out = os.path.join(tmp, "out_b")
        code, calls = run_unit(w2, out)
        assert code == 2 and calls == [], "INCOMPLETE: the unit fails visibly and run_reread is NOT called"
        assert os.path.exists(os.path.join(out, "costs_decision.csv.error"))
        val = read(out, "costs_validation.csv")
        assert list(val["check"]) == ["V1", "V2", "V3"] and list(val["pass"]) == [True, True, False]
        for name in ("costs_surface.csv", "costs_sessions.csv", "costs_depth.csv", "costs_reread.csv", "costs_trackc.csv"):
            assert len(read(out, name)) == 0, f"{name}: nothing is published on a validation failure"
        assert os.path.getsize(os.path.join(out, "costs_decision.csv")) == 0     # _gh.run's A32 contract


def test_reread_table_gating_and_columns():
    calls = []
    complete = {"label": "COMPLETE", "cm": 0.95, "cm_intraday": 1.2}
    with patched(costs, "run_reread", fake_reread_frame(calls)):
        df = costs.reread_table(complete)
        assert calls == [(0.95, 1.2)] and list(df.columns) == costs.REREAD_COLS
        inc = costs.reread_table(dict(complete, label="INCOMPLETE"))
        assert calls == [(0.95, 1.2)], "an INCOMPLETE Cm never reaches M4"
        assert len(inc) == 0 and list(inc.columns) == costs.REREAD_COLS
    with patched(costs, "run_reread", lambda cm, ci: pd.DataFrame({"x": [1]})):
        try:
            costs.reread_table(complete)
        except ValueError as e:
            assert "REREAD_COLS" in str(e)
        else:
            raise AssertionError("a re-read frame with other columns must raise, not write a second header")
    seen = []

    def stand_in(cm, cm_intraday):
        seen.append((cm, cm_intraday))
        return pd.DataFrame({"k": [1]})
    with fake_reread_module(stand_in):
        out = costs.run_reread(0.5, 0.75)
    assert seen == [(0.5, 0.75)] and list(out.columns) == ["k"], "run_reread delegates to costs_reread.reread(cm, cm_intraday)"


def test_reread_columns_match_costs_reread_module_when_present():
    try:
        from pipeline.units import costs_reread
    except ImportError:
        print("[note] pipeline.units.costs_reread is not importable here; column contract not checked")
        return
    assert list(costs_reread.COLS) == costs.REREAD_COLS, "costs.REREAD_COLS must equal costs_reread.COLS"


# ---------------------------------------------------------------------------------------------
# 8. Skip path and missing manifest
# ---------------------------------------------------------------------------------------------

SEVEN = ["costs_decision.csv", "costs_depth.csv", "costs_reread.csv", "costs_sessions.csv", "costs_surface.csv",
         "costs_trackc.csv", "costs_validation.csv"]
SEVEN_COLS = {"costs_decision.csv": costs.DECISION_COLS, "costs_depth.csv": costs.DEPTH_COLS,
              "costs_reread.csv": costs.REREAD_COLS, "costs_sessions.csv": costs.SESSIONS_COLS,
              "costs_surface.csv": costs.SURFACE_COLS, "costs_trackc.csv": costs.TRACKC_COLS,
              "costs_validation.csv": costs.VALIDATION_COLS}


def _cli(inp, out):
    return subprocess.run([sys.executable, "-m", "pipeline.units.costs", "--in", inp, "--out", out], cwd=REPO,
                          capture_output=True, text=True)


def test_skip_path_writes_seven_header_only_files_and_exits_zero():
    with tmpdir() as tmp:
        inp, out_dir = os.path.join(tmp, "ext"), os.path.join(tmp, "out")
        os.makedirs(inp)
        os.makedirs(out_dir)
        with open(os.path.join(out_dir, "costs_decision.csv.error"), "w") as f:      # a stale error must be cleared
            f.write("stale")
        r = _cli(inp, os.path.join(out_dir, "costs_decision.csv"))
        assert r.returncode == 0, r.stderr
        assert f"[SKIP] A51 waits for {os.path.join(inp, 'spy_0dte_quotes_1min_*.csv.gz')}" in r.stdout, r.stdout
        assert sorted(os.listdir(out_dir)) == SEVEN, sorted(os.listdir(out_dir))      # exactly seven, no .error
        for name, cols in SEVEN_COLS.items():
            df = pd.read_csv(os.path.join(out_dir, name))
            assert list(df.columns) == cols and len(df) == 0, name
        # the same skip path in-process: no frame is built (build_frame would need data/raw)
        with patched(costs, "build_frame", lambda *_: (_ for _ in ()).throw(AssertionError("frame built on skip"))):
            with quiet():
                costs.main(inp, os.path.join(tmp, "out2", "costs_decision.csv"))
        assert sorted(os.listdir(os.path.join(tmp, "out2"))) == SEVEN


def test_missing_manifest_fails_visibly():
    with tmpdir() as tmp:
        w = world1(os.path.join(tmp, "ext"))
        os.remove(os.path.join(w.inp, "quotes_manifest.json"))
        out_dir = os.path.join(tmp, "out")
        r = _cli(w.inp, os.path.join(out_dir, "costs_decision.csv"))
        assert r.returncode == 2, (r.returncode, r.stdout, r.stderr)
        assert os.path.exists(os.path.join(out_dir, "costs_decision.csv.error"))
        assert "manifest" in open(os.path.join(out_dir, "costs_decision.csv.error")).read().lower()
        val = pd.read_csv(os.path.join(out_dir, "costs_validation.csv"))
        assert list(val["check"]) == ["MANIFEST"] and list(val["pass"]) == [False]
        for name in SEVEN:
            if name not in ("costs_decision.csv", "costs_validation.csv"):
                df = pd.read_csv(os.path.join(out_dir, name))
                assert len(df) == 0 and list(df.columns) == SEVEN_COLS[name], name
        assert os.path.getsize(os.path.join(out_dir, "costs_decision.csv")) == 0


def test_manifest_validation():
    def manifest_of(content):
        with tmpdir() as tmp:
            if content is not None:
                with open(os.path.join(tmp, costs.MANIFEST_NAME), "w") as f:
                    f.write(content if isinstance(content, str) else json.dumps(content))
            return costs.read_manifest(tmp)

    good = {"vendor": "v", "schema": "s", "ts_semantics": "t"}
    man, problems = manifest_of(good)
    assert problems == [] and man.rows_on_change is False and man.excluded == frozenset(), "absent flag means false"
    man, problems = manifest_of(dict(good, rows_on_change=True, excluded_sessions=["2026-04-17", "2026-05-01"]))
    assert problems == [] and man.rows_on_change is True
    assert man.excluded == frozenset({ndays("2026-04-17"), ndays("2026-05-01")})
    assert manifest_of(None)[0] is None and "missing" in manifest_of(None)[1][0]
    assert manifest_of("{not json")[0] is None
    assert manifest_of([1, 2])[0] is None
    for bad in (dict(good, vendor=""), {k: v for k, v in good.items() if k != "ts_semantics"},
                dict(good, schema=3), dict(good, rows_on_change="true"), dict(good, rows_on_change=1),
                dict(good, excluded_sessions="2026-04-17"), dict(good, excluded_sessions=["2026-4-17"]),
                dict(good, excluded_sessions=["2026-02-30"]), dict(good, excluded_sessions=[20260417])):
        man, problems = manifest_of(bad)
        assert man is None and problems, f"must be rejected: {bad}"


# ---------------------------------------------------------------------------------------------
# 9. M3: delta, h, TC, exclusions
# ---------------------------------------------------------------------------------------------

def test_entry_delta_branches_and_bs_recovery():
    S, mins = 500.0, 359                                        # 10:01 -> 16:00
    T = mins / (365 * 24 * 60)
    assert costs.entry_delta(10.004, S, 490.0, mins, "C") == 1.0, "mid - intrinsic = 0.004 <= 0.005"
    assert costs.entry_delta(10.003, S, 510.0, mins, "P") == -1.0
    assert costs.entry_delta(10.005, S, 490.0, mins, "C") == 1.0, "exactly 0.005 is still +-1"
    assert costs.entry_delta(9.99, S, 490.0, mins, "C") == 1.0, "mid below intrinsic: still +-1, never excluded"
    d = costs.entry_delta(10.0051, S, 490.0, mins, "C")
    assert 0.9 < d < 1.0, f"just above 0.005 the delta is solved, not forced: {d}"
    for sigma in (0.10, 0.25, 0.60):
        mid_c = options.price(S, 500.0, mins, sigma, "c")
        mid_p = options.price(S, 500.0, mins, sigma, "p")
        want_c = options.bs_call(S, 500.0, T, sigma)[1]
        want_p = options.bs_put(S, 500.0, T, sigma)[1]
        assert abs(costs.entry_delta(mid_c, S, 500.0, mins, "C") - want_c) < 1e-6, sigma
        assert abs(costs.entry_delta(mid_p, S, 500.0, mins, "P") - want_p) < 1e-6, sigma
    assert 0.4 < want_c < 0.6 and -0.6 < want_p < -0.4, "ATM deltas are near +-0.5"
    mid_itm = options.price(S, 495.0, mins, 0.30, "c")
    assert abs(costs.entry_delta(mid_itm, S, 495.0, mins, "C") - options.bs_call(S, 495.0, T, 0.30)[1]) < 1e-6
    assert math.isnan(costs.entry_delta(400.0, S, 500.0, mins, "C")), "a mid above the sigma = 5 price does not solve"


def _m3_quotes():
    A, B, C = "2026-03-04", "2026-03-05", "2026-03-06"
    q = canon([
        (A, 601, "C", 490, 9.990, 10.018), (A, 955, "C", 490, 12.995, 13.011),      # session A: call, S 500 -> 503
        (B, 601, "P", 510, 9.990, 10.016), (B, 955, "P", 510, 12.990, 13.014),      # session B: put,  S 500 -> 497
        (C, 601, "C", 490, 449.9, 450.1), (C, 955, "C", 490, 12.995, 13.011),       # session C: absurd entry mid
    ])
    S = {(ndays(A), 601): 500.0, (ndays(A), 955): 503.0, (ndays(B), 601): 500.0, (ndays(B), 955): 497.0,
         (ndays(C), 601): 500.0, (ndays(C), 955): 503.0}
    return q, (lambda d, mod: S.get((int(d), int(mod)), float("nan"))), [ndays(x) for x in (A, B, C)]


def test_m3_hand_computed_h_tc_and_exclusions():
    q, S_of, days = _m3_quotes()
    legs = costs.depth_legs(costs.QuoteBook(q, 300), S_of, days, costs.listed_strikes(q))
    a = legs[(legs["date_days"] == days[0]) & (legs["right"] == "C") & (legs["instant"] == "10:01") & (legs["m"] == 2.0)].iloc[0]
    # call: mid_e 10.004 (intrinsic 10) -> delta +1; RT = 10 (0.014 + 0.008) = 0.22; h = 10 [(13.003-10.004) - 1 (503-500)] = -0.01
    assert a["delta"] == 1.0 and abs(a["rt"] - 0.22) < 1e-9 and abs(a["h"] - (-0.01)) < 1e-9
    assert abs(a["tc"] - 0.23) < 1e-9, a["tc"]                          # (0.22 + 0.01) / 1
    b = legs[(legs["date_days"] == days[1]) & (legs["right"] == "P") & (legs["instant"] == "10:01") & (legs["m"] == 2.0)].iloc[0]
    # put: mid_e 10.003 -> delta -1; RT = 10 (0.013 + 0.012) = 0.25; h = 10 [(13.002-10.003) - (-1)(497-500)] = -0.01
    assert b["delta"] == -1.0 and abs(b["rt"] - 0.25) < 1e-9 and abs(b["h"] - (-0.01)) < 1e-9
    assert abs(b["tc"] - 0.26) < 1e-9, b["tc"]                          # (0.25 + 0.01) / |-1|
    c = legs[(legs["date_days"] == days[2]) & (legs["right"] == "C") & (legs["instant"] == "10:01") & (legs["m"] == 2.0)].iloc[0]
    assert c["present"] and not c["solved"] and math.isnan(c["delta"])
    table = costs.depth_table(legs)
    call = table[(table["right"] == "C") & (table["instant"] == "10:01") & (table["moneyness_pct"] == 2.0)].iloc[0]
    assert (call["n_sessions"], call["n"], call["n_missing"], call["n_excluded"]) == (3, 1, 1, 1)
    assert abs(call["tc_mean"] - 0.23) < 1e-9 and abs(call["rt_mean"] - 0.22) < 1e-9 and call["delta_mean"] == 1.0
    assert abs(call["h_mean"] - (-0.01)) < 1e-9 and abs(call["h_median"] - (-0.01)) < 1e-9
    assert abs(call["rt_median"] - 0.22) < 1e-9 and call["delta_median"] == 1.0 and abs(call["tc_median"] - 0.23) < 1e-9
    put = table[(table["right"] == "P") & (table["instant"] == "10:01") & (table["moneyness_pct"] == 2.0)].iloc[0]
    assert (put["n"], put["n_missing"], put["n_excluded"]) == (1, 2, 0) and abs(put["tc_mean"] - 0.26) < 1e-9
    assert list(table.columns) == costs.DEPTH_COLS


def test_m3_cheapest_flag_and_bootstrap_columns():
    rows = []
    # m = 0.0: TC 1.4 every session (mean = median = 1.4); m = 0.5: 1, 1, 4 (mean 2.0, median 1.0): the lowest MEAN
    # is m = 0.0, the lowest median would be m = 0.5. m = 2.0 never solves.
    for m, tcs in ((0.0, [1.4, 1.4, 1.4]), (0.5, [1.0, 1.0, 4.0]), (1.0, [3.0, 3.0, 3.0]), (2.0, [np.nan] * 3)):
        for i, tc in enumerate(tcs):
            rows.append(("C", "10:01", m, i, bool(np.isfinite(tc)), bool(np.isfinite(tc)), 1.0, 1.0, 0.0, tc))
    legs = pd.DataFrame(rows, columns=["right", "instant", "m", "date_days", "present", "solved", "rt", "delta", "h", "tc"])
    t = costs.depth_table(legs)
    assert list(t.loc[t["cheapest"], "moneyness_pct"]) == [0.0], "the lowest MEAN TC (1.4) is the ATM row"
    assert abs(t.loc[t["moneyness_pct"] == 0.5, "tc_mean"].iloc[0] - 2.0) < 1e-12
    assert abs(t.loc[t["moneyness_pct"] == 0.5, "tc_median"].iloc[0] - 1.0) < 1e-12
    skewed = [1.0, 1.0, 4.0]
    row = t[t["moneyness_pct"] == 0.5].iloc[0]
    assert (row["tc_lo"], row["tc_hi"]) == costs.session_bootstrap(skewed, np.mean), "bootstrap of the MEAN TC"
    assert costs.session_bootstrap(skewed, np.mean) != costs.session_bootstrap(skewed, np.median)
    assert 1.0 <= row["tc_lo"] <= 2.0 <= row["tc_hi"] <= 4.0
    dead = t[t["moneyness_pct"] == 2.0].iloc[0]
    assert dead["cheapest"] == False and dead["n"] == 0 and math.isnan(dead["tc_mean"]) and math.isnan(dead["tc_lo"])   # noqa: E712
    two = pd.concat([legs, legs.assign(right="P", tc=legs["tc"] * 0.5)], ignore_index=True)
    t2 = costs.depth_table(two)
    assert t2.groupby("right")["cheapest"].sum().to_dict() == {"C": 1, "P": 1}, "one cheapest per (right, instant)"


def test_m3_depth_legs_delta_is_black_scholes_at_the_mid_implied_vol():
    """End to end through depth_legs: quotes priced by pipeline.options at sigma = 0.25, ATM, at 10:01 (359 minutes
    left) and 15:31 (29): the unit's delta must equal the Black-Scholes delta of that sigma. The exit spot differs
    from the entry spot, so a delta computed at the wrong S would move."""
    d, S, S_x, sigma = "2026-03-04", 500.0, 502.0, 0.25
    rows = []
    for mod, mins in ((601, 359), (931, 29)):
        for right in ("C", "P"):
            mid = options.price(S, 500.0, mins, sigma, right.lower())
            rows += [(d, mod, right, 500.0, mid - 0.01, mid + 0.01), (d, 955, right, 500.0, 1.99, 2.01)]
    q = canon(rows)
    S_of = lambda dd, mod: S_x if int(mod) == 955 else S                      # noqa: E731
    legs = costs.depth_legs(costs.QuoteBook(q, 300), S_of, [ndays(d)], costs.listed_strikes(q))
    for mod, mins, label in ((601, 359, "10:01"), (931, 29, "15:31")):
        T = mins / (365 * 24 * 60)
        for right, want in (("C", options.bs_call(S, 500.0, T, sigma)[1]), ("P", options.bs_put(S, 500.0, T, sigma)[1])):
            g = legs[(legs["instant"] == label) & (legs["right"] == right) & (legs["m"] == 0.0)].iloc[0]
            assert g["solved"] and abs(g["delta"] - want) < 1e-6, (label, right, g["delta"], want)
            mid_e = options.price(S, 500.0, mins, sigma, right.lower())
            h = 10.0 * ((2.0 - mid_e) - want * (S_x - S))              # hand formula: (mid_x - mid_e) - delta (S_x - S)
            assert abs(g["rt"] - 0.2) < 1e-6, "10 x ((ask - mid) at entry 0.01 + (mid - bid) at exit 0.01)"
            assert abs(g["h"] - h) < 1e-6, (label, right, g["h"], h)
            assert abs(g["tc"] - (0.2 - h) / abs(want)) < 1e-6, "TC = (RT - h) / |delta| with |delta| near 0.5, not 1"
    T = 359 / (365 * 24 * 60)
    for sigma_hi, solvable in ((4.5, True), (7.0, False)):                    # the bracket is [1e-4, 5.0]
        mid = options.price(S, 500.0, 359, sigma_hi, "c")
        got = costs.entry_delta(mid, S, 500.0, 359, "C")
        assert (abs(got - options.bs_call(S, 500.0, T, sigma_hi)[1]) < 1e-6) if solvable else math.isnan(got), (sigma_hi, got)


# ---------------------------------------------------------------------------------------------
# 10. M5: A43 at quotes
# ---------------------------------------------------------------------------------------------

# (right, strike) -> (bid_e, ask_e, bid_x, ask_x) at the 09:32 and 16:00 instants, dollars per share. The half-spreads
# differ from leg to leg on purpose, so a spread charged to the wrong leg or the wrong end changes the answer.
M5_BOOK = {
    ("C", 500.0): (2.40, 2.60, 1.10, 1.30), ("C", 503.0): (1.40, 1.60, 0.40, 0.60), ("C", 506.0): (0.85, 1.05, 0.30, 0.50),
    ("C", 507.0): (0.55, 0.65, 0.10, 0.20), ("C", 508.0): (0.45, 0.55, 0.05, 0.15), ("C", 510.0): (0.25, 0.35, 0.00, 0.05),
    ("P", 490.0): (0.20, 0.30, 0.00, 0.10), ("P", 495.0): (0.68, 0.92, 0.10, 0.34), ("P", 497.0): (1.30, 1.50, 0.20, 0.30),
    ("P", 500.0): (2.20, 2.50, 0.90, 1.20),
}
S1_STRIKES = {"short_call": ("C", 500.0), "short_put": ("P", 500.0), "long_call": ("C", 506.0), "long_put": ("P", 495.0)}
S3_STRIKES = {"short_call": ("C", 503.0), "short_put": ("P", 497.0), "long_call": ("C", 507.0), "long_put": ("P", 490.0)}


def _quotes_of(strikes):
    return {role: M5_BOOK[leg] for role, leg in strikes.items()}


# S1, by hand. credit = bid(500C) 2.40 + bid(500P) 2.20 - ask(506C) 1.05 - ask(495P) 0.92 = 2.63; the wider wing is
# max(506-500, 500-495) = 6, so max_loss = 3.37. gross = shorts (2.50-1.20) + (2.35-1.05) plus longs (0.40-0.95) +
# (0.22-0.80) = 1.30 + 1.30 - 0.55 - 0.58 = 1.47. cost = entry half-spreads 0.10+0.15+0.10+0.12 plus the same four
# at exit = 0.94, net = 0.53 (cross-check, sell at the bid and buy at the ask both ways: 1.10 + 1.00 - 0.75 - 0.82).
S1_HAND = dict(credit=2.63, wing_width=6.0, max_loss=3.37, gross=1.47, cost=0.94, net=0.53)
# S3, by hand (strikes 503C / 497P short, 507C / 490P long). credit = 1.40 + 1.30 - 0.65 - 0.30 = 1.75; wings 507-503 = 4
# and 497-490 = 7, so max_loss = 5.25. gross = (1.50-0.50) + (1.40-0.25) + (0.15-0.60) + (0.05-0.25) = 1.50.
# cost = entry 0.10+0.10+0.05+0.05 plus exit 0.10+0.05+0.05+0.05 = 0.55, net = 0.95
# (cross-check: 1.40-0.60 + 1.30-0.30 + 0.10-0.65 + 0.00-0.30 = 0.80 + 1.00 - 0.55 - 0.30).
S3_HAND = dict(credit=1.75, wing_width=7.0, max_loss=5.25, gross=1.50, cost=0.55, net=0.95)


def _assert_structure(got, want):
    for key, val in want.items():
        assert abs(got[key] - val) < 1e-9, f"{key}: {got[key]} != {val}"


def test_m5_price_structure_arithmetic():
    _assert_structure(costs.price_structure(_quotes_of(S1_STRIKES), S1_STRIKES), S1_HAND)
    _assert_structure(costs.price_structure(_quotes_of(S3_STRIKES), S3_STRIKES), S3_HAND)
    losing = _quotes_of(S1_STRIKES)
    losing["short_call"], losing["short_put"] = (2.40, 2.60, 3.10, 3.30), (2.20, 2.50, 2.90, 3.20)
    assert costs.price_structure(losing, S1_STRIKES)["gross"] < 0, "a short leg that rose from 2.50 to 3.20 loses"


def _m5_world(drop=(), edit=None, s=500.0):
    A = "2026-03-04"
    rows = []
    for (right, K), (be, ae, bx, ax) in M5_BOOK.items():
        if edit and (right, K) in edit:
            be, ae, bx, ax = edit[(right, K)]
        rows += [(A, 572, right, K, be, ae), (A, 960, right, K, bx, ax)]
    rows += [(A, 580, "C", 505, 1.50, 1.70), (A, 960, "C", 505, 0.20, 0.30)]     # decoy: first quoted at 09:40, after entry
    q = canon(rows)
    for right, K, mod in drop:
        q = q[~((q["is_put"] == int(right == "P")) & (q["strike"] == K) & (q["mod"] == mod))]
    S_of = lambda d, mod: s if int(mod) == 572 else float("nan")             # noqa: E731
    return q, S_of, ndays(A)


def test_m5_hand_built_days_through_sellvol_strike_rules():
    q, S_of, d = _m5_world()
    book, frames = costs.QuoteBook(q, 300), costs.day_frames(q, [d])
    trials = {t[0]: t for t in sellvol.TRIALS}
    assert costs.structure_strikes(frames[d], 500.0, 572, trials["S1"][2], trials["S1"][3]) == S1_STRIKES, \
        "the 505C decoy (first quote 09:40) must be rejected by the causal rule: 506C is the +1 % wing"
    assert costs.structure_strikes(frames[d], 500.0, 572, trials["S3"][2], trials["S3"][3]) == S3_STRIKES
    rows = costs.trackc_sessions(book, S_of, [d], frames)
    assert list(rows["structure"]) == ["S1", "S2", "S3"] and list(rows["status"]) == ["ok", "skipped", "ok"], \
        "S2 enters at 13:31 where this day has no underlying bar: skipped, S1 and S3 priced"
    _assert_structure(rows.iloc[0], S1_HAND)
    _assert_structure(rows.iloc[2], S3_HAND)
    table = costs.trackc_table(rows, 2)                                      # two window sessions, one priced per structure
    assert list(table["structure"]) == ["S1", "S2", "S3"] and list(table.columns) == costs.TRACKC_COLS
    assert list(table["entry_instant"]) == ["09:32", "13:31", "09:32"], "A43's bar-close minute m is the instant m + 1"
    assert set(table["exit_instant"]) == {"16:00"}
    assert list(table["n"]) == [1, 0, 1] and list(table["n_skipped"]) == [1, 2, 1] and set(table["n_sessions_window"]) == {2}
    s1 = table.iloc[0]
    assert abs(s1["mean_net_usd"] - 0.53) < 1e-9 and abs(s1["median_net_usd"] - 0.53) < 1e-9
    assert abs(s1["mean_pct_maxloss"] - 0.53 / 3.37 * 100) < 1e-9 and abs(s1["median_pct_maxloss"] - 0.53 / 3.37 * 100) < 1e-9
    assert abs(s1["breakeven_leg_rt_usd"] - 1.47 / 4) < 1e-9, "mean gross / 4 legs"
    assert s1["win_rate"] == 1.0 and abs(s1["worst_day_usd"] - 0.53) < 1e-9 and np.isnan(s1["p_boot_day"])
    assert s1["label"] == "UNDERPOWERED"
    assert abs(s1["mean_gross_usd"] - 1.47) < 1e-9 and abs(s1["mean_cost_usd"] - 0.94) < 1e-9
    assert abs(s1["mean_credit_usd"] - 2.63) < 1e-9 and abs(s1["mean_max_loss_usd"] - 3.37) < 1e-9
    s3 = table.iloc[2]
    assert abs(s3["mean_net_usd"] - 0.95) < 1e-9 and abs(s3["breakeven_leg_rt_usd"] - 1.50 / 4) < 1e-9
    s2 = table.iloc[1]
    assert s2["n"] == 0 and np.isnan(s2["mean_net_usd"]) and s2["label"] == "UNDERPOWERED"


def test_m5_skips_whole_structure_on_any_missing_leg_or_unsizable_loss():
    q, S_of, d = _m5_world(drop=[("P", 495.0, 960)])                         # S1's long put has no exit quote
    book, frames = costs.QuoteBook(q, 300), costs.day_frames(q, [d])
    rows = costs.trackc_sessions(book, S_of, [d], frames)
    assert list(rows["status"]) == ["skipped", "skipped", "ok"], "only the structure that uses the missing leg is skipped"
    q, S_of, d = _m5_world(drop=[("C", 500.0, 572)])                         # the short call has no entry quote at all
    rows = costs.trackc_sessions(costs.QuoteBook(q, 300), S_of, [d], costs.day_frames(q, [d]))
    assert rows.loc[rows["structure"] == "S1", "status"].iloc[0] == "skipped"
    # a quote 6 minutes before the entry instant is too old for the 5-minute book: the leg is missing, not filled
    q, S_of, d = _m5_world()
    q = q.assign(tsec=np.where((q["mod"] == 572) & (q["strike"] == 500.0) & (q["is_put"] == 0), q["tsec"] - 360, q["tsec"]),
                 mod=np.where((q["mod"] == 572) & (q["strike"] == 500.0) & (q["is_put"] == 0), 566, q["mod"]))
    rows = costs.trackc_sessions(costs.QuoteBook(q, 300), S_of, [d], costs.day_frames(q, [d]))
    assert rows.loc[rows["structure"] == "S1", "status"].iloc[0] == "skipped"
    rows = costs.trackc_sessions(costs.QuoteBook(q, 1800), S_of, [d], costs.day_frames(q, [d]))
    assert rows.loc[rows["structure"] == "S1", "status"].iloc[0] == "ok", "the 30-minute book accepts the 6-minute-old quote"
    # credit above the wider wing (max_loss <= 0) cannot be sized and is skipped, like A43's own anomaly rule
    q, S_of, d = _m5_world(edit={("C", 500.0): (5.00, 5.10, 1.10, 1.30), ("P", 500.0): (5.00, 5.10, 0.90, 1.20)})
    rows = costs.trackc_sessions(costs.QuoteBook(q, 300), S_of, [d], costs.day_frames(q, [d]))
    assert rows.loc[rows["structure"] == "S1", "status"].iloc[0] == "skipped", "credit 9.0 + > wing 6: max_loss <= 0"
    # a non-positive QUOTED credit with a positive max loss is kept and counted
    rows = pd.DataFrame([dict(structure="S1", date_days=ndays("2026-03-04") + i, status="ok", credit=c, max_loss=6.0 - c,
                              gross=0.2, cost=0.3, net=-0.1) for i, c in enumerate([-0.5, 0.0, 1.0])])
    t = costs.trackc_table(rows, 3)
    assert t.iloc[0]["n"] == 3 and t.iloc[0]["n_credit_nonpositive"] == 2


def test_m5_day_block_p_uses_session_blocks():
    from pipeline import stats
    n = 30
    days = [ndays("2026-03-02") + i for i in range(n)]
    net = np.array([0.4 + 0.01 * (i % 7) for i in range(n)])
    rows = pd.DataFrame([dict(structure="S1", date_days=days[i], status="ok", credit=2.0, max_loss=4.0, gross=net[i] + 0.2,
                              cost=0.2, net=net[i]) for i in range(n)])
    t = costs.trackc_table(rows, n).iloc[0]
    want = stats.one_sided_p(net, stats.day_blocks([pd.Timestamp(d * 86400, unit="s") for d in days]))
    assert np.isfinite(t["p_boot_day"]) and t["p_boot_day"] == want and t["p_boot_day"] < 0.05
    assert abs(t["mean_net_usd"] - net.mean()) < 1e-9 and abs(t["median_net_usd"] - np.median(net)) < 1e-9
    assert abs(t["worst_day_usd"] - net.min()) < 1e-9 and t["win_rate"] == 1.0
    assert abs(t["mean_pct_maxloss"] - (net / 4.0 * 100).mean()) < 1e-9
    assert abs(t["breakeven_leg_rt_usd"] - (net + 0.2).mean() / 4) < 1e-9
    neg = costs.trackc_table(rows.assign(net=-rows["net"]), n).iloc[0]
    assert neg["p_boot_day"] == 1.0 and neg["win_rate"] == 0.0, "one-sided: a negative mean gives p = 1"
    zero = costs.trackc_table(rows.assign(net=0.0), n).iloc[0]
    assert zero["win_rate"] == 0.0, "a day that nets exactly zero is not a win"


def test_m5_underpowered_below_200_sessions():
    def table(n):
        rows = pd.DataFrame([dict(structure="S1", date_days=20000 + i, status="ok", credit=2.0, max_loss=4.0, gross=0.5,
                                  cost=0.2, net=0.3) for i in range(n)])
        return costs.trackc_table(rows, n).iloc[0]
    assert table(199)["label"] == "UNDERPOWERED" and table(200)["label"] == "MEASURED"
    assert table(0)["label"] == "UNDERPOWERED" and table(0)["n"] == 0


def test_m5_follows_a43_tie_rule_not_m1():
    # S = 550: the +1 % wing target is 555.5, a tie between 555 and 556; the -1 % put target 544.5 ties 544/545. A43
    # (sellvol, ties toward the SMALLER strike) takes 555 and 544; M1's "away from spot" rule would take 556 and 544.
    day = pd.DataFrame({"strike": [549.0, 550.0, 551.0, 555.0, 556.0] + [544.0, 545.0, 549.0, 550.0, 551.0],
                        "right": ["C"] * 5 + ["P"] * 5, "mod": 500})
    st = costs.structure_strikes(day, 550.0, 572, 0.01, None)
    assert st == {"short_call": ("C", 550.0), "short_put": ("P", 550.0), "long_call": ("C", 555.0), "long_put": ("P", 544.0)}
    assert float(costs.nearest_away(np.array([555.0, 556.0]), 555.5, 1)) == 556.0, "M1's rule differs on the same tie"
    condor = costs.structure_strikes(day, 550.0, 572, 0.015, 0.005)           # S3: four independent targets
    assert condor == {"short_call": ("C", 551.0), "short_put": ("P", 549.0), "long_call": ("C", 556.0),
                      "long_put": ("P", 544.0)}, condor
    assert costs.structure_strikes(day[day["right"] == "C"], 550.0, 572, 0.01, None) is None, "no puts listed: unresolvable"
    late = day.assign(mod=np.where(day["strike"] == 555.0, 600, 500))
    assert costs.structure_strikes(late, 550.0, 572, 0.01, None)["long_call"] == ("C", 556.0), "555 first quotes after entry"


# ---------------------------------------------------------------------------------------------
# A51a: manifest-excluded sessions
# ---------------------------------------------------------------------------------------------

def test_vendor_excluded_sessions_leave_every_statistic():
    wild, absent, ctx = "2026-03-11", "2026-03-12", "2025-12-10"
    dates = D1 + [wild, absent, ctx]
    base = dict(BASE1, **{wild: 507.0, absent: 508.0, ctx: 480.0})
    with tmpdir() as tmp:
        w = make_world(os.path.join(tmp, "ext"), dates, lambda d: base[d], hs_fn=hs_designed,
                       price_scale={wild: 100.0, ctx: 100.0}, no_quote_dates=(absent,))
        q, _man, trades = load(w)
        meta = dict(vendor="v", schema="s", ts_semantics="t", rows_on_change=False)
        excl = frozenset(ndays(x) for x in (wild, absent, ctx, "2026-03-14", "2025-11-01"))   # last two: not sessions
        res = costs.measure(q, w.frame, costs.Manifest(excluded=excl, **meta), trades)
        dec = res["decision"].iloc[0]
        assert dec["n_sessions_window"] == 5 and dec["n_sessions"] == 5 and dec["n_sessions_excluded_vendor"] == 2, \
            "the count is the excluded dates that would otherwise be DECISION sessions (not the weekend, not 2025)"
        assert dec["n_leg_slots"] == 50 and dec["n_legs_missing"] == 0 and dec["label"] == "COMPLETE"
        assert abs(dec["cm"] - EXPECTED_CM) < 1e-9 and abs(dec["cm_intraday"] - EXPECTED_CM_INTRADAY) < 1e-9
        assert all(r["pass"] for r in res["validation"]), res["validation"]
        assert set(res["surface"]["window"]) == {"DECISION"}, "the excluded 2025Q4 context session leaves M1 as well"
        assert (res["surface"]["n_sessions"] == 5).all() and list(res["sessions"]["date"]) == D1
        assert (res["depth"]["n_sessions"] == 5).all() and (res["trackc"]["n_sessions_window"] == 5).all()
        # the same files with an empty exclusion list: the absent day is 10 missing legs, the x100 day is a session
        res0 = costs.measure(q, w.frame, costs.Manifest(excluded=frozenset(), **meta), trades)
        dec0 = res0["decision"].iloc[0]
        assert dec0["n_sessions_window"] == 7 and dec0["n_sessions_excluded_vendor"] == 0
        assert dec0["n_leg_slots"] == 70 and dec0["n_legs_missing"] == 10 and dec0["n_sessions"] == 6
        assert abs(dec0["cm"] - 1.20) < 1e-6, "median of .75 .95 1.05 1.35 2.65 and the wild session's 10.0"
        assert "2025Q4" in set(res0["surface"]["window"]) and (res0["surface"]["n_sessions"] == 7).any()
        assert (res0["depth"]["n_sessions"] == 7).all() and (res0["trackc"]["n_sessions_window"] == 7).all()
        # end to end: the manifest's list reaches the unit and the count lands in costs_decision.csv
        with open(os.path.join(w.inp, "quotes_manifest.json")) as f:
            man = json.load(f)
        man["excluded_sessions"] = [wild, absent, ctx]
        with open(os.path.join(w.inp, "quotes_manifest.json"), "w") as f:
            json.dump(man, f)
        out = os.path.join(tmp, "out")
        code, calls = run_unit(w, out)
        assert code == 0 and len(calls) == 1
        d = read(out, "costs_decision.csv").iloc[0]
        assert d["n_sessions_excluded_vendor"] == 2 and d["n_sessions_window"] == 5 and abs(d["cm"] - EXPECTED_CM) < 1e-6
        assert read(out, "costs_validation.csv")["n"].tolist()[1] == 19500, "V2 scores the 5 decision sessions' bars only"


def test_vendor_excluded_sessions_leave_v1():
    """V1 pools legs, so a single bad session cannot move it; here two of three sessions carry x100 prices."""
    dates = ["2026-03-04", "2026-03-05", "2026-03-06"]
    with tmpdir() as tmp:
        w = make_world(os.path.join(tmp, "ext"), dates, lambda d: 500.0 + dates.index(d), trades=False,
                       price_scale={dates[1]: 100.0, dates[2]: 100.0})
        q, _man, _ = load(w)
        meta = dict(vendor="v", schema="s", ts_semantics="t", rows_on_change=False)
        good = costs.measure(q, w.frame, costs.Manifest(excluded=frozenset(ndays(x) for x in dates[1:]), **meta), [])
        assert good["validation"][0]["pass"] and good["decision"].iloc[0]["n_sessions"] == 1
        bad = costs.measure(q, w.frame, costs.Manifest(excluded=frozenset(), **meta), [])
        assert not bad["validation"][0]["pass"], "without the exclusion V1 sees the x100 sessions"


# ---------------------------------------------------------------------------------------------
# Window, M1 cells, strikes, bootstrap, bands, determinism
# ---------------------------------------------------------------------------------------------

def test_context_sessions_never_enter_cm_but_appear_in_m1_by_quarter():
    ctx = "2025-12-10"
    dates = D1 + [ctx]
    base = dict(BASE1, **{ctx: 480.0})

    def hs(date, right, K, mods):                       # the context session is wildly wide: it would move Cm
        return hs_designed(date, right, K, mods) if date != ctx else np.full(len(mods), 3.0)
    with tmpdir() as tmp:
        w = make_world(os.path.join(tmp, "ext"), dates, lambda d: base[d], hs_fn=hs)
        out = os.path.join(tmp, "out")
        code, _ = run_unit(w, out)
        assert code == 0
        dec = read(out, "costs_decision.csv").iloc[0]
        assert abs(dec["cm"] - EXPECTED_CM) < 1e-6 and dec["n_sessions"] == 5 and dec["n_sessions_window"] == 5
        assert list(read(out, "costs_sessions.csv")["date"]) == D1
        surf = read(out, "costs_surface.csv")
        assert set(surf["window"]) == {"DECISION", "2025Q4"}
        q4 = surf[surf["window"] == "2025Q4"]
        assert (q4["n_sessions"] == 1).all() and q4["median"].max() > 50, "context spreads are reported, wide as they are"
        assert (surf[surf["window"] == "DECISION"]["n_sessions"] == 5).all()
        assert list(surf["window"].drop_duplicates()) == ["DECISION", "2025Q4"], "DECISION first, then quarters"
        assert read(out, "costs_validation.csv")["n"][1] == 19500, \
            "V2 scores the 5 decision sessions' bars; the context session's 3,900 bars are in the shard but not scored"
    # the window is inclusive at both ends
    groups = costs.session_groups({ndays("2026-03-01"), ndays("2026-03-02"), ndays("2026-09-11"), ndays("2026-09-12")}, set())
    assert groups[0][1] == [ndays("2026-03-02"), ndays("2026-09-11")]
    assert dict(groups)["2026Q1"] == [ndays("2026-03-01")] and dict(groups)["2026Q3"] == [ndays("2026-09-12")]


def _cell_legs(spreads_usd, window="DECISION", instant="10:01", right="C", m=1.0):
    rows = []
    for i, s in enumerate(spreads_usd):
        bid, ask = (np.nan, np.nan) if s is None else (10.0 - s / 2, 10.0 + s / 2)
        rows.append((window, i, instant, costs.MOD[instant], right, m, 500.0, 495.0, bid, ask))
    return pd.DataFrame(rows, columns=["window", "date_days", "instant", "mod", "right", "m", "S", "K", "bid", "ask"])


def test_m1_cell_r7_fields_by_hand():
    legs = _cell_legs([0.01, 0.01, 0.05, 0.10, 0.00, -0.02, None])      # one-cent x2, wide x2, locked, crossed, missing
    t = costs.surface_table(legs)
    assert len(t) == 1
    r = t.iloc[0]
    # SPX points x10: [0.1, 0.1, 0.5, 1.0, 0.0, -0.2] -> sorted -0.2 0.0 0.1 0.1 0.5 1.0
    assert (r["n_sessions"], r["n"]) == (7, 6) and abs(r["missing_share"] - 1 / 7) < 1e-12
    assert abs(r["min"] - (-0.2)) < 1e-9 and abs(r["max"] - 1.0) < 1e-9
    assert abs(r["median"] - 0.1) < 1e-9 and abs(r["mean"] - 0.25) < 1e-9
    assert abs(r["p10"] - (-0.1)) < 1e-9 and abs(r["p90"] - 0.75) < 1e-9          # np.percentile, linear
    assert abs(r["share_one_cent"] - 4 / 6) < 1e-12, "spread <= $0.01: the two one-cent, the locked and the crossed one"
    assert abs(r["share_locked_crossed"] - 2 / 6) < 1e-12, "ask <= bid: locked and crossed"
    assert abs(r["median_usd"] - 0.01) < 1e-9 and abs(r["mean_usd"] - 0.025) < 1e-9
    assert list(t.columns) == costs.SURFACE_COLS
    # ordering: DECISION before quarters, instants chronological, calls before puts, moneyness ascending
    mixed = pd.concat([_cell_legs([0.02], window="2025Q4"), _cell_legs([0.02], right="P", m=2.0),
                       _cell_legs([0.02], instant="09:32"), _cell_legs([0.02], m=-0.5), _cell_legs([0.02])])
    order = costs.surface_table(mixed)[["window", "instant", "right", "moneyness_pct"]].values.tolist()
    assert order == [["DECISION", "09:32", "C", 1.0], ["DECISION", "10:01", "C", -0.5], ["DECISION", "10:01", "C", 1.0],
                     ["DECISION", "10:01", "P", 2.0], ["2025Q4", "10:01", "C", 1.0]], order


def test_m1_strike_rule_nearest_listed_ties_away_from_spot():
    ks = np.arange(540.0, 561.0)
    d = ndays("2026-03-04")

    def strikes(S, moneyness, listed=ks):
        both = {(d, 0): listed, (d, 1): listed}
        t = costs.strike_table([d], ["10:01"], costs.RIGHTS, moneyness, lambda *_: S, both)
        return {(r["right"], r["m"]): r["K"] for _, r in t.iterrows()}
    k = strikes(550.0, [1.0, -1.0, 0.5, 0.0])
    assert k[("C", 1.0)] == 544.0, "ITM call target 544.5: tie -> deeper ITM (lower)"
    assert k[("P", 1.0)] == 556.0, "ITM put target 555.5: tie -> deeper ITM (higher)"
    assert k[("C", -1.0)] == 556.0, "OTM call target 555.5: tie -> further OTM (higher)"
    assert k[("P", -1.0)] == 544.0, "OTM put target 544.5: tie -> further OTM (lower)"
    assert k[("C", 0.5)] == 547.0 and k[("P", 0.5)] == 553.0 and k[("C", 0.0)] == 550.0   # 547.25 -> 547, 552.75 -> 553
    k = strikes(550.5, [0.0])
    assert k[("C", 0.0)] == 550.0 and k[("P", 0.0)] == 551.0, "ATM tie: ITM side (call lower, put higher)"
    # exact ties whose float target is a hair off (500 x 1.005 = 502.49999999999994): still ties, still away from spot
    k = strikes(500.0, [0.5, 1.5, -0.5, -1.5], listed=np.arange(480.0, 521.0))
    assert k[("P", 0.5)] == 503.0 and k[("P", 1.5)] == 508.0, "ITM put targets 502.5 / 507.5: deeper ITM = higher"
    assert k[("C", -0.5)] == 503.0 and k[("C", -1.5)] == 508.0, "OTM call targets 502.5 / 507.5: further OTM = higher"
    assert k[("C", 0.5)] == 497.0 and k[("P", -0.5)] == 497.0, "ITM call / OTM put target 497.5: lower"
    k = strikes(550.2, [0.0])
    assert k[("C", 0.0)] == 550.0 and k[("P", 0.0)] == 550.0, "no tie: simply the nearest"
    assert strikes(500.0, [2.5])[("C", 2.5)] == 540.0, "a target below the listed range takes the lowest listed strike"
    assert strikes(600.0, [-2.5])[("C", -2.5)] == 560.0
    both = {(d, 0): ks, (d, 1): ks}
    t = costs.strike_table([d], ["10:01"], ["C"], [0.0], lambda *_: float("nan"), both)
    assert t["K"].isna().all(), "no S -> no strike"
    t = costs.strike_table([d + 1], ["10:01"], ["C"], [0.0], lambda *_: 550.0, both)
    assert t["K"].isna().all(), "no listed strikes that session -> missing"


def test_bootstrap_is_seeded_and_reproducible():
    v = np.array([0.4, 0.5, 0.9, 1.3, 2.0, 0.7, 0.6])
    rng = np.random.default_rng(11)
    idx = rng.integers(0, len(v), size=(2000, len(v)))
    lo, hi = np.percentile(np.median(v[idx], axis=1), [5, 95])
    got = costs.session_bootstrap(v, np.median)
    assert got == (float(lo), float(hi)), "seed 11, 2000 resamples of the sessions, 5th and 95th percentile"
    assert costs.session_bootstrap(v, np.median) == got
    assert costs.session_bootstrap(v, np.mean) != got
    # The median of 7 values is discrete, so its 5th/10th (and 90th/95th) percentiles can coincide and cannot tell a
    # 90 % interval from an 80 % one. The mean's resampled distribution is continuous: pin the interval there too.
    means = v[idx].mean(axis=1)
    assert len({float(np.percentile(means, q)) for q in (5, 10, 90, 95)}) == 4, "premise: four distinct percentiles"
    mean_lo, mean_hi = np.percentile(means, [5, 95])
    assert costs.session_bootstrap(v, np.mean) == (float(mean_lo), float(mean_hi)), "5th and 95th percentile of the means"
    assert all(math.isnan(x) for x in costs.session_bootstrap([], np.median))
    assert costs.session_bootstrap([0.0, 0.0, 0.0], np.median) == (0.0, 0.0)
    assert costs.BOOT_SEED == 11 and costs.N_BOOT == 2000


def test_outcome_bands_use_a51_boundaries():
    assert costs.band_of(1.0) == ">=1.0" and costs.band_of(2.5) == ">=1.0"
    assert costs.band_of(0.999999) == "[0.5,1.0)" and costs.band_of(0.5) == "[0.5,1.0)"
    assert costs.band_of(0.499999) == "<0.5" and costs.band_of(0.0) == "<0.5"
    assert costs.band_of(float("nan")) == "n/a"
    assert "not conservative" in costs.MEANING[">=1.0"] and "conservative by up to half a point" in costs.MEANING["[0.5,1.0)"]
    assert "measured cost instead of 1.0" in costs.MEANING["<0.5"]


def test_crossed_quotes_are_flagged_at_entry_or_exit_and_not_dropped():
    """A51 charges what the quotes say: a crossed quote is not excluded from Cm, it is reported (n_legs_locked_crossed,
    share_legs_locked_crossed). Hand case, S = 500.4 so the A8 strikes are 490 (call) and 511 (put), one entry instant:
    call entry crossed (bid 10.60 > ask 10.50), exit fine (10.40 / 10.60); put entry fine (10.40 / 10.60), exit crossed
    (bid 10.70 > ask 10.50). RT_call = 10 [(10.50 - 10.55) + (10.50 - 10.40)] = 0.5, RT_put = 10 [(10.60 - 10.50) +
    (10.60 - 10.70)] = 0.0; entry spreads x10: -1.0 and 2.0."""
    d = "2026-03-04"
    q = canon([(d, 601, "C", 490, 10.60, 10.50), (d, 955, "C", 490, 10.40, 10.60),
               (d, 601, "P", 511, 10.40, 10.60), (d, 955, "P", 511, 10.70, 10.50)])
    S_of = lambda dd, mod: 500.4 if int(mod) == 601 else float("nan")        # noqa: E731
    legs = costs.decision_legs(costs.QuoteBook(q, 300), S_of, [ndays(d)])
    ok = legs[legs["present"]]
    assert len(ok) == 2 and list(ok["right"]) == ["C", "P"] and list(ok["K"]) == [490.0, 511.0]
    assert np.allclose(ok["rt"], [0.5, 0.0], atol=1e-9) and np.allclose(ok["spread_e"], [-1.0, 2.0], atol=1e-9)
    assert list(ok["crossed"]) == [True, True], "crossed at entry (call) and crossed at exit (put) are both flagged"
    assert not legs[~legs["present"]]["crossed"].any(), "missing legs have no quotes to be crossed"
    sess = costs.session_table(legs, [ndays(d)]).iloc[0]
    assert sess["n_legs"] == 2 and sess["n_legs_locked_crossed"] == 2
    assert abs(sess["c_s"] - 0.25) < 1e-9 and abs(sess["c_intraday"] - 0.5) < 1e-9


def test_decision_row_band_and_meaning_text():
    man = costs.Manifest("v", "s", "t", False, frozenset())

    def row(cs, present=True, n_window=None):
        n = len(cs)
        sess = pd.DataFrame({"c_s": cs, "c_intraday": [x * 2 for x in cs]})
        legs = pd.DataFrame({"present": [present] * (10 * n), "crossed": [False] * (10 * n)})
        return costs.decision_row(legs, sess, n if n_window is None else n_window, 0, man)
    for cs, band, text in (([1.0, 1.0, 1.0], ">=1.0", "not conservative"), ([0.5, 0.5, 0.5], "[0.5,1.0)", "up to half a point"),
                           ([0.49, 0.49, 0.49], "<0.5", "measured cost instead of 1.0")):
        r = row(cs)
        assert r["band"] == band and text in r["meaning"] and r["label"] == "COMPLETE", (cs, r["band"], r["meaning"])
        assert r["cm"] == cs[0] and r["cm_intraday"] == 2 * cs[0] and r["n_sessions"] == 3
    r = row([0.6, 0.6, 0.6], n_window=5)                       # 30 of 50 slots present: 40 % missing
    assert r["label"] == "INCOMPLETE" and r["meaning"] == costs.MEANING_INCOMPLETE and r["n_legs_missing"] == 20
    assert abs(r["missing_share"] - 0.4) < 1e-12 and r["quote_max_age_min"] == 5.0 and r["rows_on_change"] is False
    assert costs.decision_row(pd.DataFrame({"present": [], "crossed": []}), pd.DataFrame({"c_s": [], "c_intraday": []}),
                              0, 0, man)["label"] == "INCOMPLETE", "no window sessions at all is incomplete, not complete"


def test_outputs_are_deterministic_and_headers_match_the_constants():
    with tmpdir() as tmp:
        w = world1(os.path.join(tmp, "ext"))
        a, b = os.path.join(tmp, "a"), os.path.join(tmp, "b")
        assert run_unit(w, a)[0] == 0 and run_unit(w, b)[0] == 0
        for name in SEVEN:
            ba, bb = open(os.path.join(a, name), "rb").read(), open(os.path.join(b, name), "rb").read()
            assert ba == bb, f"{name}: two runs differ"
            assert open(os.path.join(a, name)).readline().strip().split(",") == SEVEN_COLS[name], name
        surf = read(a, "costs_surface.csv")
        assert len(surf) == 9 * 2 * 9 and list(surf["instant"].drop_duplicates()) == costs.INSTANT_LABELS
        assert read(a, "costs_trackc.csv")["structure"].tolist() == ["S1", "S2", "S3"]
        assert sorted(os.listdir(a)) == SEVEN
        for name in SEVEN:
            text = open(os.path.join(a, name)).read()
            assert re.search(r"\d\.\d{7,}", text) is None, f"{name}: floats are written with %.6f"
            assert "e+" not in text and "nan" not in text.lower(), f"{name}: NaN is an empty field"


def test_trade_shards_are_required_for_v2():
    with tmpdir() as tmp:
        w = world1(os.path.join(tmp, "ext"), trades=False)
        q, man, trades = load(w)
        assert trades == []
        res = costs.measure(q, w.frame, man, trades)
        v2 = res["validation"][1]
        assert v2["check"] == "V2" and v2["pass"] is False and "trade shard" in v2["detail"]


def test_listed_strikes_are_per_right_and_per_session():
    d, e = "2026-03-04", "2026-03-05"
    q = canon([(d, 601, "C", 500, 1, 1.1), (d, 602, "C", 501, 1, 1.1), (d, 601, "C", 500, 1, 1.1), (d, 601, "P", 499, 1, 1.1),
               (e, 601, "C", 700, 1, 1.1)])
    listed = costs.listed_strikes(q)
    assert listed[(ndays(d), 0)].tolist() == [500.0, 501.0], "calls of the session: sorted, unique"
    assert listed[(ndays(d), 1)].tolist() == [499.0], "the put strikes are not mixed with the call strikes"
    assert listed[(ndays(e), 0)].tolist() == [700.0] and (ndays(e), 1) not in listed


def test_no_decision_window_sessions_fails_visibly():
    """Shards that hold only sessions outside 2026-03-02..2026-09-11 (and a frame without window sessions): nothing to
    decide on, so V1, V2 and V3 fail, nothing is published, and the unit exits 2 instead of crashing."""
    dates = ["2025-12-08", "2025-12-09"]
    with tmpdir() as tmp:
        w = make_world(os.path.join(tmp, "ext"), dates, lambda d: 500.0)
        out = os.path.join(tmp, "out")
        code, calls = run_unit(w, out)
        assert code == 2 and calls == []
        val = read(out, "costs_validation.csv")
        assert list(val["check"]) == ["V1", "V2", "V3"] and list(val["pass"]) == [False, False, False], val
        assert "no trade bars" in val["detail"][1]
        assert val["n"][2] == 0 and val["n"][0] == 0, "no decision legs, no decision slots"
        assert os.path.exists(os.path.join(out, "costs_decision.csv.error"))
        for name in SEVEN:
            if name not in ("costs_decision.csv", "costs_validation.csv"):
                assert len(read(out, name)) == 0, name


def test_excluded_or_quoteless_window_and_empty_shards_fail_visibly():
    with tmpdir() as tmp:
        # (a) the manifest excludes every window session: nothing is left to decide on
        w = world1(os.path.join(tmp, "a"), manifest={"excluded_sessions": D1})
        out = os.path.join(tmp, "out_a")
        code, calls = run_unit(w, out)
        val = read(out, "costs_validation.csv")
        assert code == 2 and calls == [] and list(val["pass"]) == [False, False, False] and list(val["n"]) == [0, 0, 0]
        # (b) window sessions are in the frame but the quote file only holds a context session: every leg is missing
        dates = D1 + ["2025-12-08"]
        w = make_world(os.path.join(tmp, "b"), dates, lambda d: 500.0 + dates.index(d), no_quote_dates=tuple(D1))
        out = os.path.join(tmp, "out_b")
        code, calls = run_unit(w, out)
        val = read(out, "costs_validation.csv")
        assert code == 2 and calls == [] and list(val["pass"]) == [False, False, False]
        assert val["n"][2] == 50 and val["value_1"][2] == 1.0, "50 decision legs, all of them missing"
        # (c) a shard with a header and no rows: an input error, visible, nothing published
        w = world1(os.path.join(tmp, "c"))
        for name in os.listdir(w.inp):
            if name.startswith("spy_0dte_quotes"):
                import gzip
                with gzip.open(os.path.join(w.inp, name), "wt") as f:
                    f.write(",".join(costs.QUOTE_FILE_COLS) + "\n")
        out = os.path.join(tmp, "out_c")
        code, calls = run_unit(w, out)
        assert code == 2 and calls == []
        assert "no usable rows" in open(os.path.join(out, "costs_decision.csv.error")).read()
        for name in SEVEN:
            if name != "costs_decision.csv":
                assert len(read(out, name)) == 0, name


def test_a51_constants_are_the_registered_ones():
    assert costs.INSTANT_LABELS == ["09:32", "10:01", "11:01", "13:01", "13:31", "15:01", "15:31", "15:55", "16:00"]
    assert costs.ENTRY_LABELS == ["10:01", "11:01", "13:01", "15:01", "15:31"] and costs.EXIT_LABEL == "15:55"
    assert [costs.MOD[l] for l in costs.INSTANT_LABELS] == INSTANT_MODS
    assert costs.M1_MONEYNESS == [-1.5, -1.0, -0.5, 0.0, 0.5, 1.0, 1.5, 2.0, 2.5]
    assert costs.DEPTH_MONEYNESS == [0.0, 0.5, 1.0, 1.5, 2.0, 2.5]
    assert costs.WINDOW_TEXT == "2026-03-02..2026-09-11" and costs.WINDOW_DAYS == (ndays("2026-03-02"), ndays("2026-09-11"))
    assert costs.MAX_AGE_S == 300 and costs.MAX_AGE_ON_CHANGE_S == 1800 and costs.MISSING_LIMIT == 0.20
    assert costs.SPX_PER_SPY == 10.0 and costs.V1_RANGE == (-0.10, 0.25) and costs.V2_MIN_SHARE == 0.25
    assert costs.IV_BOUNDS == (1e-4, 5.0) and costs.DELTA_ONE_TOL == 0.005 and costs.N_MIN_TRACKC == 200
    assert [t[0] for t in sellvol.TRIALS] == ["S1", "S2", "S3"] and [t[1] for t in sellvol.TRIALS] == [571, 810, 571]


MUTATION_PROOF = """Mutation proof (2026-10-02). costs.py was copied into a sandbox and 125 one-line mutants were applied one at a time,
each run against this file with `pytest -x`: 124 killed, 1 survivor that is equivalent by algebra (RT-MID-AT-EXIT:
(ask - mid) == (mid - bid) when mid = (bid + ask) / 2). A first pass of 74 mutants against an earlier revision of this suite
found two real gaps (V2 scoring context sessions went unnoticed; TC was never checked at a delta other than +-1) and one
redundant line (the manifest row filter, removed). The final pass found one more gap: the median of 7 resampled values is
discrete, so its 5th/10th and 90th/95th percentiles can coincide and a 90 % interval could not be told from an 80 % one; the
mean-bootstrap pin in test_bootstrap_is_seeded_and_reproducible closes it (BOOT-PCT re-run: killed). Separately, the
degenerate-input tests found a real bug (an empty decision window crashed with a TypeError before the validation rows were
written), fixed in costs.py. Mutant classes killed: RT with the full entry spread or without the x10; Cm as a mean or a leg
median; c_s as a leg median; Cm_intraday as a mean; A8 toward spot (call, put, both); exit at 16:00; look-ahead (ts >= t);
staleness limit exclusive, in minutes mistaken for seconds, or manifest flag ignored (both directions); empty-book rows dropped
or half-priced; vendor-excluded sessions kept in either universe or miscounted; fixed-offset DST (instants and stamps); S read
from the wrong bar or unscaled; ties toward spot, ATM to the OTM side, tolerance 0; window edges, context in Cm, quarter label;
V1 bounds, depth, mean, put intrinsic, NaN pass, window restriction; V2 swapped, strict, floors, pad, denominator, session
restriction; V3 inverted; coverage >=; M3 delta tolerance, bracket, delta at the exit spot or exit mid, hedge sign, TC without
|delta| or without the division, solved-count, cheapest by max or by median, bootstrap of the median; M5 sign, credit, entry or
exit only cost, narrower wing, non-causal strikes, bar-start entry, 15:55 exit, breakeven, % denominator, UNDERPOWERED edge,
win-rate edge, worst day, unsizable loss, missing leg, S3 leg directions, day-frame rights; R7 fields; bootstrap seed, size and
percentiles; re-read gating, arguments and columns; float format; sort order; manifest checks; duplicate rows; contract and
session isolation; the skip path building the frame."""


# ---------------------------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------------------------

def main():
    ok = True
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"[PASS] {name}")
            except Exception as e:                                   # noqa: BLE001 - report every failure, then exit 1
                ok = False
                frame = traceback.extract_tb(e.__traceback__)[-1]
                print(f"[FAIL] {name}: {type(e).__name__}: {e} (line {frame.lineno}: {frame.line})")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
