"""0DTE dealer-hedging flow impulse (A49, pre-registered 2026-09-16, before any code; 3 trials,
family 45 -> 48). Mechanism: a dealer who absorbs a large directional 0DTE customer order is
immediately short or long delta and must hedge in the underlying before the close (same-day
expiry removes every other option), so the forced hedge is concentrated in the MINUTES after the
customer order and pushes the underlying in the direction of that customer's delta.

    python -m pipeline.units.oflow --in extended --out out/oflow_candidates.csv

3 trials, all counted (A49): T1 = per-minute tick-rule imbalance >= the expanding 90th percentile
of |imbalance| over all minutes of strictly prior sessions (min 100 prior sessions) -> long 2%
ITM call, entry at the NEXT minute's close, exit 30 minutes later; T2 = same signal, entry delayed
15 minutes (entry at signal_minute + 16, exit 30 minutes after THAT entry -- must be WEAKER than
T1, the timing fingerprint); T3 = imbalance <= -the threshold -> long 2% ITM put, same horizon as
T1 (the mirror; must ALSO work, since dealer hedging is symmetric by construction). Non-
overlapping per trial: no new entry while a position from that SAME trial is open; the first
qualifying minute after a position closes is taken. Reported on two windows (SELECTION
2024-02-01..2025-06-30, HOLDOUT 2025-07-01..2026-09-11, on the real `data/ext/
spy_0dte_1min_2024/2025/2026.csv.gz` shards for the signal and `sessions.build_extended` for
entries/exits/P&L, both already in SPX points); the verdict is on HOLDOUT. No parameter is swept
beyond the three trials; the 90th percentile, the 100-session minimum, the 1/16-minute entry lags
and the 30-minute horizon are FIXED by the pre-registration and never varied.

Every ambiguity A49 left open is fixed here and restated in the `spec` column (SPEC_NOTE below);
worth flagging up front:
(1) Session-boundary exit (A49 does not name this; the only causal option, stated here as the
    registered handling): if entry_mod + 30 would fall at or past the session's own last bar, the
    trade exits at that last bar instead (`frame.groupby('date')['mod'].max()`, not a hardcoded
    959 -- the same defensive per-session lookup flatten.py/gapliq.py use for `last_mod`, though
    in this window every session this unit ever trades happens to have its last bar at mod 959).
(2) A signal whose OWN entry (signal_minute + lag) would land AT OR PAST the session's last bar
    cannot be entered at all -- there is no bar left to buy. This is NOT the registered exit-
    boundary rule above (which only concerns the EXIT); it is a plain data-availability fact, and
    such a signal produces no trade and is counted in `n_skipped`, never silently dropped. The
    same `n_skipped` bucket also counts a signal minute whose entry or (post-clamp) exit bar is
    individually missing from the underlying minute frame (the real feed has occasional tickless
    minutes even inside RTH, sessions.py's own FULL_BARS comment).
(3) Tick rule "contract (strike+right+expiry) within a session": `expiry` is verified (0 mismatches
    across all ~9.48M rows of all three shards) to equal the session date read from `ts` on every
    row, so the session key IS that date, and grouping by (date, strike, right) is exactly
    grouping by (expiry, strike, right); `expiry` itself is not read at all (MEMORY, point 11).
(4) "Carry that contract's previous sign" on an equal-price print is implemented as forward-
    filling the last CLASSIFIED (+1/-1) sign within the (date, strike, right) group, not the raw
    previous close: a run of equal prices immediately after a session's very first print for that
    contract (itself unsigned -- no prior print) stays unsigned until a real price change first
    establishes a sign to carry. Only pandas' own groupby/ffill is used, never a hand-rolled loop.
(5) The gate's expanding threshold pools ALL MINUTES of every strictly prior session (not one
    value per session, unlike every existing `signals.expanding_threshold` caller), so that
    helper's shape does not fit here; `session_expanding_threshold` below mirrors its
    `.expanding(min_periods=N).quantile(q).shift(1)` semantics by hand, at SESSION granularity:
    the threshold for session d is the 90th percentile of every valid |imbalance| value from every
    minute of every session strictly before d, defined only once >= 100 such prior sessions exist.
(6) A49's Scoring paragraph says "day-selection control (random non-signal sessions, same
    entry/exit, 200 seeds)", reusing A39's/A46's own phrase verbatim -- but THIS signal fires at
    MINUTE granularity (several non-overlapping trades per session is normal), so there is no
    well-defined "same entry/exit" for an entire non-signal SESSION the way there is for a single
    hold-to-close trade. FLAGGED LOUDLY: this file reads it as the natural minute-granularity
    analogue of flatten.py's/gapliq.py's own day-selection control -- one seeded generator (11),
    200 draws WITHOUT replacement from the window's threshold-defined minutes carrying NEITHER
    sig_bull NOR sig_bear (mirroring flatten's "carrying none of U1/U2/U3" pool exclusion exactly,
    generalised to minutes), each entered/exited with the MATCHED trial's own fixed lag/hold, net
    of cost -- NOT a per-session draw. This is an unregistered interpretive choice, not a literal
    reading of A49's own text, because the literal session-level reading has no operational
    meaning for a signal that fires many times inside one session.
(7) Timing control: same real trades' session dates, entry replaced by a uniformly random integer
    minute in [sessions.RTH_START, last_mod) (a real, tradeable bar strictly before the session's
    own last bar), held for the SAME 30-minute duration as the matched trial (identical session-
    boundary clamp), same direction/cost; 200 draws from one seeded generator (7, A39's/A46's own
    arbitrary constant, distinct from 11). Read literally as "random entry minute" -- the entry
    ITSELF is randomised, not a random signal minute plus the matched trial's own lag.
(8) Option leg (2% ITM, k=1.3 x prior-close VIX, 1 pt spread, cash settle,
    `pipeline.options.trade_table`) priced on the real trades only, same convention as every
    sibling unit (A45 rules 2/3: entry never before 10:00 is not at issue here -- these are
    intraday impulse entries, not a fixed clock time -- and the 2% ITM strike satisfies rule 3).
(9) DSR at N=48 (A49's own "family 45 -> 48" text) uses THIS RUN'S OWN 3 trials' per-trade Sharpe
    in the SAME window as the SR0 pool (flatten.py's/gapliq.py's own convention; the other 45
    trials already in the family are not available to this standalone unit).
(10) On any exception this unit follows `pipeline.units._gh.run` exactly as flatten.py/gapliq.py
    do: an empty output file plus `<out>.error` with the traceback, exit code 2 (A32) -- unlike
    eventvol.py's/sellvol.py's A38 header-only-exit-0 contract, because the data this unit needs
    (`data/ext/spy_0dte_1min_*.csv.gz`) already exists on this branch (A49's own feasibility
    check ran before registration).
(11) MEMORY: the three shards (~9.5M rows total, ~9.48M after the RTH filter) are read and reduced
    to a per-(date, minute) table ONE FILE AT A TIME (`build_minute_flow`) -- the raw per-print
    frame for a shard (up to ~3.8M rows, the 2025 file) is discarded before the next shard is
    read, so peak memory is bounded by the LARGEST single shard, never the sum of all three.
"""
import argparse
import glob

import numpy as np
import pandas as pd

from pipeline import options, sessions, signals, stats
from pipeline.units import _gh

NY = sessions.NY
DATA_GLOB = "data/ext/spy_0dte_1min_*.csv.gz"
REQUIRED_COLS = {"ts", "strike", "right", "close", "volume"}

Q_GATE = 0.90               # the gate's expanding percentile (A49, no fitted parameter)
MIN_PRIOR_SESSIONS = 100    # A49's own warm-up minimum
LAG_T1 = 1                  # T1/T3 entry = signal minute + 1 (the NEXT minute's close)
LAG_T2 = 16                 # T2 entry = signal minute + 16 (15 minutes later than T1, A49)
HOLD = 30                   # minutes held after entry, all three trials (A49, fixed horizon)
COST1, COST2 = 1.0, 2.0     # SPX points round trip (base / reported sensitivity)
OPT_K = 1.3                 # option leg IV = OPT_K x prior-close VIX (as in D4/flatten/gapliq)
N_SEEDS = 200
CONTROL_SEED = 11           # day-selection (here: minute-selection) control
TIMING_SEED = 7             # timing control; arbitrary fixed constant, distinct from 11 (A39/A46)
DSR_N = 48                  # A49's own "family 45 -> 48"
WINDOWS = [("SELECTION", "2024-02-01", "2025-06-30"), ("HOLDOUT", "2025-07-01", "2026-09-11")]
# name, gate column, direction (+1 call / -1 put), option kind, entry lag (minutes after signal)
TRIALS = [("T1", "sig_bull", 1.0, "c", LAG_T1),
          ("T2", "sig_bull", 1.0, "c", LAG_T2),
          ("T3", "sig_bear", -1.0, "p", LAG_T1)]
OUT_COLS = ["window", "trial", "side", "entry_lag", "n_signal_minutes", "n_skipped", "n_overlap_skipped",
            "n", "win", "net_pts_cost1", "net_pts_cost2", "net_pct_cost1", "net_pct_cost2",
            "median_net_pts_cost1", "worst_trade_pts_cost1", "worst_day_pts_cost1",
            "sharpe_calday", "p_boot_day", "p_boot_month",
            "control_mean_pts_cost1", "frac_seeds_beaten",
            "timing_control_pts_cost1", "frac_timing_beaten",
            "opt_mean_pct_s1", "dsr_N48", "spec"]
TRADE_COLS = ["window", "trial", "date", "signal_mod", "entry_mod", "exit_mod", "entry_px", "exit_px", "net_pts_cost1"]

SPEC_NOTE = (
    "FIXED (pre-registration, A49): per contract (strike+right+expiry key, expiry verified equal "
    "to the ts-derived session date on every row of every shard, so expiry is not even read) "
    "within a session, sign each minute's volume by the tick rule against that contract's most "
    "recent PRIOR print in the same session (higher close -> buyer-initiated, lower -> seller-"
    "initiated, equal -> carry the last CLASSIFIED sign via forward-fill, no prior print -> "
    "unsigned and excluded). Aggregate per (date, minute): bullish = buyer-initiated call volume + "
    "seller-initiated put volume; bearish = seller-initiated call volume + buyer-initiated put "
    "volume; imbalance = (bullish-bearish)/(bullish+bearish), NaN when the denominator is 0. Gate: "
    "|imbalance| >= the expanding 90th percentile of |imbalance| pooled over ALL MINUTES of "
    "strictly prior sessions (min 100 prior sessions, no fitted parameter) -- mirrored by hand at "
    "session granularity since signals.expanding_threshold assumes one value per row. T1 = "
    "imbalance >= +threshold -> long 2% ITM call, entry at the next minute's close, exit 30 "
    "minutes later; T2 = same signal, entry delayed 15 minutes (signal_minute+16, exit 30 minutes "
    "after that entry); T3 = imbalance <= -threshold -> long 2% ITM put, same horizon as T1. Non-"
    "overlapping per trial (no new entry while that trial's own position is open; the first "
    "qualifying minute after a close is taken). Session-boundary exit (A49 does not name this, the "
    "only causal option): an exit past the session's own last bar clamps to that last bar instead; "
    "a signal whose OWN entry would land at/past the last bar produces no trade at all (n_skipped) "
    "-- entry cannot be clamped, only exit can. Costs 1.0/2.0 pts. Day-selection control (A16), "
    "adapted from flatten's/gapliq's per-SESSION draw to per-MINUTE (flagged as an unregistered "
    "interpretive choice -- this signal has no session-level 'same entry/exit'): 200 draws from "
    "one generator seeded 11 over the window's threshold-defined minutes carrying NEITHER sig_bull "
    "NOR sig_bear, each priced with the matched trial's own fixed lag/hold. Timing control: same "
    "real trade sessions, 200 draws from one generator seeded 7, entry at a uniformly random "
    "integer minute in [RTH_START, last_mod), held the same 30 minutes, same boundary clamp. "
    "Option leg: 2% ITM, k=1.3 x prior-close VIX, 1 pt spread, cash settle "
    "(pipeline.options.trade_table), priced on the real trades only. DSR at N=48 (family 45->48) "
    "uses this run's own 3 trials' per-trade Sharpe in the same window as the SR0 pool. Windows: "
    "SELECTION 2024-02-01..2025-06-30, HOLDOUT 2025-07-01..2026-09-11; the verdict is on HOLDOUT.")


def shard_paths(pattern=DATA_GLOB):
    return sorted(glob.glob(pattern))


def build_minute_flow(path):
    """One shard (~2.6-3.8M raw contract-minute rows) reduced to a per-(date, minute) bullish/
    bearish signed-volume table (~390 x ~230 rows) before the caller reads the next shard (module
    docstring point 11, MEMORY): read only the columns the tick rule needs (no `expiry`, module
    docstring point 3), restrict to the RTH minutes this signal ever trades
    (`sessions.RTH_START`..`sessions.RTH_END`), sign every print against that same (date, strike,
    right) contract's most recent PRIOR print (module docstring point 4), then sum the bullish/
    bearish leg per (date, minute) and let the raw per-print frame go out of scope."""
    df = pd.read_csv(path, usecols=["ts", "strike", "right", "close", "volume"])
    if REQUIRED_COLS - set(df.columns):
        raise ValueError(f"{path} missing required column(s): {sorted(REQUIRED_COLS - set(df.columns))}")
    ts = pd.DatetimeIndex(pd.to_datetime(df["ts"], utc=True)).tz_convert(NY)
    df["date"] = ts.tz_localize(None).normalize()
    df["mod"] = ts.hour * 60 + ts.minute
    df = df[(df["mod"] >= sessions.RTH_START) & (df["mod"] < sessions.RTH_END)].drop(columns=["ts"])
    df["right"] = df["right"].astype(str).str.upper()
    df["strike"] = df["strike"].astype("float32")
    df["close"] = df["close"].astype("float32")
    df["volume"] = df["volume"].astype("float64")
    df = df.sort_values(["date", "strike", "right", "mod"], kind="mergesort")
    keys = ["date", "strike", "right"]
    diff = df.groupby(keys, sort=False)["close"].diff()
    raw_sign = np.sign(diff)
    base = raw_sign.where(diff != 0)                        # equal-price rows masked to NaN (to be carried forward)
    df["sign"] = base.groupby([df["date"], df["strike"], df["right"]], sort=False).ffill()
    is_call = (df["right"] == "C").to_numpy()
    buyer, seller = (df["sign"] > 0).to_numpy(), (df["sign"] < 0).to_numpy()
    vol = df["volume"].to_numpy()
    bullish = np.where(buyer & is_call, vol, 0.0) + np.where(seller & ~is_call, vol, 0.0)
    bearish = np.where(seller & is_call, vol, 0.0) + np.where(buyer & ~is_call, vol, 0.0)
    minute = pd.DataFrame({"date": df["date"].to_numpy(), "mod": df["mod"].to_numpy(),
                          "bullish": bullish, "bearish": bearish})
    return minute.groupby(["date", "mod"], as_index=False)[["bullish", "bearish"]].sum()


def load_flow_table(paths):
    """Every shard's own small minute table (module docstring 11), concatenated -- never the raw
    per-print shards themselves, which `build_minute_flow` reads and discards one at a time."""
    parts = [build_minute_flow(p) for p in paths]
    flow = pd.concat(parts, ignore_index=True).sort_values(["date", "mod"]).reset_index(drop=True)
    denom = flow["bullish"] + flow["bearish"]
    flow["imbalance"] = np.where(denom > 0, (flow["bullish"] - flow["bearish"]) / denom, np.nan)
    return flow


def session_expanding_threshold(flow, q=Q_GATE, min_prior=MIN_PRIOR_SESSIONS):
    """A49's gate threshold, computed at SESSION granularity (module docstring point 5): the
    q-quantile of |imbalance| pooled across every minute of every STRICTLY PRIOR session, defined
    only once at least `min_prior` such sessions exist -- mirrors `signals.expanding_threshold`'s
    own `.expanding(min_periods=N).quantile(q).shift(1)` semantics by hand, since that helper
    assumes one value per row and this gate pools ~390 values per session. Returns a Series
    indexed by date (one threshold per session, broadcast onto every minute of that session by the
    caller via `.map`); causal by construction (a session's own minutes are appended to the pool
    only AFTER its own threshold is computed)."""
    abs_imb = flow["imbalance"].abs()
    by_date = {d: g.dropna().to_numpy() for d, g in abs_imb.groupby(flow["date"])}
    dates_sorted = sorted(by_date)
    pool, out = [], {}
    for i, d in enumerate(dates_sorted):
        if i >= min_prior:
            combined = np.concatenate(pool)
            out[d] = float(np.quantile(combined, q)) if len(combined) else np.nan
        else:
            out[d] = np.nan
        pool.append(by_date[d])
    return pd.Series(out)


def add_signals(flow, thr):
    """`thr_ok`/`sig_bull`/`sig_bear` from the session-level threshold Series (module docstring 5),
    broadcast onto every minute of its own session."""
    flow = flow.copy()
    flow["thr"] = flow["date"].map(thr)
    flow["thr_ok"] = flow["thr"].notna()
    flow["sig_bull"] = flow["thr_ok"] & (flow["imbalance"] >= flow["thr"])
    flow["sig_bear"] = flow["thr_ok"] & (flow["imbalance"] <= -flow["thr"])
    return flow


def build_trades(flow, sig_col, direction, kind, lag, last_mod, close_lookup, hold=HOLD):
    """One row per NON-OVERLAPPING trade for one trial (module docstring, non-overlap): candidate
    signal minutes are scanned in ascending order WITHIN each session (a trade can never span two
    sessions -- the exit is always clamped to that session's own last bar); a candidate is skipped
    -- never queued -- when its own entry would land inside a still-open position from this SAME
    trial (`n_overlap_skipped`, by design, not a data problem) OR at/past the session's last bar OR
    on a bar this run's own price grid does not have (`n_skipped`, module docstring points 1-2).
    Returns (trades_df, n_signal_minutes, n_skipped, n_overlap_skipped)."""
    sig = flow.loc[flow[sig_col], ["date", "mod"]].sort_values(["date", "mod"])
    n_signal_minutes = len(sig)
    rows, n_skipped, n_overlap_skipped = [], 0, 0
    for d, g in sig.groupby("date", sort=False):
        lm = last_mod.get(d)
        if lm is None or (isinstance(lm, float) and np.isnan(lm)):
            n_skipped += len(g)
            continue
        lm = int(lm)
        open_until = -1     # no position open yet; every real mod is >= sessions.RTH_START (570)
        for t in g["mod"].to_numpy():
            t = int(t)
            entry_mod = t + lag
            if entry_mod >= lm:                      # cannot enter after the session's last bar (point 2)
                n_skipped += 1
                continue
            if entry_mod < open_until:                # still inside this trial's own open position
                n_overlap_skipped += 1
                continue
            entry_px = close_lookup.get((d, entry_mod))
            if entry_px is None:
                n_skipped += 1
                continue
            exit_mod = min(entry_mod + hold, lm)       # session-boundary clamp (point 1)
            exit_px = close_lookup.get((d, exit_mod))
            if exit_px is None:
                n_skipped += 1
                continue
            rows.append((d, t, entry_mod, exit_mod, entry_px, exit_px))
            open_until = exit_mod
    cols = ["date", "signal_mod", "entry_mod", "exit_mod", "entry_px", "exit_px"]
    trades = pd.DataFrame(rows, columns=cols)
    if len(trades):
        for c in ("signal_mod", "entry_mod", "exit_mod", "entry_px", "exit_px"):
            trades[c] = trades[c].astype(float)
        trades["pts"] = direction * (trades["exit_px"] - trades["entry_px"])
        trades["ret_pct"] = direction * (trades["exit_px"] / trades["entry_px"] - 1) * 100
        trades["kind"] = kind
    else:
        for c in ("signal_mod", "entry_mod", "exit_mod", "entry_px", "exit_px", "pts", "ret_pct"):
            trades[c] = pd.Series(dtype=float)
        trades["kind"] = pd.Series(dtype=object)
        trades["date"] = pd.Series(dtype="datetime64[ns]")
    return trades, n_signal_minutes, n_skipped, n_overlap_skipped


def minute_selection_control(flow, start_ts, end_ts, direction, lag, cost, n_trades,
                             last_mod, close_lookup, n_seeds=N_SEEDS, seed=CONTROL_SEED):
    """A16, adapted to minute granularity (module docstring point 6): 200 draws from one seeded
    generator over the window's threshold-defined minutes carrying NEITHER sig_bull NOR sig_bear,
    each entered/exited with the matched trial's own fixed lag/hold (net of `cost`). Returns the
    per-seed mean net pts array (empty when there is no matched trade or too few priceable
    eligible minutes to draw `n_trades` from)."""
    w = flow[(flow["date"] >= start_ts) & (flow["date"] <= end_ts) & flow["thr_ok"]
            & ~flow["sig_bull"] & ~flow["sig_bear"]]
    if n_trades == 0 or len(w) == 0:
        return np.array([])
    dates, mods = w["date"].to_numpy(), w["mod"].to_numpy()
    pts = np.full(len(w), np.nan)
    for i in range(len(w)):
        d, t = dates[i], int(mods[i])
        lm = last_mod.get(d)
        if lm is None:
            continue
        lm = int(lm)
        entry_mod = t + lag
        if entry_mod >= lm:
            continue
        entry_px = close_lookup.get((d, entry_mod))
        if entry_px is None:
            continue
        exit_mod = min(entry_mod + HOLD, lm)
        exit_px = close_lookup.get((d, exit_mod))
        if exit_px is None:
            continue
        pts[i] = direction * (exit_px - entry_px) - cost
    pts_valid = pts[~np.isnan(pts)]
    if len(pts_valid) < n_trades:
        return np.array([])
    rng = np.random.default_rng(seed)
    return np.array([pts_valid[rng.choice(len(pts_valid), n_trades, replace=False)].mean() for _ in range(n_seeds)])


def timing_control(trades, direction, cost, last_mod, close_lookup, n_seeds=N_SEEDS, seed=TIMING_SEED):
    """Same real trades' session dates, entry replaced by a uniformly random integer minute in
    [sessions.RTH_START, last_mod) (module docstring point 7), held the SAME 30 minutes as the
    matched trial (identical session-boundary clamp), same direction/cost. 200 draws from one
    seeded generator. Returns the per-seed mean net pts array (empty when there are no matched
    trades)."""
    n = len(trades)
    if n == 0:
        return np.array([])
    dates = trades["date"].to_numpy()
    lm = np.array([last_mod.get(d, np.nan) for d in dates], dtype=float)
    rng = np.random.default_rng(seed)
    out = np.empty(n_seeds)
    for s in range(n_seeds):
        pts = np.full(n, np.nan)
        for i in range(n):
            if np.isnan(lm[i]) or lm[i] <= sessions.RTH_START:
                continue
            entry_mod = int(rng.integers(sessions.RTH_START, int(lm[i])))
            entry_px = close_lookup.get((dates[i], entry_mod))
            if entry_px is None:
                continue
            exit_mod = min(entry_mod + HOLD, int(lm[i]))
            exit_px = close_lookup.get((dates[i], exit_mod))
            if exit_px is None:
                continue
            pts[i] = direction * (exit_px - entry_px) - cost
        out[s] = np.nanmean(pts) if np.isfinite(pts).any() else np.nan
    return out


def summarize(win_name, name, side, lag, flow, start_ts, end_ts, sig_col, direction, kind,
             last_mod, close_lookup, vix_prev_map, td):
    w = flow[(flow["date"] >= start_ts) & (flow["date"] <= end_ts)]
    trades, n_signal_minutes, n_skipped, n_overlap_skipped = build_trades(w, sig_col, direction, kind, lag,
                                                                          last_mod, close_lookup)
    n = len(trades)
    trades["vix_prev"] = trades["date"].map(vix_prev_map) if n else pd.Series(dtype=float)
    trades["net_pts_cost1"] = trades["pts"] - COST1
    trades["net_pts_cost2"] = trades["pts"] - COST2
    trades["net_pct_cost1"] = trades["ret_pct"] - 100 * COST1 / trades["entry_px"]
    trades["net_pct_cost2"] = trades["ret_pct"] - 100 * COST2 / trades["entry_px"]
    net_pct1 = trades["net_pct_cost1"].to_numpy() if n else np.array([])
    all_dates = [d for d in td if start_ts <= d <= end_ts]
    row = dict(window=win_name, trial=name, side=side, entry_lag=f"+{lag}min",
              n_signal_minutes=n_signal_minutes, n_skipped=n_skipped, n_overlap_skipped=n_overlap_skipped, n=n,
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
    ctrl_pts = minute_selection_control(flow, start_ts, end_ts, direction, lag, COST1, n, last_mod, close_lookup)
    valid = ~np.isnan(ctrl_pts) if len(ctrl_pts) else np.array([], dtype=bool)
    row["control_mean_pts_cost1"] = float(np.nanmean(ctrl_pts)) if valid.any() else np.nan
    row["frac_seeds_beaten"] = float(np.mean(row["net_pts_cost1"] > ctrl_pts[valid])) if (n and valid.any()) else np.nan
    tim_pts = timing_control(trades, direction, COST1, last_mod, close_lookup) if n else np.array([])
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
        raise ValueError(f"pipeline.units.oflow only supports --in extended (got {inp!r})")
    paths = shard_paths()
    if not paths:
        raise FileNotFoundError(f"no shards matched {DATA_GLOB!r}")
    flow = load_flow_table(paths)
    thr = session_expanding_threshold(flow)
    flow = add_signals(flow, thr)

    td = sessions.trading_days_from_vix()
    frame, _dropped, meta = sessions.build_extended(trading_days=td)
    last_mod = frame.groupby("date")["mod"].max().to_dict()
    close_lookup = dict(zip(zip(frame["date"], frame["mod"]), frame["close"]))
    vix = pd.read_parquet("data/raw/vix_daily.parquet")
    day = signals.day_table(frame, vix, dividends=meta["dividends"] if meta else None,
                            trading_days=td, roll_dates=meta["roll_dates"] if meta else ())
    vix_prev_map = day["vix_prev"]

    rows, trade_frames = [], []
    for win_name, start, end in WINDOWS:
        start_ts, end_ts = pd.Timestamp(start), pd.Timestamp(end)
        win_rows, win_nets, win_trades = [], [], []
        for name, sig_col, direction, kind, lag in TRIALS:
            side = "call" if kind == "c" else "put"
            row, trades, net_pct1 = summarize(win_name, name, side, lag, flow, start_ts, end_ts,
                                              sig_col, direction, kind, last_mod, close_lookup, vix_prev_map, td)
            win_rows.append(row)
            win_nets.append(net_pct1)
            t_out = trades.assign(window=win_name, trial=name)
            win_trades.append(t_out[TRADE_COLS] if len(t_out) else pd.DataFrame(columns=TRADE_COLS))
        sr_pool = [stats.per_trade_sharpe(x) for x in win_nets]
        for row, x in zip(win_rows, win_nets):
            row["dsr_N48"] = stats.deflated_sharpe(x, sr_trials=sr_pool, n=DSR_N)[0] if len(x) >= 3 else np.nan
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
