"""Intraday forced-flattening rebound (A46, pre-registered 2026-09-15, before any run; amended by
A46a minutes later, before any code or result existed). Mechanism: accounts under daily loss
limits and margin calls are forced to flatten longs after a large morning decline; the forced
selling pushes price further down and then exhausts, so the hypothesis is a positive drift from
11:00 to the close on those days (U1), a WEAKER drift on a milder morning decline (U2, A46a's
causal dose-response fingerprint: the liquidation is claimed to be an EXTREME-morning effect) and
NO mirror effect after a large morning RISE (U3, mirror signal, put, must NOT be positive at 1
pt). This is the intraday analogue of A39's overnight version (`pipeline.units.gapliq`) and shares
its template; the trigger is disjoint from A39's (this session's open -> 11:00 move, not the
prior session's close -> open gap).

    python -m pipeline.units.flatten --in extended --out out/flatten_candidates.csv

3 trials, all counted (A46/A46a): U1 = long call, entry 11:00 bar close, exit 16:00 close, on days
where the open->11:00 return (09:30 session open -> 11:00 bar close) is <= the expanding 10th
percentile of that same measure over all prior sessions (min 250 prior sessions, no fitted
parameter); U2 = long call, entry 11:00, exit 16:00, on days where the same measure is <= the
expanding 30th percentile AND > the expanding 10th percentile (disjoint from U1 by construction,
A46a's replacement for the registered-but-defective 09:45 timing fingerprint -- see point (1)
below); U3 = mirror signal (open->11:00 return >= the expanding 90th percentile), long put, entry
11:00 bar close, exit 16:00. Reported on three windows (CONTEXT 2005-01-01..2012-12-31, SELECTION
2013-01-01..2020-05-13, HOLDOUT 2020-07-27..2026-09-11) on the extended frame
(sessions.build_extended, Oanda SPX + the ext feed, both already in SPX points); the verdict is on
HOLDOUT (A46). No parameter is swept beyond the three trials; the 10th/30th/90th percentile, the
250-session minimum and the 11:00 entry time are FIXED by the pre-registration and never varied.
Promotion (ACCEPTANCE's kill/promotion rule) is judged in `pipeline/report.py` from this file's
own columns, never re-typed.

Every ambiguity the amendment left open is fixed here and restated in the `spec` column
(SPEC_NOTE below); the ones worth flagging:
(1) A46's registered U2 (entry 09:45, on the same days as U1) was look-ahead: the gate does not
    complete until the 11:00 bar closes, so a 09:45 entry could not be traded on that signal at
    all. A46a replaced it, before any code or result existed, with the causal mild-decline band
    defined above; U2 still enters at 11:00, same as U1/U3.
(2) A session is eligible for ANY of the three trials only if BOTH the 11:00 bar and the 16:00
    close are present (most conservative reading of "sessions with missing 11:00 or close bars
    are skipped"); sessions failing this gate are counted in `n_skipped`, not dropped silently.
    In practice this can only bind on the close (always present in `signals.day_table`) since a
    missing 11:00 bar already makes `ret_to_1100` NaN and therefore signals nothing -- the check
    is kept explicit anyway, matching gapliq's own defensive convention.
(3) Open->11:00 return uses `signals.day_table`'s "open" column (the first RTH bar's open, i.e.
    the session's 09:30 open per that table's own docstring) with no prior-close reference needed
    (unlike A39's overnight gap): both legs of the measure belong to the SAME session, so there is
    no dividend/roll-day reference-close problem to gate on.
(4) The 10th/30th/90th percentile thresholds expand across the WHOLE history (via `signals.
    expanding_threshold`, min_prior=250), never resetting at a window boundary -- same convention
    as gapliq and the D1 gates; only the reported ROWS are filtered by window.
(5) Day-selection control (A16): 200 draws from ONE generator seeded 11 (matching gapliq's
    convention); pool = the window's eligible sessions carrying NONE of U1/U2/U3 (not just the
    matched trial's own signal -- unlike gapliq's two-signal case, three bands here partition both
    tails and the mild-decline middle, so "no signal" must mean none of the three), same fixed
    11:00 entry / 16:00 exit as the matched trial.
(6) Timing control: same real trade days, entry at a uniformly random INTEGER minute-of-day in
    [09:31,15:00] (bar close, reusing gapliq's TIMING_LO/TIMING_HI), exit at 16:00 close, same
    direction/cost. TIMING_SEED is gapliq's own arbitrary fixed constant (distinct from 11),
    reused here for the same reason gapliq chose it: determinism, nothing else.
(7) Option leg (2% ITM, k=1.3 x prior-close VIX, 1 pt spread, cash settle) is priced on the REAL
    trades only, via `pipeline.options.trade_table`, same convention as gapliq/D4/insample.py.
    Entry at 11:00 (never before 10:00) satisfies A45 rule 2; the 2% ITM strike satisfies A45
    rule 3 (ACCEPTANCE.md's owner rulebook).
(8) On any exception this unit follows `pipeline.units._gh.run` exactly as gapliq.py/fvg.py/
    flow.py do: an empty (zero-byte) output file plus `<out>.error` with the traceback, exit code
    2 -- the fleet-unit convention actually implemented in this codebase (A32).
"""
import argparse

import numpy as np
import pandas as pd

from pipeline import options, sessions, signals, stats
from pipeline.units import _gh

MOD_1100 = 11 * 60         # 660 (11:00 bar close)
MOD_0931 = 9 * 60 + 31     # 571 (timing control lower bound, reused from gapliq)
TIMING_LO, TIMING_HI = MOD_0931, 15 * 60     # 09:31..15:00, inclusive, integer minutes
Q_LO, Q_MILD, Q_HI = 0.10, 0.30, 0.90
MIN_PRIOR_SESSIONS = 250   # no fitted parameter (A46, same warm-up as A39)
COST1, COST2 = 1.0, 2.0    # SPX points round trip (base / reported sensitivity)
OPT_K = 1.3                # option leg IV = OPT_K * prior-close VIX (as in D4/gapliq)
N_SEEDS = 200
CONTROL_SEED = 11          # day-selection control (reused from gapliq)
TIMING_SEED = 7            # timing control; arbitrary fixed constant, distinct from 11 (see docstring)
DSR_N = 45                 # fixed by A46/A46a ("DSR at N = 45")
WINDOWS = [("CONTEXT", "2005-01-01", "2012-12-31"),
           ("SELECTION", "2013-01-01", "2020-05-13"),
           ("HOLDOUT", "2020-07-27", "2026-09-11")]
# name, signal column, direction (+1 call / -1 put), option kind, entry_time label
TRIALS = [("U1", "sig_u1", 1.0, "c", "11:00"),
          ("U2", "sig_u2", 1.0, "c", "11:00"),
          ("U3", "sig_u3", -1.0, "p", "11:00")]
OUT_COLS = ["window", "trial", "side", "entry_time", "n_signal_days", "n_skipped", "n", "win",
            "net_pts_cost1", "net_pts_cost2", "net_pct_cost1", "net_pct_cost2",
            "median_net_pts_cost1", "worst_trade_pts_cost1", "worst_day_pts_cost1",
            "sharpe_calday", "p_boot_day", "p_boot_month",
            "control_mean_pts_cost1", "frac_seeds_beaten",
            "timing_control_pts_cost1", "frac_timing_beaten",
            "opt_mean_pct_s1", "dsr_N45", "spec"]
TRADE_COLS = ["window", "trial", "date", "entry_px", "exit_px", "net_pts_cost1"]

SPEC_NOTE = (
    "FIXED (pre-registration, A46/A46a): signal = open->11:00 return (09:30 session open -> 11:00 "
    "bar close) vs the expanding percentile of that same measure over all strictly prior sessions "
    "(min 250 prior sessions, no fitted parameter). U1 = ret_to_1100 <= expanding 10th pct (the "
    "hypothesis); U2 = ret_to_1100 <= expanding 30th pct AND > expanding 10th pct (A46a's causal "
    "mild-decline dose-response band, disjoint from U1 by construction, replacing the look-ahead "
    "09:45 timing fingerprint the amendment first registered); U3 = ret_to_1100 >= expanding 90th "
    "pct (mirror signal). All three enter long at the 11:00 bar close (U1/U2 call, U3 put) and "
    "exit at the 16:00 session close. Costs 1.0/2.0 pts. A session trades only if both the 11:00 "
    "bar and the 16:00 close are present (else n_skipped); the percentile thresholds expand across "
    "the whole history, never resetting at a window boundary. Day-selection control: 200 draws "
    "from one generator seeded 11, pool = eligible sessions in the window carrying NONE of "
    "U1/U2/U3, same fixed 11:00 entry / 16:00 exit. Timing control: same real trade days, 200 "
    "draws from one generator seeded 7, entry at a uniformly random integer minute in "
    "[09:31,15:00] (bar close), exit 16:00. Option leg: 2% ITM, k=1.3 x prior-close VIX, 1 pt "
    "spread, cash settle (pipeline.options.trade_table), priced on the real trades only. Entry at "
    "11:00 (not before 10:00) satisfies A45 rule 2; the 2% ITM strike satisfies A45 rule 3. DSR at "
    "N=45 (A46/A46a) uses the per-trade-Sharpe dispersion of THIS RUN'S OWN 3 trials in the same "
    "window as SR0's pool (the wider family is not available to this standalone unit). Windows: "
    "CONTEXT 2005-01-01..2012-12-31, SELECTION 2013-01-01..2020-05-13, HOLDOUT "
    "2020-07-27..2026-09-11; the verdict is on HOLDOUT.")


def compute_thresholds(ret):
    """The three expanding-percentile thresholds (10th/30th/90th) the gate reads, each already
    shifted by one session by `signals.expanding_threshold` so only STRICTLY PRIOR sessions feed
    today's threshold (min 250 prior sessions, no fitted parameter)."""
    thr_lo = signals.expanding_threshold(ret, q=Q_LO, min_prior=MIN_PRIOR_SESSIONS)
    thr_mild = signals.expanding_threshold(ret, q=Q_MILD, min_prior=MIN_PRIOR_SESSIONS)
    thr_hi = signals.expanding_threshold(ret, q=Q_HI, min_prior=MIN_PRIOR_SESSIONS)
    return thr_lo, thr_mild, thr_hi


def compute_bands(ret):
    """The three disjoint signal bands from the day measure `ret` (open->11:00 return): U1 <= the
    10th pct; U2 in (10th pct, 30th pct] (A46a's mild-decline dose-response band); U3 >= the 90th
    pct (mirror). Disjoint by construction since the 10th/30th/90th percentiles of one series are
    non-decreasing in q."""
    thr_lo, thr_mild, thr_hi = compute_thresholds(ret)
    sig_u1 = ret <= thr_lo
    sig_u2 = (ret <= thr_mild) & (ret > thr_lo)
    sig_u3 = ret >= thr_hi
    return sig_u1, sig_u2, sig_u3


def build_day_table(frame, vix, meta, td):
    """One row per session: signals.day_table's usual columns (open = first RTH bar's open, close
    = last RTH bar's close = the 16:00 print, vix_prev) plus the 11:00 bar close, the eligibility
    flag, the open->11:00 return and the three disjoint expanding-percentile signal bands."""
    day = signals.day_table(frame, vix, dividends=meta["dividends"] if meta else None,
                            trading_days=td, roll_dates=meta["roll_dates"] if meta else ())
    px_1100 = frame.loc[frame["mod"] == MOD_1100].groupby("date")["close"].first()
    day["px_1100"] = px_1100.reindex(day.index)
    day["elig"] = day["px_1100"].notna() & day["close"].notna()
    day["ret_to_1100"] = day["px_1100"] / day["open"] - 1
    day["sig_u1"], day["sig_u2"], day["sig_u3"] = compute_bands(day["ret_to_1100"])
    return day


def build_trades(day, dates, direction, kind):
    """One row per eligible signal day: entry (11:00 bar close) and exit (16:00 session close)
    prices and points, plus the option-leg inputs (entry_mod/exit_mod/vix_prev/kind) for
    pipeline.options.trade_table."""
    d = day.loc[dates]
    entry_px = d["px_1100"].to_numpy(float)
    exit_px = d["close"].to_numpy(float)
    pts = direction * (exit_px - entry_px)
    ret_pct = direction * (exit_px / entry_px - 1) * 100
    return pd.DataFrame(dict(date=pd.DatetimeIndex(dates), entry_px=entry_px, exit_px=exit_px,
                             pts=pts, ret_pct=ret_pct, entry_mod=MOD_1100,
                             exit_mod=d["last_mod"].to_numpy(), vix_prev=d["vix_prev"].to_numpy(), kind=kind))


def day_selection_control(day, start_ts, end_ts, direction, cost, n_trades,
                          n_seeds=N_SEEDS, seed=CONTROL_SEED):
    """A16: 200 draws from one seeded generator over the window's eligible sessions carrying NONE
    of U1/U2/U3, same fixed 11:00 entry / 16:00 exit as the matched trial (net of `cost`). Returns
    the per-seed mean net pts array (empty when there is no matched trade or not enough sessions
    to draw from)."""
    w = day[(day.index >= start_ts) & (day.index <= end_ts) & day["elig"]
            & ~day["sig_u1"] & ~day["sig_u2"] & ~day["sig_u3"]]
    if n_trades == 0 or len(w) < n_trades:
        return np.array([])
    entry, exitp = w["px_1100"].to_numpy(float), w["close"].to_numpy(float)
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


def summarize(win_name, name, side, entry_time, day, start_ts, end_ts, sig_col, direction, kind, frame, td):
    w = day[(day.index >= start_ts) & (day.index <= end_ts)]
    sig = w[w[sig_col]]
    n_signal_days = len(sig)
    elig_dates = sig.index[sig["elig"]]
    n_skipped = n_signal_days - len(elig_dates)
    trades = build_trades(day, elig_dates, direction, kind)
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
    ctrl_pts = day_selection_control(day, start_ts, end_ts, direction, COST1, n)
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
        raise ValueError(f"pipeline.units.flatten only supports --in extended (got {inp!r})")
    td = sessions.trading_days_from_vix()
    frame, _dropped, meta = sessions.build_extended(trading_days=td)
    vix = pd.read_parquet("data/raw/vix_daily.parquet")
    day = build_day_table(frame, vix, meta, td)

    rows, trade_frames = [], []
    for win_name, start, end in WINDOWS:
        start_ts, end_ts = pd.Timestamp(start), pd.Timestamp(end)
        win_rows, win_nets, win_trades = [], [], []
        for name, sig_col, direction, kind, entry_time in TRIALS:
            side = "call" if kind == "c" else "put"
            row, trades, net_pct1 = summarize(win_name, name, side, entry_time, day, start_ts, end_ts,
                                              sig_col, direction, kind, frame, td)
            win_rows.append(row)
            win_nets.append(net_pct1)
            win_trades.append(trades.assign(window=win_name, trial=name)[TRADE_COLS])
        sr_pool = [stats.per_trade_sharpe(x) for x in win_nets]
        for row, x in zip(win_rows, win_nets):
            if len(x) >= 3:
                dsr, _, _ = stats.deflated_sharpe(x, sr_trials=sr_pool, n=DSR_N)
            else:
                dsr = np.nan
            row["dsr_N45"] = dsr
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
