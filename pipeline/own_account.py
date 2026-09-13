"""D5 — the 8-sleeve unconstrained portfolio (Thread A) re-measured on the fetched data.

Sleeve code is imported UNCHANGED from research/thread_A_multisleeve where a function exists
(it7.dipscore/trades, it8.s4_turn_of_month/vol_target/perf, it9.s5_volmanaged/s6_strev,
it11.build_sleeves); the inverse-vol TSMOM/XSMOM variants are copied from it8b.py (that file
runs at import) with `iv` passed explicitly; S12 (gap-up afternoon, underlying at ES cost) comes
from pipeline.signals; S13 (VXX/VXZ term structure) is re-implemented from
ASSESSMENT_iteration17_VOL.md (no script in the bundle).

Windows: BASELINE 2006-01→2017-11-10 (Thread A's sample; train <2012 / test ≥2012 as it8b.py)
and EXTENDED to the last date each sleeve's data allows: SPY daily and the stock panel run to
2026-03 (S1, S4, S5, S8); the Oanda minute feed to 2020-05 (S12); the Kaggle ETF panel to
2017-11-10 (S2, S3, S6, S13) until data/ext/etf_daily_*.csv.gz is supplied (bridged per A13).
Reproduction targets (STRATEGY.md:55-57, HANDOFF.md:136-138): 8 sleeves equal weight Sharpe
1.12 full / 1.35 test, maxDD −6.10%; two buckets 50/50: 1.20 / 1.40, maxDD −5.26%.
"""
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "research" / "thread_A_multisleeve"))
import it7  # noqa: E402  dipscore, trades
import it8  # noqa: E402  s4_turn_of_month, vol_target, perf, COST_BPS, UNIVERSE
import it9  # noqa: E402  s5_volmanaged, s6_strev
import it11  # noqa: E402  build_sleeves (S8 BAB)

from pipeline import sessions, signals  # noqa: E402

UNIVERSE = it8.UNIVERSE
SPLIT = "2012-01-01"
BASE_END = "2017-11-10"
BUCKET_A = ["S1_MEANREV", "S12_GAPUP", "S13_VOLTS"]
BUCKET_B = ["S2_TSMOM", "S3_XSMOM", "S5_VOLMGD", "S6_STREV", "S8_BAB"]
ES_COST_PTS = 0.42               # ES round trip in index points (ACCEPTANCE budget 0.33-0.50 pts; A21), charged per trade at the entry level
VOL_COST_BPS = 5.0               # VXX/VXZ per side, ASSESSMENT_iteration17
S13_CAP = 0.5                    # weight cap on S13 relative to the other sleeves (STRATEGY.md:92-103)
BRIDGE_MIN_CORR = 0.98           # A13 (amended): measured old-VXZ vs VIXM daily-return corr is 0.987 (ETN vs ETF on the same index)


# --------------------------------------------------------------------------- data
def etf_closes(ext_path="data/ext/etf_daily_2017-11_2026-09.csv.gz"):
    k = pd.read_parquet("data/raw/etf_daily_kaggle.parquet")
    C = k.pivot(index="date", columns="ticker", values="close").sort_index()
    note = "Kaggle mirror to 2017-11-10"
    if os.path.exists(ext_path):
        e = pd.read_csv(ext_path, parse_dates=["date"])
        E = e.pivot(index="date", columns="ticker", values="adj_close").sort_index()
        C = bridge(C, E)
        note = "Kaggle mirror bridged to the ext panel"
    return C, note


def bridge(C, E):
    """Chain each ticker's ext series onto the Kaggle series by returns from the last common
    date (or from the ext start when there is no overlap). VXX/VXZ per A13 are bridged through
    VIXY/VIXM outside this function (see splice_vol)."""
    out = {}
    for t in set(C.columns) | set(E.columns):
        a = C[t].dropna() if t in C else pd.Series(dtype=float)
        b = E[t].dropna() if t in E else pd.Series(dtype=float)
        if a.empty:
            out[t] = b
        elif b.empty:
            out[t] = a
        else:
            b = b[b.index > a.index[-1]]
            scale = a.iloc[-1] / E[t].reindex([a.index[-1]]).iloc[0] if a.index[-1] in E.index else 1.0
            out[t] = pd.concat([a, b * scale])
    return pd.DataFrame(out).sort_index()


def splice_vol(C, old, new, proxy, out=None):
    """A13: chain `old` (original ETN, ends 2017-11-10) -> `proxy` (VIXY/VIXM, continuous) -> `new`
    (the 2018 Series B note, present only when the ext panel is supplied) by daily returns.
    Returns (price-like series, dict of bridge correlations); the bridge is refused (returns
    the old series only) if any correlation on an overlap is below BRIDGE_MIN_CORR (0.98, A13)."""
    corr = {}
    o = C[old].dropna() if old in C else pd.Series(dtype=float)
    p = C[proxy].dropna() if proxy in C else pd.Series(dtype=float)
    n = C[new].dropna() if new in C else pd.Series(dtype=float)
    if o.empty or p.empty:
        return o, corr
    ov = o.index.intersection(p.index)
    corr[f"{old}_vs_{proxy}"] = float(o.pct_change().reindex(ov).corr(p.pct_change().reindex(ov))) if len(ov) > 250 else np.nan
    r = o.pct_change().fillna(0.0)
    tail = p.pct_change()[p.index > o.index[-1]]
    if not n.empty and n.index.max() > o.index[-1]:
        n2 = n[n.index > o.index[-1]]
        ov2 = n2.index.intersection(p.index)
        corr[f"{new}_vs_{proxy}"] = float(n2.pct_change().reindex(ov2).corr(p.pct_change().reindex(ov2))) if len(ov2) > 250 else np.nan
        tail = pd.concat([tail[tail.index < n2.index[0]], n2.pct_change().fillna(0.0)])
    if any(v == v and v < BRIDGE_MIN_CORR for v in corr.values()):
        return o, corr
    chained = pd.concat([r, tail.dropna()])
    return (1 + chained).cumprod() * o.iloc[0], corr


def spy_ohlc():
    d = pd.read_parquet("data/raw/spy_daily.parquet").sort_values("date")
    return d[["date", "open", "high", "low", "close"]].reset_index(drop=True)


def clean_universe(panel, min_rows=1200):
    """Thread A's it5b cleaning of the 928-stock big_movers panel down to the 626-name
    universe that `it11.build_sleeves` (S8 BAB) was built for (it11.py:6, "the 626-name
    single-stock panel"). `panel_clean.pkl` itself is not in the bundle, so the rules are
    reconstructed here, verbatim, from the two scripts that produced it (research/ is not
    edited):
      - history >= 1200 rows, price floor close.median() >= 5 (it5.py:36, `load_panel`:
        "if len(df) < 1200 or df.close.median() < 5: continue")
      - liquidity floor (close*volume).median() >= 5e6 (it5.py:37: "(df.close *
        df.volume).median() < 5e6: continue")
      - drop symbols with > 5 days of |daily return| > 50%, reverse-split/delisting
        artifacts (it5b.py:5-8: "chronic = (r.abs()>0.5).sum(); drop =
        chronic[chronic>5].index"), documented as "drop the 30 symbols with more than
        five such days" in ASSESSMENT_iteration5_FINAL.md section 1.
    `panel` is the long-form frame (ticker, date, open, high, low, close, volume) as loaded
    from data/raw/stocks_daily.parquet. Returns the cleaned close-price panel; the remaining
    per-day artifact mask (it5b.py:11-12) is already applied inline by `it11.build_sleeves`
    ("R = R.where(R.abs() < 0.5)  # artifact mask, as iteration 5").
    """
    n0 = panel["ticker"].nunique()
    print(f"BAB universe: {n0} raw tickers (data/raw/stocks_daily.parquet)")
    keep = []
    for sym, g in panel.groupby("ticker"):
        g = g.sort_values("date").drop_duplicates("date")
        if len(g) < min_rows or g["close"].median() < 5:            # it5.py:36
            continue
        if (g["close"] * g["volume"]).median() < 5e6:               # it5.py:37
            continue
        keep.append(sym)
    print(f"BAB universe: {len(keep)} after history>={min_rows}d / price>=$5 / dollar-vol>=$5e6 (it5.py:36-37)")
    C = panel[panel["ticker"].isin(keep)].pivot(index="date", columns="ticker", values="close").sort_index()
    r = C.pct_change(fill_method=None)
    chronic = (r.abs() > 0.5).sum()                                 # it5b.py:6
    drop = chronic[chronic > 5].index                                # it5b.py:7
    keep2 = [s for s in C.columns if s not in drop]
    print(f"BAB universe: dropped {len(drop)} chronic reverse-split/delisting symbols (it5b.py:5-9) "
          f"-> {len(keep2)} names (Thread A reports 626, ASSESSMENT_iteration5_FINAL.md §1)")
    return C[keep2]


def stock_closes(min_rows=1200):
    s = pd.read_parquet("data/raw/stocks_daily.parquet")
    return clean_universe(s, min_rows=min_rows)


# --------------------------------------------------------------------------- sleeves
def tsmom_iv(C, R, iv, lb=252):
    """it8b.py tsmom_iv, with iv passed in."""
    sig = (C / C.shift(lb) - 1 > 0).shift(1).astype(float).where(C.shift(lb).notna())
    w = (sig * iv)
    w = w.div(w.sum(axis=1).replace(0, np.nan), axis=0).fillna(0.0)
    turn = w.diff().abs().sum(axis=1).fillna(0.0)
    return (w * R).sum(axis=1) - turn * it8.COST_BPS / 10000.0


def xsmom_iv(C, R, iv, lb=252, frac=3):
    """it8b.py xsmom_iv, with iv passed in."""
    mom = (C / C.shift(lb) - 1).shift(1)
    rk = mom.rank(axis=1, pct=True)
    n = mom.notna().sum(axis=1)
    lw = ((rk > 1 - 1 / frac).astype(float) * iv)
    sw = ((rk < 1 / frac).astype(float) * iv)
    lw = lw.div(lw.sum(axis=1).replace(0, np.nan), axis=0)
    sw = sw.div(sw.sum(axis=1).replace(0, np.nan), axis=0)
    w = (lw.fillna(0) - sw.fillna(0)).where(n >= 8, 0.0)
    turn = w.diff().abs().sum(axis=1).fillna(0.0)
    return (w * R).sum(axis=1) - turn * it8.COST_BPS / 10000.0


def s1_dipscore(spy, index):
    """it8b.py lines 24-30: DipScore trades on SPY daily → daily return stream."""
    d = it7.dipscore(spy.copy())
    t = it7.trades(d, (d["score"] >= 0.35).values, 2.0, 1.0, 5, cost_bps=it8.COST_BPS)
    px = spy.set_index("date")["close"]
    r = px.pct_change().reindex(index).fillna(0.0)
    s = pd.Series(0.0, index=index)
    for _, x in t.iterrows():
        m = (index > pd.Timestamp(x.entry_date)) & (index <= pd.Timestamp(x.exit_date))
        s[m] += r[m].values
    return s, t


def s12_gapup(index):
    """Gap-up afternoon on the underlying (futures cost), from pipeline.signals on Oanda."""
    vix = pd.read_parquet("data/raw/vix_daily.parquet")
    frame, _ = sessions.build("oanda", "data/raw/oanda_SPX500_USD.parquet", sessions.trading_days_from_vix())
    day = signals.day_table(frame, vix)
    g = signals.gap_up_call(day)
    r = pd.Series(g["ret_pct"].to_numpy() / 100 - ES_COST_PTS / g["entry_px"].to_numpy(), index=pd.to_datetime(g["date"]))
    return r.reindex(index).fillna(0.0), frame["date"].max()


def s13_volts(C, bridge=None):
    """ASSESSMENT_iteration17_VOL.md: sign of the 5-day VXX−VXZ return spread, lagged one day;
    + → long VXX, − → short VXX; 5 bp per side. VXX/VXZ come from splice_vol (A13)."""
    if "vxx" not in C or "vxz" not in C:
        return None
    vxx, cx = splice_vol(C, "vxx", "vxx_new", "vixy")
    vxz, cz = splice_vol(C, "vxz", "vxz_new", "vixm")
    if bridge is not None:
        bridge.update({**cx, **cz})
    vxx, vxz = vxx.dropna(), vxz.dropna()
    idx = vxx.index.intersection(vxz.index)
    vxx, vxz = vxx.reindex(idx), vxz.reindex(idx)
    spread = (vxx / vxx.shift(5) - 1) - (vxz / vxz.shift(5) - 1)
    w = np.sign(spread).shift(1).fillna(0.0)
    r = vxx.pct_change().fillna(0.0)
    turn = w.diff().abs().fillna(0.0)
    return (w * r) - turn * VOL_COST_BPS / 10000.0


def build_sleeves():
    C, note = etf_closes()
    if "vxx" in C and C["vxx"].dropna().index.max() > pd.Timestamp("2018-06-01"):   # ext panel present: separate the Series B notes
        for t in ("vxx", "vxz"):
            new = C[t][C[t].index > pd.Timestamp("2017-11-10")]
            C[f"{t}_new"] = new
            C.loc[C.index > pd.Timestamp("2017-11-10"), t] = np.nan
    U = C[[c for c in UNIVERSE if c in C]]
    R = U.pct_change()
    iv = (1.0 / (R.rolling(60).std().shift(1))).replace([np.inf, -np.inf], np.nan)
    index = U.index
    spy = spy_ohlc()
    ends = {}
    s1, dip_trades = s1_dipscore(spy, spy.set_index("date").index)
    s12, s12_end = s12_gapup(spy.set_index("date").index)
    stocks = stock_closes()
    mkt = stocks.pct_change().where(lambda x: x.abs() < 0.5).mean(axis=1)
    bab = it11.build_sleeves(stocks, mkt)["S8_BAB"]
    spyC = spy.set_index("date")[["close"]].rename(columns={"close": "spy"})
    bridge = {}
    s13 = s13_volts(C, bridge)
    sleeves = {
        "S1_MEANREV": s1, "S2_TSMOM": tsmom_iv(U, R, iv), "S3_XSMOM": xsmom_iv(U, R, iv),
        "S5_VOLMGD": it9.s5_volmanaged(spyC, "spy"), "S6_STREV": it9.s6_strev(U),
        "S8_BAB": bab, "S12_GAPUP": s12, "S13_VOLTS": s13}
    ends = {"S1_MEANREV": spy["date"].max(), "S2_TSMOM": U.index.max(), "S3_XSMOM": U.index.max(),
            "S5_VOLMGD": spy["date"].max(), "S6_STREV": U.index.max(), "S8_BAB": stocks.index.max(),
            "S12_GAPUP": s12_end, "S13_VOLTS": s13.index.max() if s13 is not None else pd.NaT}
    pd.DataFrame([dict(pair=k, daily_return_corr=v) for k, v in bridge.items()] or [dict(pair="none", daily_return_corr=np.nan)]).to_csv(
        "out/own_account_bridge.csv", index=False, float_format="%.6f")
    S = pd.DataFrame({k: v for k, v in sleeves.items() if v is not None})
    S = S.loc["2006-01-01":].copy()
    for k, e in ends.items():                       # no returns after a sleeve's data ends
        if k in S:
            S.loc[S.index > pd.Timestamp(e), k] = np.nan
    return S, ends, note, dip_trades, bridge


def combine(S, cap13=S13_CAP):
    V = S.apply(it8.vol_target)                     # each sleeve to 10% vol, trailing only (it8.vol_target)
    V["S13_VOLTS"] = V["S13_VOLTS"] * cap13 if "S13_VOLTS" in V else np.nan
    avail = V.notna()
    eq = V.fillna(0.0).sum(axis=1) / avail.sum(axis=1).replace(0, np.nan)
    a = V[[c for c in BUCKET_A if c in V]]
    b = V[[c for c in BUCKET_B if c in V]]
    ba = a.fillna(0.0).sum(axis=1) / a.notna().sum(axis=1).replace(0, np.nan)
    bb = b.fillna(0.0).sum(axis=1) / b.notna().sum(axis=1).replace(0, np.nan)
    two = 0.5 * ba.fillna(0.0) + 0.5 * bb.fillna(0.0)
    P = pd.DataFrame({"EQUAL_8": eq, "BUCKET_A": ba, "BUCKET_B": bb, "TWO_BUCKET_50_50": two})
    P.attrs["n_sleeves"] = avail.sum(axis=1)          # how many sleeves the equal-weight book holds each day (Phase 4 defect 4)
    return V, P


def regimes(index):
    spy = spy_ohlc().set_index("date")["close"].reindex(index).ffill()
    vix = pd.read_parquet("data/raw/vix_daily.parquet").set_index("date")["close"].reindex(index).ffill().shift(1)
    sma = spy.rolling(200).mean()
    up = (spy > sma) & (sma.diff(20) > 0)
    hv = vix > vix.expanding(min_periods=250).quantile(2 / 3).shift(1)
    reg = pd.Series("downtrend", index=index)
    reg[up] = "uptrend"
    reg[hv] = "high_vol"
    return reg


def perf_row(r, label, window, n_sleeves=None):
    p = it8.perf(r.dropna(), label)
    if p is None:
        return dict(label=label, window=window, n_days=int(r.notna().sum()))
    p.update(window=window, n_days=int(r.notna().sum()), start=str(r.dropna().index.min().date()), end=str(r.dropna().index.max().date()))
    if n_sleeves is not None:
        ns = n_sleeves.reindex(r.dropna().index)
        p.update(sleeves_mean=float(ns.mean()), sleeves_min=int(ns.min()), sleeves_max=int(ns.max()))
        if ns.min() < 8 and label == "EQUAL_8":
            p["label"] = f"EQUAL_available({int(ns.min())}-{int(ns.max())})"
    return p


def main():
    os.makedirs("out", exist_ok=True)
    S, ends, note, dip_trades, bridge = build_sleeves()
    V, P = combine(S)
    ns = P.attrs["n_sleeves"]
    rows = []
    windows = {"BASELINE 2006-2017-11 full": ("2006-01-01", BASE_END), "BASELINE train <2012": ("2006-01-01", "2011-12-31"),
               "BASELINE test 2012-2017-11": (SPLIT, BASE_END), "EXTENDED (each sleeve to its data end)": ("2006-01-01", "2026-12-31"),
               "POST-BASELINE 2017-11-13 →": ("2017-11-13", "2026-12-31")}
    for wl, (a, b) in windows.items():
        for c in V.columns:
            rows.append(perf_row(V.loc[a:b, c], c, wl))
        for c in P.columns:
            rows.append(perf_row(P.loc[a:b, c], c, wl, ns))
    res = pd.DataFrame(rows)
    res.to_csv("out/own_account_summary.csv", index=False, float_format="%.6f")
    V.to_csv("out/own_account_sleeves.csv", float_format="%.8f")
    P.to_csv("out/own_account_portfolios.csv", float_format="%.8f")
    reg = regimes(P.index)
    Pl = P.rename(columns={"EQUAL_8": "EQUAL_available"})             # the book holds fewer than 8 sleeves outside 2012-2017 (Phase 4 defect 4)
    by_reg = Pl.groupby(reg).mean() * 252
    by_reg["sleeves_mean"] = ns.groupby(reg).mean()
    by_reg.index.name = "regime"
    by_reg.to_csv("out/own_account_by_regime.csv", float_format="%.6f")
    by_year = Pl.groupby(Pl.index.year).sum()
    by_year["sleeves_mean"] = ns.groupby(ns.index.year).mean()
    by_year["sleeves_min"] = ns.groupby(ns.index.year).min()
    by_year.index.name = "year"
    by_year.to_csv("out/own_account_by_year.csv", float_format="%.6f")
    print("ETF panel:", note, "| VXX/VXZ bridge correlations:", bridge or "old series only (ext panel absent)")
    print("sleeve data ends:", {k: str(v)[:10] for k, v in ends.items()})
    cm = V.loc[:BASE_END].corr()
    iu = np.triu_indices_from(cm.values, 1)
    rho = np.nanmean(cm.values[iu])
    print(f"baseline mean pairwise sleeve correlation {rho:.3f} -> n_eff {len(V.columns) / (1 + (len(V.columns) - 1) * max(rho, 0)):.2f}")
    show = res[res["window"].str.startswith("BASELINE")][["window", "label", "cagr", "vol", "sharpe", "maxdd", "n_days", "sleeves_mean"]]
    print(show.to_string(index=False, float_format=lambda x: f"{x:.4f}"))
    print("\nEXTENDED / POST-BASELINE:")
    print(res[~res["window"].str.startswith("BASELINE")][["window", "label", "cagr", "vol", "sharpe", "maxdd", "start", "end", "sleeves_mean", "sleeves_min"]]
          .to_string(index=False, float_format=lambda x: f"{x:.4f}"))
    print("\nby regime (annualised mean):")
    print(by_reg.to_string(float_format=lambda x: f"{x:.4f}"))
    print("\nby year (sum of daily returns):")
    print(by_year.to_string(float_format=lambda x: f"{x:.4f}"))


if __name__ == "__main__":
    main()
