"""Overnight-loss forced-liquidation rebound (A39, pre-registered 2026-09-13 12:19 UTC, before any
run; NOT tuned to look good). Mechanism: after a large overnight loss, margin calls issued on the
prior close force liquidations at/just after the open (Brunnermeier & Pedersen 2009); the forced
selling is front-loaded in the first 30 minutes, so the hypothesis is a positive drift from 10:00
to the close on those days (T1), a LARGER drift from 10:00 than from 09:31 (T2, timing fingerprint:
must be worse than T1) and NO mirror effect after large overnight gains (T3, mirror signal, put,
must NOT be positive at 1 pt).

    python -m pipeline.units.gapliq --in extended --out out/gapliq_candidates.csv

3 trials, all counted (A39): T1 = long call, entry 10:00 bar close, exit 16:00 close, on days
where the overnight return (prior 16:00 close -> this session's 09:30 open) is <= the expanding
10th percentile of overnight returns over all prior sessions (min 250 prior sessions, no fitted
parameter); T2 = same days as T1, long call, entry 09:31 bar close, exit 16:00; T3 = mirror signal
(overnight return >= the expanding 90th percentile), long put, entry 10:00 bar close, exit 16:00.
Reported on three windows (CONTEXT 2005-01-01..2012-12-31, SELECTION 2013-01-01..2020-05-13,
HOLDOUT 2020-07-27..2026-09-11) on the extended frame (sessions.build_extended, Oanda SPX + the
ext feed, both already in SPX points). No parameter is swept beyond the three trials; the 10th/90th
percentile, the 250-session minimum and the 10:00/09:31 entry times are FIXED by the
pre-registration and never varied. Promotion (ACCEPTANCE's kill/promotion rule) is judged in
`pipeline/report.py` section 10 from this file's own columns, never re-typed.

Every ambiguity the amendment left open is fixed here and restated in the `spec` column
(SPEC_NOTE below); the ones worth flagging:
(1) "entry at the 10:00 / 09:31 bar close" is read LITERALLY as the close of the 1-minute bar at
    that exact minute-of-day (mod 600 / 571) on the regular-session frame `sessions.build_extended`
    returns -- NOT the codebase's usual A11 "decide on a bar close, enter at the NEXT bar's open"
    convention, because the amendment names the entry itself as a bar close.
(2) A session is eligible for ANY of the three trials only if BOTH the 10:00 and the 09:31 bar are
    present (most conservative reading of "sessions with missing 10:00 or 09:31 bars are skipped");
    this also guarantees T1 and T2 trade the literal same day set, as the amendment requires for T2.
    Sessions failing this gate are counted in `n_skipped`, not dropped silently.
(3) Overnight return uses `signals.day_table`'s dividend-adjusted, roll-day-excluded prior close
    (`prev_close`/`ref_ok`) rather than the raw prior close, matching every other prior-close-based
    signal in this codebase (a mechanical ex-dividend drop is not an economic overnight loss); a
    session without a valid prior-trading-day reference gets no overnight return and cannot signal
    or feed the expanding-percentile pool.
(4) The 10th/90th percentile thresholds expand across the WHOLE history (via `signals.
    expanding_threshold`, min_prior=250), never resetting at a window boundary -- same convention
    as the D1 gates and fvg.py's ATR/structure lookback; only the reported ROWS are filtered by
    window.
(5) Day-selection control (A16): 200 draws from ONE generator seeded 11 (not 200 independent
    seeds), matching fvg.py's/signals.day_selection_control's documented convention; pool = the
    window's non-signal, both-bars-eligible sessions, same fixed entry/exit as the matched trial.
(6) Timing control: same real trade days, entry at a uniformly random INTEGER minute-of-day in
    [09:31,15:00] (bar close at that minute, mirroring this file's own bar-close entry convention),
    exit at 16:00 close, same direction/cost. The amendment fixes "200 seeds" but not a seed number
    (unlike the day-selection control, which this file's caller specified as seed 11); TIMING_SEED
    below is an arbitrary fixed constant, distinct from 11, chosen only for determinism.
(7) Option leg (2% ITM, k=1.3 x prior-close VIX, 1 pt spread, cash settle) is priced on the REAL
    trades only, via `pipeline.options.trade_table`, same convention as D4/insample.py.
(8) On any exception this unit follows `pipeline.units._gh.run` exactly as fvg.py/flow.py do: an
    empty (zero-byte) output file plus `<out>.error` with the traceback, exit code 2 -- the
    fleet-unit convention actually implemented in this codebase (A32).
"""
import argparse

import numpy as np
import pandas as pd

from pipeline import options, sessions, signals, stats
from pipeline.units import _gh

MOD_1000 = 10 * 60          # 600
MOD_0931 = 9 * 60 + 31      # 571
TIMING_LO, TIMING_HI = MOD_0931, 15 * 60     # 09:31..15:00, inclusive, integer minutes
Q_LO, Q_HI = 0.10, 0.90
MIN_PRIOR_SESSIONS = 250    # no fitted parameter (A39)
COST1, COST2 = 1.0, 2.0     # SPX points round trip (base / reported sensitivity)
OPT_K = 1.3                 # option leg IV = OPT_K * prior-close VIX (as in D4)
N_SEEDS = 200
CONTROL_SEED = 11           # day-selection control (specified by the caller)
TIMING_SEED = 7             # timing control; arbitrary fixed constant, distinct from 11 (see docstring)
DSR_N = 37                  # 3 trials this run + 34 already in the run's family (A38/A39 amendment text)
WINDOWS = [("CONTEXT", "2005-01-01", "2012-12-31"),
           ("SELECTION", "2013-01-01", "2020-05-13"),
           ("HOLDOUT", "2020-07-27", "2026-09-11")]
# name, signal column, entry-price column, direction (+1 call / -1 put), option kind, entry_time label
TRIALS = [("T1", "sig_lo", "px_1000", 1.0, "c", "10:00"),
          ("T2", "sig_lo", "px_0931", 1.0, "c", "09:31"),
          ("T3", "sig_hi", "px_1000", -1.0, "p", "10:00")]
OUT_COLS = ["window", "trial", "side", "entry_time", "n_signal_days", "n_skipped", "n", "win",
            "net_pts_cost1", "net_pts_cost2", "net_pct_cost1", "net_pct_cost2",
            "median_net_pts_cost1", "worst_trade_pts_cost1", "worst_day_pts_cost1",
            "sharpe_calday", "p_boot_day", "p_boot_month",
            "control_mean_pts_cost1", "frac_seeds_beaten",
            "timing_control_pts_cost1", "frac_timing_beaten",
            "opt_mean_pct_s1", "dsr_N37", "spec"]
TRADE_COLS = ["window", "trial", "date", "entry_px", "exit_px", "net_pts_cost1"]

SPEC_NOTE = (
    "FIXED (pre-registration, A39): signal = overnight return (prior session's last RTH close -> "
    "this session's first RTH open) <= the expanding 10th percentile (T1/T2) / >= the expanding "
    "90th percentile (T3, mirror) of overnight returns over all strictly prior sessions, min 250 "
    "prior sessions, no fitted parameter. T1 long call entry 10:00 bar close; T2 same days as T1, "
    "long call entry 09:31 bar close; T3 mirror signal, long put, entry 10:00 bar close; all exit "
    "at the 16:00 close. Costs 1.0/2.0 pts. A session trades only if BOTH the 10:00 and 09:31 bars "
    "are present (else n_skipped); overnight return uses signals.day_table's dividend-adjusted, "
    "roll-day-excluded prior close, and the percentile thresholds expand across the whole history, "
    "never resetting at a window boundary. Day-selection control: 200 draws from one generator "
    "seeded 11, same-count random non-signal both-bars-eligible sessions, same fixed entry/exit. "
    "Timing control: same real trade days, 200 draws from one generator seeded 7, entry at a "
    "uniformly random integer minute in [09:31,15:00] (bar close), exit 16:00. Option leg: 2% ITM, "
    "k=1.3 x prior-close VIX, 1 pt spread, cash settle (pipeline.options.trade_table), priced on "
    "the real trades only. DSR at N=37 (3 trials this run + 34 already in the family) uses the "
    "per-trade-Sharpe dispersion of THIS RUN'S OWN 3 trials in the same window as SR0's pool (the "
    "other 34 trials are not available to this standalone unit). Windows: CONTEXT "
    "2005-01-01..2012-12-31, SELECTION 2013-01-01..2020-05-13, HOLDOUT 2020-07-27..2026-09-11.")


def build_day_table(frame, vix, meta, td):
    """One row per session: signals.day_table's usual columns (open = first RTH bar's open, close
    = last RTH bar's close = the 16:00 print, prev_close = dividend-adjusted, ref_ok, vix_prev)
    plus the 10:00/09:31 bar closes, the both-bars eligibility flag, the overnight return and the
    two expanding signal flags."""
    day = signals.day_table(frame, vix, dividends=meta["dividends"] if meta else None,
                            trading_days=td, roll_dates=meta["roll_dates"] if meta else ())
    px_1000 = frame.loc[frame["mod"] == MOD_1000].groupby("date")["close"].first()
    px_0931 = frame.loc[frame["mod"] == MOD_0931].groupby("date")["close"].first()
    day["px_1000"] = px_1000.reindex(day.index)
    day["px_0931"] = px_0931.reindex(day.index)
    day["both_bars"] = day["px_1000"].notna() & day["px_0931"].notna()
    day["overnight_ret"] = np.where(day["ref_ok"], day["open"] / day["prev_close"] - 1, np.nan)
    thr_lo = signals.expanding_threshold(day["overnight_ret"], q=Q_LO, min_prior=MIN_PRIOR_SESSIONS)
    thr_hi = signals.expanding_threshold(day["overnight_ret"], q=Q_HI, min_prior=MIN_PRIOR_SESSIONS)
    day["sig_lo"] = day["overnight_ret"] <= thr_lo
    day["sig_hi"] = day["overnight_ret"] >= thr_hi
    return day


def build_trades(day, dates, entry_col, direction, kind):
    """One row per eligible signal day: entry/exit prices and points, plus the option-leg inputs
    (entry_mod/exit_mod/vix_prev/kind) for pipeline.options.trade_table."""
    d = day.loc[dates]
    entry_px = d[entry_col].to_numpy(float)
    exit_px = d["close"].to_numpy(float)
    pts = direction * (exit_px - entry_px)
    ret_pct = direction * (exit_px / entry_px - 1) * 100
    entry_mod = MOD_1000 if entry_col == "px_1000" else MOD_0931
    return pd.DataFrame(dict(date=pd.DatetimeIndex(dates), entry_px=entry_px, exit_px=exit_px,
                             pts=pts, ret_pct=ret_pct, entry_mod=entry_mod,
                             exit_mod=d["last_mod"].to_numpy(), vix_prev=d["vix_prev"].to_numpy(), kind=kind))


def day_selection_control(day, start_ts, end_ts, sig_col, entry_col, direction, cost, n_trades,
                          n_seeds=N_SEEDS, seed=CONTROL_SEED):
    """A16: 200 draws from one seeded generator over the window's non-signal, both-bars-eligible
    sessions, same fixed entry/exit as the matched trial (net of `cost`). Returns the per-seed
    mean net pts array (empty when there is no matched trade or not enough sessions to draw from)."""
    w = day[(day.index >= start_ts) & (day.index <= end_ts) & day["both_bars"] & ~day[sig_col]]
    if n_trades == 0 or len(w) < n_trades:
        return np.array([])
    entry, exitp = w[entry_col].to_numpy(float), w["close"].to_numpy(float)
    pts = direction * (exitp - entry) - cost
    rng = np.random.default_rng(seed)
    return np.array([pts[rng.choice(len(w), n_trades, replace=False)].mean() for _ in range(n_seeds)])


def timing_control(frame, day, dates, direction, cost, n_seeds=N_SEEDS, seed=TIMING_SEED):
    """Same real trade days, entry at a uniformly random integer minute-of-day in
    [09:31,15:00] (bar close), exit at 16:00 close, net of `cost`. 200 draws from one seeded
    generator. Returns the per-seed mean net pts array (empty when there are no matched days)."""
    if len(dates) == 0:
        return np.array([])
    mods = np.arange(TIMING_LO, TIMING_HI + 1)
    piv = (frame[(frame["mod"] >= TIMING_LO) & (frame["mod"] <= TIMING_HI)]
          .pivot(index="date", columns="mod", values="close").reindex(index=pd.DatetimeIndex(dates), columns=mods))
    vals = piv.to_numpy(float)
    exitp = day.loc[dates, "close"].to_numpy(float)
    n = len(dates)
    rng = np.random.default_rng(seed)
    out = np.empty(n_seeds)
    for s in range(n_seeds):
        cols = rng.integers(0, len(mods), size=n)
        entry = vals[np.arange(n), cols]
        pts = direction * (exitp - entry) - cost
        out[s] = np.nanmean(pts) if np.isfinite(pts).any() else np.nan
    return out


def summarize(win_name, name, side, entry_time, day, start_ts, end_ts, sig_col, entry_col, direction, kind, frame, td):
    w = day[(day.index >= start_ts) & (day.index <= end_ts)]
    sig = w[w[sig_col]]
    n_signal_days = len(sig)
    elig_dates = sig.index[sig["both_bars"]]
    n_skipped = n_signal_days - len(elig_dates)
    trades = build_trades(day, elig_dates, entry_col, direction, kind)
    n = len(trades)
    trades["net_pts_cost1"] = trades["pts"] - COST1
    trades["net_pts_cost2"] = trades["pts"] - COST2
    trades["net_pct_cost1"] = trades["ret_pct"] - 100 * COST1 / trades["entry_px"]
    trades["net_pct_cost2"] = trades["ret_pct"] - 100 * COST2 / trades["entry_px"]
    net_pct1 = trades["net_pct_cost1"].to_numpy() if n else np.array([])
    all_dates = [d for d in td if start_ts <= d <= end_ts]
    row = dict(window=win_name, trial=name, side=side, entry_time=entry_time,
               n_signal_days=n_signal_days, n_skipped=n_skipped, n=n,
               win=(100 * (trades["pts"] > 0).mean()) if n else np.nan,
               net_pts_cost1=trades["net_pts_cost1"].mean() if n else np.nan,
               net_pts_cost2=trades["net_pts_cost2"].mean() if n else np.nan,
               net_pct_cost1=trades["net_pct_cost1"].mean() if n else np.nan,
               net_pct_cost2=trades["net_pct_cost2"].mean() if n else np.nan,
               median_net_pts_cost1=trades["net_pts_cost1"].median() if n else np.nan,
               worst_trade_pts_cost1=trades["net_pts_cost1"].min() if n else np.nan,
               worst_day_pts_cost1=trades.groupby("date")["net_pts_cost1"].sum().min() if n else np.nan)
    row["sharpe_calday"] = stats.calendar_day_sharpe(net_pct1, trades["date"], all_dates)
    row["p_boot_day"] = stats.one_sided_p(net_pct1, stats.day_blocks(trades["date"])) if n else np.nan
    row["p_boot_month"] = stats.one_sided_p(net_pct1, stats.month_blocks(trades["date"])) if n else np.nan
    ctrl_pts = day_selection_control(day, start_ts, end_ts, sig_col, entry_col, direction, COST1, n)
    valid = ~np.isnan(ctrl_pts) if len(ctrl_pts) else np.array([], dtype=bool)
    row["control_mean_pts_cost1"] = float(np.nanmean(ctrl_pts)) if valid.any() else np.nan
    row["frac_seeds_beaten"] = float(np.mean(row["net_pts_cost1"] > ctrl_pts[valid])) if (n and valid.any()) else np.nan
    tim_pts = timing_control(frame, day, trades["date"].to_numpy(), direction, COST1) if n else np.array([])
    tvalid = ~np.isnan(tim_pts) if len(tim_pts) else np.array([], dtype=bool)
    row["timing_control_pts_cost1"] = float(np.nanmean(tim_pts)) if tvalid.any() else np.nan
    row["frac_timing_beaten"] = float(np.mean(row["net_pts_cost1"] > tim_pts[tvalid])) if (n and tvalid.any()) else np.nan
    if n:
        opt_in = trades[["entry_px", "exit_px", "entry_mod", "exit_mod", "vix_prev", "kind"]]
        o = options.trade_table(opt_in, k=OPT_K, itm=0.02, spread_pts=1.0, grid=options.GRID["SPX"], settle="cash")
        row["opt_mean_pct_s1"] = float(o["opt_ret"].mean() * 100) if len(o) else np.nan
    else:
        row["opt_mean_pct_s1"] = np.nan
    row["spec"] = SPEC_NOTE
    return row, trades, net_pct1


def main(inp, out):
    if inp != "extended":
        raise ValueError(f"pipeline.units.gapliq only supports --in extended (got {inp!r})")
    td = sessions.trading_days_from_vix()
    frame, _dropped, meta = sessions.build_extended(trading_days=td)
    vix = pd.read_parquet("data/raw/vix_daily.parquet")
    day = build_day_table(frame, vix, meta, td)

    rows, trade_frames = [], []
    for win_name, start, end in WINDOWS:
        start_ts, end_ts = pd.Timestamp(start), pd.Timestamp(end)
        win_rows, win_nets, win_trades = [], [], []
        for name, sig_col, entry_col, direction, kind, entry_time in TRIALS:
            side = "call" if kind == "c" else "put"
            row, trades, net_pct1 = summarize(win_name, name, side, entry_time, day, start_ts, end_ts,
                                              sig_col, entry_col, direction, kind, frame, td)
            win_rows.append(row)
            win_nets.append(net_pct1)
            win_trades.append(trades.assign(window=win_name, trial=name)[TRADE_COLS])
        sr_pool = [stats.per_trade_sharpe(x) for x in win_nets]
        for row, x in zip(win_rows, win_nets):
            if len(x) >= 3:
                dsr, _, _ = stats.deflated_sharpe(x, sr_trials=sr_pool, n=DSR_N)
            else:
                dsr = np.nan
            row["dsr_N37"] = dsr
        rows.extend(win_rows)
        trade_frames.extend(win_trades)

    res = pd.DataFrame(rows)[OUT_COLS]
    res.to_csv(out, index=False, float_format="%.6f")
    trades_path = out[:-4] + "_trades.csv" if out.endswith(".csv") else out + "_trades.csv"
    tr_all = pd.concat(trade_frames, ignore_index=True) if trade_frames else pd.DataFrame(columns=TRADE_COLS)
    tr_all[TRADE_COLS].to_csv(trades_path, index=False, float_format="%.6f")
    print(res.to_string(index=False, float_format=lambda x: f"{x:.4f}"))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", default="extended")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    _gh.run(lambda: main(a.inp, a.out), a.out)
