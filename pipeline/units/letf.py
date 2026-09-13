"""Leveraged-ETF close-rebalancing candidate (A38, owner's option C, pre-registered 2026-09-13
12:19 UTC; NOT tuned to look good). Mechanism: daily-reset leveraged/inverse S&P 500 funds must
trade (L^2 - L) x NetAssets x r_t near the close to reset leverage before the 16:00 NAV (Cheng &
Madhavan 2009; Tuzun 2013); the sign is the sign of the day's move for long AND inverse funds
alike, so aggregate forced demand is D_t = Sum_i (L_i^2 - L_i) * NetAssets_{i,t-1} * r_t.

    python -m pipeline.units.letf --in extended --out out/letf_candidates.csv

Exactly ONE trial: entry 15:30 ET at the bar close, direction = sign(r_t) (call if r_t > 0, put
if r_t < 0, no trade if r_t == 0), gate = |D_t| >= the expanding 70th percentile of |D| over all
PRIOR sessions that have assets data (min 250 such sessions before the first signal, no fitted
parameter), exit at the 16:00 close. Reported on three windows (CONTEXT 2005-01-01..2012-12-31,
SELECTION 2013-01-01..2020-05-13, HOLDOUT 2020-07-27..2026-09-11), each over sessions with assets
data only. Costs 1.0/2.0 pts; option leg 2% ITM at k=1.3 x prior-close VIX, 1 pt spread, cash
settle. Funds and coefficients (S&P 500 only, A38): SSO 2, SDS 6, UPRO 6, SPXU 12, SPXL 6, SPXS
12, SH 2.

`data/ext/letf_aum_2006_2026.csv` (DATA.md) does not exist on this branch yet: without it, this
unit prints `[SKIP] ...` and writes both output files with a header row only, exit 0, so `make
all`'s non-empty-output check passes and nothing downstream blocks. UNLIKE every other fleet unit
in this codebase (`pipeline.units._gh.run`'s A32 convention: empty file + `<out>.error` + exit 2),
THIS unit's failure contract is fixed by the task that produced it: header-only outputs on ANY
exception (missing file, bad data, a bug) and exit 0, never a `.error` file -- a not-yet-runnable,
pre-registered candidate must never fail `make all`.

Every ambiguity the amendment left open is fixed here and restated in the `spec` column
(SPEC_NOTE below); worth flagging up front:
(1) "entry 15:30 ET at the bar close" is read LITERALLY, like gapliq.py's 10:00/09:31 entries: the
    close of the 1-minute bar at that minute-of-day (`signals.day_table`'s `dec_930`, decision
    price = close of the last bar within 5 min at or before the minute) -- NOT the codebase's usual
    A11 "decide on a bar close, enter at the NEXT bar's open" convention, because the amendment
    names the entry itself as a bar close. A session missing that bar is skipped and counted
    (`n_skipped`), never filled.
(2) r_t = SPX prior close -> 15:30 close uses `signals.day_table`'s dividend-adjusted, roll-day-
    excluded prior close (`prev_close`/`ref_ok`), matching every other prior-close-based signal in
    this codebase (a mechanical ex-dividend drop is not an economic overnight/intraday move; A34).
(3) "net_assets_{i, prior trading day}" = fund i's `net_assets` on the immediate previous NYSE
    trading day (the VIX calendar, `sessions.trading_days_from_vix`), looked up as an EXACT-DATE
    match in that fund's own series -- no forward-fill across a gap. A fund with no row on that
    exact date contributes 0 to D_t: this is read as the fund not yet existing / having no
    rebalancing flow that day (the correct null for a fund that has not launched), never a
    fabricated or filled value. A session counts as "has assets data" (`n_sessions_with_assets`)
    iff AT LEAST ONE fund has such a row, matching the amendment's "runs on every session with
    assets data for at least one fund; sessions without are absent, not filled."
(4) Unknown tickers in the assets file are dropped with a printed note; the seven named tickers'
    coefficients are exactly the amendment's L^2-L values (all positive, since a single common r_t
    multiplies every fund's contribution).
(5) Gate: `signals.expanding_threshold(|D_t|, q=0.70, min_prior=250)` is reused as-is. pandas'
    `expanding(min_periods=n)` counts only NON-NULL observations toward `n` (verified), which is
    exactly "sessions that have assets data" because D_t is NaN whenever no fund has data OR r_t is
    undefined -- this is why D_t is never explicitly re-filtered before the threshold call.
(6) Day-selection control (A16 as A38 restates it): ONE seeded generator (seed 11, the amendment's
    own number), 200 draws (not 200 independent seeds -- the same "one generator, N draws"
    convention documented in fvg.py/gapliq.py), pool = the window's non-signal sessions that DO
    have assets data and a valid 15:30/close price and r_t, same direction rule (sign(r_t)), same
    cost. No timing control is specified by A38 (unlike A39/gapliq) and none is reported here.
(7) magnitude_row_net_pts / beats_magnitude_row: `out/reconcile_candidates.csv` only ever carries
    two literal `window` strings -- the SELECTION range (identical to this file's SELECTION window)
    and D1's own generic holdout range "2020-06-01..2026-09-11", which is NOT this amendment's
    HOLDOUT range (2020-07-27..2026-09-11, the owner's SPY/IEX feed's first bar) -- the two files'
    literal date strings cannot agree for HOLDOUT. The match is therefore made by the reconcile
    row's `label` column instead (the closest defensible reading of "matched by the window/label
    columns"): label == "SELECTION" for our SELECTION window; label in {"PRE-REGISTERED",
    "POST-SELECTION"} for our HOLDOUT window. CONTEXT has no reconcile row at all (NaN).
    `beats_magnitude_row` is False, not NaN, when the magnitude row is absent (an unproven "beats"
    is not asserted true).
(8) DSR at N=37 (25 base + 8 fvg + 1 letf + 3 gapliq, ACCEPTANCE A39's running count) uses THIS
    trial's own per-trade Sharpe as its only SR0-pool entry (n_obs=1 -> SR0=0, i.e. the
    probabilistic Sharpe ratio at the historical family size) -- same "this run's own trials only"
    convention as fvg.py/gapliq.py for a standalone unit that cannot see the other files' trades.
(9) Option leg uses k=1.3 fixed, exactly as the amendment's own text states ("k=1.3 x prior-close
    VIX"), not the D4 sensitivity sweep (k in {1.0,1.3,1.6}), because only one k is named here.
"""
import argparse
import os
import sys
import traceback

import numpy as np
import pandas as pd

from pipeline import options, sessions, signals, stats

ASSETS_PATH = "data/ext/letf_aum_2006_2026.csv"
REQUIRED_COLS = {"ticker", "date", "shares_outstanding", "nav", "net_assets"}
FUND_COEF = {   # L^2 - L (ACCEPTANCE A38); all positive since a single common r_t multiplies every fund
    "SSO": 2,    # 2x
    "SDS": 6,    # -2x
    "UPRO": 6,   # 3x
    "SPXU": 12,  # -3x
    "SPXL": 6,   # 3x
    "SPXS": 12,  # -3x
    "SH": 2,     # -1x
}
MOD_1530 = 15 * 60 + 30     # 930, entry bar-close minute
GATE_Q = 0.70
MIN_PRIOR_SESSIONS = 250   # no fitted parameter (A38)
COST1, COST2 = 1.0, 2.0    # SPX points round trip
OPT_K = 1.3                 # option leg IV = OPT_K * prior-close VIX (A38's own text)
N_SEEDS = 200
CONTROL_SEED = 11           # day-selection control, seed fixed by the amendment itself
DSR_N = 37                  # 25 base + 8 fvg + 1 letf (this trial's own SELECTION row) + 3 gapliq
TRIAL_NAME = "15:30|both|letf_demand"
MAG_CANDIDATE = "15:30|both|mag"    # the price-only magnitude row this candidate must beat (A38)
WINDOWS = [("CONTEXT", "2005-01-01", "2012-12-31"),
           ("SELECTION", "2013-01-01", "2020-05-13"),
           ("HOLDOUT", "2020-07-27", "2026-09-11")]
OUT_COLS = ["window", "trial", "n_sessions_with_assets", "n_signal", "n_skipped", "n", "win",
            "net_pts_cost1", "net_pts_cost2", "net_pct_cost1", "net_pct_cost2",
            "worst_trade_pts_cost1", "worst_day_pts_cost1", "sharpe_calday", "p_boot_day", "p_boot_month",
            "control_mean_pts_cost1", "frac_seeds_beaten",
            "magnitude_row_net_pts", "beats_magnitude_row",
            "opt_mean_pct_s1", "dsr_N37", "spec"]
TRADE_COLS = ["window", "trial", "date", "kind", "direction", "entry_px", "exit_px", "pts",
              "net_pts_cost1", "net_pts_cost2", "ret_pct", "net_pct_cost1", "net_pct_cost2",
              "r_t", "d_t", "d_thr", "w_prior_assets"]

SPEC_NOTE = (
    "FIXED (pre-registration, A38): D_t = Sum_i (L_i^2-L_i) * NetAssets_{i,t-1} * r_t over SSO(2), "
    "SDS(6), UPRO(6), SPXU(12), SPXL(6), SPXS(12), SH(2); r_t = SPX prior close -> 15:30 ET close "
    "(signals.day_table's dividend-adjusted, roll-day-excluded prior close); entry = 15:30 bar "
    "close (literal, not the A11 next-bar-open convention), direction = sign(r_t) (no trade if "
    "r_t == 0), exit = 16:00 close. Gate: |D_t| >= the expanding 70th percentile of |D| over all "
    "strictly prior sessions with assets data (min 250 such sessions, no fitted parameter). "
    "NetAssets_{i,t-1} is an EXACT-DATE lookup on the immediate previous NYSE trading day in fund "
    "i's own series, no forward-fill across a gap; a missing row means that fund contributes 0 "
    "(not yet launched), and a session 'has assets data' iff >= 1 fund has such a row. Costs "
    "1.0/2.0 pts. Day-selection control: 200 draws from one generator seeded 11, same-count random "
    "non-signal sessions with assets data, same direction rule, same fixed entry/exit. "
    "magnitude_row_net_pts is the price-only `15:30|both|mag` row of out/reconcile_candidates.csv "
    "matched by the `label` column (SELECTION, or PRE-REGISTERED/POST-SELECTION for HOLDOUT -- the "
    "two files' literal `window` date strings disagree for HOLDOUT); NaN for CONTEXT (no reconcile "
    "row exists) and beats_magnitude_row is False, not NaN, when it is absent. Option leg: 2% ITM, "
    "k=1.3 x prior-close VIX, 1 pt spread, cash settle (pipeline.options.trade_table). DSR at N=37 "
    "(25 base + 8 fvg + 1 letf + 3 gapliq) uses THIS trial's own per-trade Sharpe as its only SR0-"
    "pool entry (the other trials' files are not available to this standalone unit). Windows: "
    "CONTEXT 2005-01-01..2012-12-31, SELECTION 2013-01-01..2020-05-13, HOLDOUT "
    "2020-07-27..2026-09-11, each reported only over sessions with assets data. On ANY exception "
    "(including the assets file being absent) this unit writes header-only outputs and exits 0, "
    "unlike pipeline.units._gh.run's empty-file+.error+exit-2 convention used by every other fleet "
    "unit here (A32) -- this candidate must never fail `make all` before its data exists.")


def load_assets(path):
    """Validate and filter the assets file (DATA.md): required columns present, unknown tickers
    dropped with a printed note (never silently mixed into the demand sum). Returns a frame with
    only `ticker`, `date` (normalised) and `net_assets`, restricted to the seven named funds."""
    df = pd.read_csv(path)
    missing = REQUIRED_COLS - set(df.columns)
    if missing:
        raise ValueError(f"{path} missing required column(s): {sorted(missing)}")
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"]).dt.normalize()
    known = df["ticker"].isin(FUND_COEF)
    unknown = sorted(set(df.loc[~known, "ticker"]))
    if unknown:
        print(f"[NOTE] A38 letf.py ignoring unknown ticker(s) in {path}: {unknown}")
    return df.loc[known, ["ticker", "date", "net_assets"]].reset_index(drop=True)


def prior_trading_day(dates, td):
    """For each date in `dates`, the immediate previous entry in `td` (the NYSE trading-day
    calendar), or NaT where none exists (the very first date(s) in history) -- same searchsorted
    technique as signals.day_table's prev_is_prior_td."""
    td_sorted = pd.DatetimeIndex(sorted(set(td)))
    pos = td_sorted.searchsorted(np.asarray(dates, dtype="datetime64[ns]"), side="left") - 1
    vals = np.where(pos >= 0, td_sorted.to_numpy()[np.clip(pos, 0, None)], np.datetime64("NaT"))
    return pd.DatetimeIndex(vals)


def build_asset_features(day_index, assets_known, td):
    """W_{t-1} = Sum_i coef_i * net_assets_{i, prior trading day} per session date in `day_index`,
    using an EXACT-DATE lookup per fund on its own series (no forward-fill across a gap -- see the
    module docstring, point 3). Returns (w_prior, has_assets), both pandas Series aligned to
    `day_index`; w_prior is NaN wherever has_assets is False (no fund has data that session)."""
    prior = prior_trading_day(day_index, td)
    w = pd.Series(0.0, index=day_index)
    has = pd.Series(False, index=day_index)
    for ticker, coef in FUND_COEF.items():
        s = (assets_known.loc[assets_known["ticker"] == ticker]
             .drop_duplicates("date", keep="last").set_index("date")["net_assets"])
        val = pd.Series(s.reindex(prior).to_numpy(), index=day_index)
        has = has | val.notna()
        w = w + coef * val.fillna(0.0)
    return w.where(has), has


def build_day_table(frame, vix, meta, td, assets_known):
    """`signals.day_table` plus r_t (prior close -> 15:30 close), the aggregate prior-day asset
    weight, the has-assets flag, D_t, its expanding-70th-percentile gate and the signal flag."""
    day = signals.day_table(frame, vix, dividends=meta["dividends"] if meta else None, trading_days=td,
                            roll_dates=meta["roll_dates"] if meta else ())
    day["r_t"] = np.where(day["ref_ok"] & day["dec_930"].notna(), day["dec_930"] / day["prev_close"] - 1, np.nan)
    w_prior, has_assets = build_asset_features(day.index, assets_known, td)
    day["w_prior_assets"] = w_prior
    day["has_assets"] = has_assets
    day["d_t"] = day["w_prior_assets"] * day["r_t"]
    day["d_thr"] = signals.expanding_threshold(day["d_t"].abs(), q=GATE_Q, min_prior=MIN_PRIOR_SESSIONS)
    day["signal"] = (day["d_t"].abs() >= day["d_thr"]).fillna(False)
    return day


def build_trades(day, dates):
    """One row per executed trade: entry = 15:30 bar close, exit = 16:00 close, direction =
    sign(r_t)."""
    d = day.loc[dates]
    entry_px = d["dec_930"].to_numpy(float)
    exit_px = d["close"].to_numpy(float)
    r_t = d["r_t"].to_numpy(float)
    direction = np.sign(r_t)
    pts = direction * (exit_px - entry_px)
    ret_pct = direction * (exit_px / entry_px - 1) * 100
    return pd.DataFrame(dict(date=pd.DatetimeIndex(dates), kind=np.where(direction > 0, "c", "p"),
                             direction=direction, entry_px=entry_px, exit_px=exit_px, pts=pts, ret_pct=ret_pct,
                             entry_mod=MOD_1530, exit_mod=d["last_mod"].to_numpy(), vix_prev=d["vix_prev"].to_numpy(),
                             r_t=r_t, d_t=d["d_t"].to_numpy(), d_thr=d["d_thr"].to_numpy(),
                             w_prior_assets=d["w_prior_assets"].to_numpy()))


def day_selection_control(day, start_ts, end_ts, cost, n_trades, n_seeds=N_SEEDS, seed=CONTROL_SEED):
    """A16/A38: 200 draws from one seeded generator over the window's non-signal sessions that have
    assets data and a valid 15:30/close price and r_t, same direction rule (sign(r_t)), same fixed
    entry/exit (net of `cost`). Returns the per-seed mean net pts array (empty when there is no
    matched trade or not enough eligible sessions to draw from)."""
    w = day[(day.index >= start_ts) & (day.index <= end_ts) & day["has_assets"] & ~day["signal"]
           & day["r_t"].notna() & (day["r_t"] != 0) & day["dec_930"].notna() & day["close"].notna()]
    if n_trades == 0 or len(w) < n_trades:
        return np.array([])
    entry, exitp = w["dec_930"].to_numpy(float), w["close"].to_numpy(float)
    direction = np.sign(w["r_t"].to_numpy(float))
    pts = direction * (exitp - entry) - cost
    rng = np.random.default_rng(seed)
    return np.array([pts[rng.choice(len(w), n_trades, replace=False)].mean() for _ in range(n_seeds)])


def magnitude_row_net_pts(recon, win_name):
    """The price-only `15:30|both|mag` row of out/reconcile_candidates.csv matched by `label`
    (see module docstring point 7); NaN when reconcile hasn't run or no matching row exists."""
    if recon is None or not len(recon):
        return np.nan
    if win_name == "SELECTION":
        sub = recon[(recon["candidate"] == MAG_CANDIDATE) & (recon["label"] == "SELECTION")]
    elif win_name == "HOLDOUT":
        sub = recon[(recon["candidate"] == MAG_CANDIDATE) & (recon["label"].isin(("PRE-REGISTERED", "POST-SELECTION")))]
    else:
        return np.nan
    return float(sub["net_pts"].iloc[0]) if len(sub) else np.nan


def summarize(win_name, day, start_ts, end_ts, recon):
    win_day = day[(day.index >= start_ts) & (day.index <= end_ts)]
    n_sessions_with_assets = int(win_day["has_assets"].sum())
    n_skipped = int((win_day["has_assets"] & win_day["d_t"].isna()).sum())
    sig_dates = win_day.index[win_day["signal"]]
    n_signal = len(sig_dates)
    exec_dates = [d for d in sig_dates if win_day.loc[d, "r_t"] != 0]   # r_t == 0 -> no trade (A38)
    trades = build_trades(day, exec_dates)
    n = len(trades)
    trades["net_pts_cost1"] = trades["pts"] - COST1
    trades["net_pts_cost2"] = trades["pts"] - COST2
    trades["net_pct_cost1"] = trades["ret_pct"] - 100 * COST1 / trades["entry_px"]
    trades["net_pct_cost2"] = trades["ret_pct"] - 100 * COST2 / trades["entry_px"]
    net_pct1 = trades["net_pct_cost1"].to_numpy() if n else np.array([])
    all_dates = win_day.index[win_day["has_assets"]].tolist()   # A38: reported only over sessions with assets data
    row = dict(window=win_name, trial=TRIAL_NAME, n_sessions_with_assets=n_sessions_with_assets,
               n_signal=n_signal, n_skipped=n_skipped, n=n,
               win=(100 * (trades["pts"] > 0).mean()) if n else np.nan,
               net_pts_cost1=trades["net_pts_cost1"].mean() if n else np.nan,
               net_pts_cost2=trades["net_pts_cost2"].mean() if n else np.nan,
               net_pct_cost1=trades["net_pct_cost1"].mean() if n else np.nan,
               net_pct_cost2=trades["net_pct_cost2"].mean() if n else np.nan,
               worst_trade_pts_cost1=trades["net_pts_cost1"].min() if n else np.nan,
               worst_day_pts_cost1=trades.groupby("date")["net_pts_cost1"].sum().min() if n else np.nan)
    row["sharpe_calday"] = stats.calendar_day_sharpe(net_pct1, trades["date"], all_dates)
    row["p_boot_day"] = stats.one_sided_p(net_pct1, stats.day_blocks(trades["date"])) if n else np.nan
    row["p_boot_month"] = stats.one_sided_p(net_pct1, stats.month_blocks(trades["date"])) if n else np.nan
    ctrl_pts = day_selection_control(day, start_ts, end_ts, COST1, n)
    valid = ~np.isnan(ctrl_pts) if len(ctrl_pts) else np.array([], dtype=bool)
    row["control_mean_pts_cost1"] = float(np.nanmean(ctrl_pts)) if valid.any() else np.nan
    row["frac_seeds_beaten"] = float(np.mean(row["net_pts_cost1"] > ctrl_pts[valid])) if (n and valid.any()) else np.nan
    mag = magnitude_row_net_pts(recon, win_name)
    row["magnitude_row_net_pts"] = mag
    row["beats_magnitude_row"] = bool(n and pd.notna(mag) and row["net_pts_cost1"] > mag)
    if n:
        opt_in = trades[["entry_px", "exit_px", "entry_mod", "exit_mod", "vix_prev", "kind"]]
        o = options.trade_table(opt_in, k=OPT_K, itm=0.02, spread_pts=1.0, grid=options.GRID["SPX"], settle="cash")
        row["opt_mean_pct_s1"] = float(o["opt_ret"].mean() * 100)
    else:
        row["opt_mean_pct_s1"] = np.nan
    row["spec"] = SPEC_NOTE
    return row, trades, net_pct1


def _trades_path(out):
    return out[:-4] + "_trades.csv" if out.endswith(".csv") else out + "_trades.csv"


def _write_header_only(out):
    pd.DataFrame(columns=OUT_COLS).to_csv(out, index=False)
    pd.DataFrame(columns=TRADE_COLS).to_csv(_trades_path(out), index=False)


def main(inp, out, assets_path=ASSETS_PATH):
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    if inp != "extended":
        raise ValueError(f"pipeline.units.letf only supports --in extended (got {inp!r})")
    if not os.path.exists(assets_path):
        print(f"[SKIP] A38 waits for {assets_path} (DATA.md)")
        _write_header_only(out)
        return
    assets_known = load_assets(assets_path)
    td = sessions.trading_days_from_vix()
    frame, _dropped, meta = sessions.build_extended(trading_days=td)
    vix = pd.read_parquet("data/raw/vix_daily.parquet")
    day = build_day_table(frame, vix, meta, td, assets_known)
    recon = pd.read_csv("out/reconcile_candidates.csv") if os.path.exists("out/reconcile_candidates.csv") else None

    rows, trade_frames = [], []
    for win_name, start, end in WINDOWS:
        start_ts, end_ts = pd.Timestamp(start), pd.Timestamp(end)
        row, trades, net_pct1 = summarize(win_name, day, start_ts, end_ts, recon)
        if len(net_pct1) >= 3:
            dsr, _, _ = stats.deflated_sharpe(net_pct1, sr_trials=[stats.per_trade_sharpe(net_pct1)], n=DSR_N)
        else:
            dsr = np.nan
        row["dsr_N37"] = dsr
        rows.append(row)
        trade_frames.append(trades.assign(window=win_name, trial=TRIAL_NAME))

    res = pd.DataFrame(rows)[OUT_COLS]
    res.to_csv(out, index=False, float_format="%.6f")
    tr_all = (pd.concat(trade_frames, ignore_index=True) if trade_frames else pd.DataFrame(columns=TRADE_COLS))
    tr_all.reindex(columns=TRADE_COLS).to_csv(_trades_path(out), index=False, float_format="%.6f")
    print(res.to_string(index=False, float_format=lambda x: f"{x:.4f}"))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", default="extended")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    try:
        main(a.inp, a.out)
    except Exception:
        # A38's own contract (see module docstring): header-only outputs, never a .error file, exit
        # 0 -- this pre-registered-but-not-yet-runnable candidate must never fail `make all`.
        traceback.print_exc()
        _write_header_only(a.out)
    sys.exit(0)
