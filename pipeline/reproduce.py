"""Phase 2 gate (c): reproduce both threads' headline numbers on the re-fetched data BEFORE any
new signal runs (ACCEPTANCE A22, A30). Prints one PASS/FAIL line per target and never touches
research/ (A33).

Thread B (RESULTS_PART10 / CLAUDE_original.md:219-223):
  (c1) DATA IDENTITY, Thread B's own conventions (detected open + offsets, bar-close fill,
       session = [open, open+390), month blocks, cost 100*0.33/2100, one-sided p):
         discovery histdata 2010-2018, VIX>17.06 & |move|>0.665%: n=337 +0.0645% 58.5% SR 2.50 p 0.0003
         LEGACY holdout: Oanda 2019-01→2020-05 on NAIVE UTC stamps with ONE detected open
         (step17_intramom.py:34-42):                              n=85  +0.0975% 54.1% SR 1.67 p 0.135
         unconditional rest-of-day, discovery:                    net -0.0063%, R^2 2.3%
  (c2) CORRECTED holdout on America/New_York sessions — the reference row downstream.
Thread A (ASSESSMENT_iteration22, HANDOFF.md:157-162), Oanda 2005-2020, train <2013 / test >=2013:
  HARD: trade counts within ±10% of 516 big-down puts, 473 big-up calls, 1,030 gap-up calls;
        underlying win rate within 1 point of the published option win rates (52.7 / 53.1).
  SOFT: TEST mean within 0.3 percentage points of premium at k=1.0, 2% ITM unrounded, r=0,
        quoted spread 1.0 pt, Thread A's inferred convention (ask entry, intrinsic settlement);
        the half-on-exit alternative is printed beside it.
Also: Thread A's mh.sanity() random-walk test and the clock-observability checks.
"""
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from pipeline import options, sessions, signals, stats

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "research" / "thread_A_multisleeve"))
COST_B = 100 * 0.33 / 2100          # Thread B's constant, used only to reproduce Thread B


def _threadB_days(raw, om):
    d = raw[(raw["mod"] >= om) & (raw["mod"] < om + 390)].copy()

    def px_at(m):
        return d[(d["mod"] <= m) & (d["mod"] >= m - 5)].groupby("date")["close"].last()
    out = pd.DataFrame({"prev_close": d.groupby("date")["close"].last().shift(1),
                        "p_1030": px_at(om + 30), "p_1500": px_at(om + 330), "p_1530": px_at(om + 360),
                        "close": d.groupby("date")["close"].last(), "bars": d.groupby("date").size()})
    out = out[out["bars"] > 300].dropna()
    out["r1"] = 100 * (out["p_1030"] / out["prev_close"] - 1)
    out["r12"] = 100 * (out["p_1530"] / out["p_1500"] - 1)
    out["r_rest"] = 100 * (out["p_1530"] / out["prev_close"] - 1)
    out["r13"] = 100 * (out["close"] / out["p_1530"] - 1)
    return out


def _threadB_eval(x, sig, blocks="month"):
    r = np.sign(x[sig]) * x["r13"]
    net = r - COST_B
    b = stats.month_blocks(x.index) if blocks == "month" else pd.to_datetime(x.index).astype(str).to_numpy()
    p = stats.one_sided_p(r.to_numpy(), b)
    corr = np.corrcoef(x[sig], x["r13"])[0, 1] if len(x) > 2 else np.nan
    return dict(n=len(x), net=net.mean(), win=100 * (r > 0).mean(), sr=net.mean() / net.std() * np.sqrt(252), p=p, r2=100 * corr ** 2)


def _vix_asof(idx, vix):
    return pd.merge_asof(pd.DataFrame({"date": pd.to_datetime(idx)}), vix[["date", "close"]].rename(columns={"close": "v"}),
                         on="date", allow_exact_matches=False)["v"].to_numpy()


def thread_b(vix):
    rows = []
    raw = sessions._load("histdata", "data/raw/histdata_SPXUSD.parquet")
    raw["mod"] = raw["ts_ny"].dt.hour * 60 + raw["ts_ny"].dt.minute
    raw["date"] = raw["ts_ny"].dt.tz_localize(None).dt.normalize()
    raw = raw[raw["ts_ny"].dt.dayofweek < 5]
    om = sessions.detect_open(raw)
    A = _threadB_days(raw, om)
    A["vix"] = _vix_asof(A.index, vix)
    f = A[(A["vix"] > 17.06) & (A["r_rest"].abs() > 0.665)]
    rows.append(("c1 B discovery, histdata 2010-18, B's conventions (open %02d:%02d)" % (om // 60, om % 60),
                 _threadB_eval(f, "r_rest"), dict(n=337, net=0.0645, win=58.5, sr=2.50, p=0.0003),
                 lambda g, t: abs(g["n"] - t["n"]) <= 2 and abs(g["net"] - t["net"]) < 0.002 and abs(g["win"] - t["win"]) < 0.5 and abs(g["sr"] - t["sr"]) < 0.05))
    rows.append(("c1 B discovery unconditional rest-of-day", _threadB_eval(A, "r_rest"), dict(net=-0.0063, r2=2.3),
                 lambda g, t: abs(g["net"] - t["net"]) < 0.003))
    # LEGACY holdout: naive UTC stamps, one detected open by volume (step17.half_hours_oanda)
    o = pd.read_parquet("data/raw/oanda_SPX500_USD.parquet")
    o = o[o["ts_utc"] >= "2019-01-01"].copy()
    o["ts"] = o["ts_utc"].dt.tz_localize(None)
    o["mod"] = o["ts"].dt.hour * 60 + o["ts"].dt.minute
    o["date"] = o["ts"].dt.normalize()
    om_utc = int(o.groupby("mod")["volume"].mean().rolling(5, center=True).mean().diff(5).idxmax())
    L = _threadB_days(o, om_utc)
    v = vix.set_index(vix["date"].dt.normalize())["close"]
    L["vix"] = v.reindex(L.index).shift(1).to_numpy()          # step17:97 row shift
    fl = L[(L["vix"] > 17.06) & (L["r_rest"].abs() > 0.665)]
    rows.append(("c1 B holdout LEGACY (naive UTC, one open %02d:%02d UTC)" % (om_utc // 60, om_utc % 60),
                 _threadB_eval(fl, "r_rest"), dict(n=85, net=0.0975, win=54.1, sr=1.67, p=0.135),
                 lambda g, t: g["n"] == t["n"] and abs(g["net"] - t["net"]) < 0.001 and abs(g["sr"] - t["sr"]) < 0.02))
    # CORRECTED holdout: America/New_York sessions, B's offsets from the detected NY open, day blocks (17 months < 20)
    raw2 = sessions._load("oanda", "data/raw/oanda_SPX500_USD.parquet")
    raw2["mod"] = raw2["ts_ny"].dt.hour * 60 + raw2["ts_ny"].dt.minute
    raw2["date"] = raw2["ts_ny"].dt.tz_localize(None).dt.normalize()
    raw2 = raw2[(raw2["ts_ny"].dt.dayofweek < 5) & (raw2["date"] >= "2019-01-01")]
    om2 = int(raw2.groupby("mod")["volume"].mean().rolling(5, center=True).mean().diff(5).idxmax())
    C = _threadB_days(raw2, om2)
    C["vix"] = _vix_asof(C.index, vix)
    fc = C[(C["vix"] > 17.06) & (C["r_rest"].abs() > 0.665)]
    rows.append(("c2 B holdout CORRECTED (NY sessions, open %02d:%02d, B's bar-close fill, day blocks)" % (om2 // 60, om2 % 60),
                 _threadB_eval(fc, "r_rest", "day"), dict(n=None, net=None, win=None, sr=None, p=None), None))
    return rows


def thread_a(vix):
    frame, _ = sessions.build("oanda", "data/raw/oanda_SPX500_USD.parquet", sessions.trading_days_from_vix())
    day = signals.day_table(frame, vix)
    put = signals.candidate(day, 900, "put", "mag", name="A 15:00 put")
    upcall = signals.candidate(day, 900, "both", "mag", name="A big-up call")
    upcall = upcall[upcall["direction"] > 0]
    call = signals.gap_up_call(day, name="A 13:00 call")
    rows = []
    for name, t, target in [("A 15:00 put (big-down)", put, dict(n=516, win=52.7, test_mean=2.77)),
                            ("A 15:00 call (big-up, rejected leg)", upcall, dict(n=473, win=None, test_mean=None)),
                            ("A 13:00 call (gap-up > 0.3%)", call, dict(n=1030, win=53.1, test_mean=1.14))]:
        te = t[t["date"] >= "2013-01-01"]
        got = dict(n=len(t), win=100 * (te["ret_pct"] > 0).mean(), test_n=len(te), test_pts=te["pts"].mean())
        cash = options.trade_table(te, k=1.0, itm=0.02, spread_pts=1.0, settle="cash")
        exit_ = options.trade_table(te, k=1.0, itm=0.02, spread_pts=1.0, settle="exit")
        got["test_mean"] = 100 * cash["opt_ret"].mean()
        got["test_mean_exit_convention"] = 100 * exit_["opt_ret"].mean()
        rows.append((name, got, target))
    fixed = {e: signals.fixed_thresholds(day, e) for e in (900, 930)}
    obs = signals.check_observability(day, signals.all_candidates(day, fixed))
    return rows, obs, fixed


def sanity():
    """Thread A's harness on a zero-drift random walk (mh.sanity, unchanged). mh.sanity passes
    cost_pts=0 but keeps SLIP_BPS = 0.5/side, so the expected meanR is exactly
    -(2 * 0.5 bp * 2000) / stop, which README.md:15-16 states. The win rate sits between the
    geometric prior stop/(stop+target) and 50% because 120-bar time exits are booked at the
    close (mh.py:80); README's "within 3 points" does not hold for the bundled parameters, so
    the gate is: residual meanR equals the modelled slippage within 0.03R and |t| < 2.5."""
    import mh  # research/thread_A_multisleeve/mh.py, unchanged
    res = mh.sanity()
    slip_R = {st: 2 * mh.SLIP_BPS / 10000.0 * 2000 / st for st in (3.0, 6.0, 4.0)}
    ok = all(abs(s["meanR"] + slip_R[st]) < 0.03 and abs(s["t"]) < 2.5 for (st, tg), s in res.items())
    return ok, res


def fmt(v):
    if isinstance(v, (float, np.floating)):
        return "NA (< 20 blocks)" if np.isnan(v) else f"{v:+.4f}"
    return str(v)


if __name__ == "__main__":
    vix = pd.read_parquet("data/raw/vix_daily.parquet")
    results = []
    print("=" * 100 + "\nTHREAD B REPRODUCTION\n" + "=" * 100)
    for name, got, tgt, test in thread_b(vix):
        print(name)
        for k in tgt:
            print(f"   {k:>4}: got {fmt(got[k])}   target {fmt(tgt[k]) if tgt[k] is not None else '(reference row)'}")
        if test is not None:
            ok = test(got, tgt)
            results.append((name, ok))
            print(f"   [{'PASS' if ok else 'FAIL'}]")
    print("=" * 100 + "\nTHREAD A REPRODUCTION (re-implemented from ASSESSMENT_iteration22 prose)\n" + "=" * 100)
    rows, obs, fixed = thread_a(vix)
    for name, got, tgt in rows:
        print(name, "| got:", {k: round(float(v), 3) for k, v in got.items()}, "| target:", tgt)
        hard = abs(got["n"] - tgt["n"]) <= 0.10 * tgt["n"] and (tgt["win"] is None or abs(got["win"] - tgt["win"]) <= 1.0)
        results.append((f"HARD {name}", hard))
        print(f"   [{'PASS' if hard else 'FAIL'}] HARD: trade count within 10% and win rate within 1 point")
        if tgt["test_mean"] is not None:
            soft = abs(got["test_mean"] - tgt["test_mean"]) <= 0.3
            results.append((f"SOFT {name}", soft))
            print(f"   [{'PASS' if soft else 'FAIL'}] SOFT: TEST mean within 0.3 pts of premium (ask entry, intrinsic settlement); "
                  f"half-on-exit convention gives {got['test_mean_exit_convention']:+.2f}%")
    print(f"vixmove_fixed thresholds from Oanda 2005-2012: 15:00 {fixed[900]}, 15:30 {fixed[930]}")
    print("=" * 100 + "\nSANITY: zero-drift random walk through mh.backtest (Thread A harness)\n" + "=" * 100)
    ok, _ = sanity()
    results.append(("sanity", ok))
    print(f"[{'PASS' if ok else 'FAIL'}] residual meanR equals modelled slippage (-0.2/stop) within 0.03R and |t| < 2.5")
    print("=" * 100 + "\nOBSERVABILITY (clock-based)\n" + "=" * 100)
    for name, ok in obs:
        results.append((name, ok))
        print(f"[{'PASS' if ok else 'FAIL'}] {name}")
    clean = subprocess.run(["git", "status", "--porcelain", "research/"], capture_output=True, text=True).stdout.strip() == ""
    results.append(("research/ untouched", clean))
    print(f"[{'PASS' if clean else 'FAIL'}] git status --porcelain research/ is empty")
    print("\nGATE (c):", "PASS" if all(ok for _, ok in results) else "FAIL", "-", sum(ok for _, ok in results), "of", len(results))
    pd.DataFrame(results, columns=["check", "ok"]).to_csv("out/gate_c.csv", index=False)
