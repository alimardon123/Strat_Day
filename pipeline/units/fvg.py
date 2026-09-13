"""Owner's chart setup — fair value gap (FVG) box candidate (NEW candidate family, pre-registered
literally per the owner's drawing; counted as trials, A31; never tuned to look good).

    python -m pipeline.units.fvg --in extended --out out/fvg_candidates.csv

8 trials = side {short: sell a bearish FVG; long: buy a bullish FVG} x R {1, 2} x BOS {on, off},
each reported on three windows (CONTEXT 2005-2012, SELECTION 2013-01-01..2020-05-13, HOLDOUT
2020-07-27..2026-09-11 — the owner's SPY/IEX feed's first bar) on the extended frame
(sessions.build_extended, Oanda SPX + the ext feed, both already in SPX points). No parameter is
swept beyond the 8 trials; ATR multiple 1.5, lookback 12, buffer 0.1, min height 0.05 and the
midpoint entry are FIXED by the pre-registration and never varied.

Bars: 5-minute OHLC built from the 1-minute RTH frame, one bar per 5-minute slot per session
(78 slots, 09:30..15:55 start times) so bar position ("N bars ago") is stable even where a slot
is thin; a slot with < 3 of its 5 minutes present is NaN (no signal, but the slot still occupies
its position in the sequence).

Every ambiguity the owner's description left open is fixed here and restated in the `spec`
column of the output (SPEC_NOTE below); the two biggest are: (1) ATR is a plain rolling(20) mean
true range over the bars in chronological order across the whole history — same-session-only for
every bar except the first ~19 of a session, which borrow from the prior session's tail (the
pre-registration's explicit ATR allowance); true range at a session's first bar uses that bar's
own open in place of "previous close" so an overnight/inter-session gap never enters the ATR.
(2) the FVG 3-bar pattern and the 12-bar structure-break lookback are SAME-SESSION ONLY (no
cross-session borrowing) — an intraday structure reference spanning the overnight gap would not
match the owner's drawing; insufficient same-session history means no setup (BOS=on) / no
structure break, never a cross-session lookback.
"""
import argparse

import numpy as np
import pandas as pd

from pipeline import sessions, stats
from pipeline.units import _gh

BAR_LEN = 5                 # minutes per bar
MIN_MIN_PER_BAR = 3         # >= 3 of 5 minutes present, else NaN (no signal)
ATR_WINDOW = 20             # bars
ATR_MULT = 1.5              # displacement threshold
LOOKBACK = 12                # bars = one hour, structure-break window
BUFFER = 0.1                # stop = box edge +/- BUFFER * ATR
MIN_HEIGHT_ATR = 0.05       # box height >= MIN_HEIGHT_ATR * ATR, else skip
FILL_DEADLINE_MOD = 15 * 60 + 30   # 15:30 ET; a bar STARTING at or before this is fill-eligible
ENTRY_WINDOW = (10 * 60, 15 * 60 + 30)   # random-entry control: bar start in [10:00, 15:30]
COST1, COST2 = 1.0, 2.0     # SPX points round trip (base / reported sensitivity)
N_SEEDS = 200
CONTROL_SEED = 17           # arbitrary, fixed for determinism (distinct from stats.SEED=11)
DSR_N = 33                  # 8 trials this run + 25 already in the run's family
WINDOWS = [("CONTEXT", "2005-01-01", "2012-12-31"),
           ("SELECTION", "2013-01-01", "2020-05-13"),
           ("HOLDOUT", "2020-07-27", "2026-09-11")]
TRADE_COLS = ["date", "t_ts", "filled", "exit_reason", "entry_ts", "entry_px", "exit_ts", "exit_px",
              "pts", "ret_pct", "box_top", "box_bottom", "stop_px", "tp_px"]

SPEC_NOTE = (
    "FIXED (pre-registration): ATR mult 1.5, structure lookback 12 bars, stop buffer 0.1 ATR, "
    "min box height 0.05 ATR, entry = box midpoint. atr_ref for a setup ending at bar t = "
    "rolling(20) mean true range of the 20 bars strictly before the displacement bar t-1 (no "
    "lookahead into t-1/t); ATR rolls across sessions only for the first ~19 bars of a session, "
    "else same-session (pre-registration's own allowance); true range at a session's first bar "
    "uses that bar's own open, not the prior session's close (no overnight gap in ATR). FVG 3-bar "
    "pattern and the 12-bar structure lookback are SAME-SESSION ONLY; insufficient same-session "
    "history => no setup / no structure break. Fill deadline = bar START <= 15:30 ET; fill test = "
    "bar range contains the midpoint; exit search starts AT the fill bar itself (a wide bar can "
    "both fill and stop/TP); stop wins a same-bar stop+TP tie. One ACTIVE setup at a time per "
    "side (most conservative reading of 'one position at a time'): a setup occupies its side from "
    "detection until it is resolved (filled-then-exited, or unfilled through the 15:30/session-end "
    "deadline); a pattern detected while one is active is skipped (n_skipped_open) and NOT counted "
    "in n_setups. n_setups = patterns actually acted on (not blocked); n_patterns_detected = total "
    "pattern count before that gate; fill_rate = n_filled / n_setups. Random-entry control: 200 "
    "draws from one seeded generator (not 200 independent seeds, matching signals.day_selection_"
    "control's convention), entry = OPEN of a uniformly random bar in [10:00,15:30], same stop "
    "distance and R as the matched real trade, evaluated at the 1.0-pt cost only (not swept at "
    "2.0). DSR at N=33 (8 trials this run + 25 already in the family) uses the per-trade-Sharpe "
    "dispersion of THIS RUN'S OWN 8 trials in the same window as SR0's pool (the 25 external "
    "trials are not available to this standalone unit). win/median/worst/calendar-day Sharpe/"
    "bootstrap p use the 1.0-pt cost; net pts and net % are also reported at 2.0. Windows: CONTEXT "
    "2005-01-01..2012-12-31, SELECTION 2013-01-01..2020-05-13, HOLDOUT 2020-07-27..2026-09-11.")


def build_bars(frame):
    """One row per 5-minute slot per RTH session (78 slots, 09:30..15:55 start), even where a
    slot has zero printed minutes, so bar position is stable; OHLC is NaN where < 3 of the slot's
    5 minutes are present. Adds session_idx (0-based position within its session), g_idx (global
    sequential position across the whole history), true range and the rolling-20 ATR."""
    d = frame[["date", "mod", "open", "high", "low", "close"]].copy()
    d["bar_mod"] = (d["mod"] // BAR_LEN) * BAR_LEN
    agg = d.groupby(["date", "bar_mod"]).agg(open=("open", "first"), high=("high", "max"),
                                             low=("low", "min"), close=("close", "last"),
                                             n_min=("close", "size")).reset_index()
    dates = np.sort(agg["date"].unique())
    mods = np.arange(sessions.RTH_START, sessions.RTH_END, BAR_LEN)
    full_idx = pd.MultiIndex.from_product([dates, mods], names=["date", "bar_mod"])
    bars = agg.set_index(["date", "bar_mod"]).reindex(full_idx).reset_index()
    bars["n_min"] = bars["n_min"].fillna(0).astype(int)
    thin = bars["n_min"] < MIN_MIN_PER_BAR
    bars.loc[thin, ["open", "high", "low", "close"]] = np.nan
    bars = bars.sort_values(["date", "bar_mod"]).reset_index(drop=True)
    bars["session_idx"] = bars.groupby("date").cumcount()
    bars["g_idx"] = np.arange(len(bars))
    bars["bar_ts"] = bars["date"] + pd.to_timedelta(bars["bar_mod"], unit="m")
    prev_close = bars.groupby("date")["close"].shift(1)
    ref_close = np.where(bars["session_idx"] == 0, bars["open"], prev_close)
    bars["tr"] = np.maximum(bars["high"] - bars["low"],
                            np.maximum((bars["high"] - ref_close).abs(), (bars["low"] - ref_close).abs()))
    bars["atr20"] = bars["tr"].rolling(ATR_WINDOW, min_periods=ATR_WINDOW).mean()
    return bars


def detect_side(bars, side):
    """Every bearish (side='short') or bullish (side='long') FVG at bar t that also clears the
    displacement and min-height gates, with the structure-break flag reported alongside (BOS='on'
    additionally requires it; BOS='off' ignores it) — one row per qualifying pattern."""
    idx = bars.index
    same3 = (bars["date"] == bars["date"].shift(1)) & (bars["date"] == bars["date"].shift(2)) & (bars["session_idx"] >= 2)
    low_t2, high_t2, close_t2 = bars["low"].shift(2), bars["high"].shift(2), bars["close"].shift(2)
    open_t1, close_t1 = bars["open"].shift(1), bars["close"].shift(1)
    high_t, low_t = bars["high"], bars["low"]
    atr_ref = bars["atr20"].shift(2)          # 20-bar ATR ending at t-2 (strictly before t-1 opens)
    disp = (close_t1 - open_t1).abs() >= ATR_MULT * atr_ref
    struct_ok = bars["session_idx"].shift(1) >= LOOKBACK    # t-1 has >= 12 same-session bars before it
    if side == "short":
        fvg = same3 & (high_t < low_t2)
        box_top = pd.Series(np.where(close_t2 > low_t2, close_t2, low_t2), index=idx)
        box_bottom = high_t
        lookback_extreme = bars["low"].rolling(LOOKBACK, min_periods=LOOKBACK).min().shift(2)
        structure = struct_ok & (close_t1 < lookback_extreme)
        stop_px = box_top + BUFFER * atr_ref
    elif side == "long":
        fvg = same3 & (low_t > high_t2)
        box_bottom = pd.Series(np.where(close_t2 < high_t2, close_t2, high_t2), index=idx)
        box_top = low_t
        lookback_extreme = bars["high"].rolling(LOOKBACK, min_periods=LOOKBACK).max().shift(2)
        structure = struct_ok & (close_t1 > lookback_extreme)
        stop_px = box_bottom - BUFFER * atr_ref
    else:
        raise ValueError(side)
    height_ok = (box_top - box_bottom) >= MIN_HEIGHT_ATR * atr_ref
    ok = (fvg & disp & height_ok & atr_ref.notna()).fillna(False)
    out = bars.loc[ok, ["g_idx", "date", "session_idx", "bar_ts"]].copy()
    out["box_top"] = box_top[ok]
    out["box_bottom"] = box_bottom[ok]
    out["mid"] = (box_top[ok] + box_bottom[ok]) / 2.0
    out["atr_ref"] = atr_ref[ok]
    out["stop_px"] = stop_px[ok]
    out["structure_break"] = structure.fillna(False)[ok].to_numpy()
    return out.reset_index(drop=True)


def simulate(bars_by_date, setups, side, r):
    """Walk the (already side/BOS-filtered) setups in bar order, one active setup at a time (see
    SPEC_NOTE); returns the per-setup trade table (including unfilled and skipped-for-open-
    position rows) and the setup/fill counts."""
    direction = -1.0 if side == "short" else 1.0
    setups = setups.sort_values("g_idx").reset_index(drop=True)
    trades = []
    busy_until = -1
    n_patterns, n_skipped_open, n_setups, n_filled = len(setups), 0, 0, 0
    for row in setups.itertuples(index=False):
        if row.g_idx <= busy_until:
            n_skipped_open += 1
            trades.append(dict(date=row.date, t_ts=row.bar_ts, filled=False, exit_reason="skipped_open_position",
                               entry_ts=pd.NaT, entry_px=np.nan, exit_ts=pd.NaT, exit_px=np.nan, pts=np.nan,
                               ret_pct=np.nan, box_top=row.box_top, box_bottom=row.box_bottom,
                               stop_px=row.stop_px, tp_px=np.nan))
            continue
        n_setups += 1
        day_bars = bars_by_date[row.date]
        window_all = day_bars[(day_bars["session_idx"] > row.session_idx) & (day_bars["bar_mod"] <= FILL_DEADLINE_MOD)]
        window_valid = window_all[window_all["close"].notna()]
        touch = window_valid[(window_valid["low"] <= row.mid) & (window_valid["high"] >= row.mid)]
        if touch.empty:
            busy_until = int(window_all["g_idx"].max()) if len(window_all) else int(row.g_idx)
            trades.append(dict(date=row.date, t_ts=row.bar_ts, filled=False, exit_reason="unfilled",
                               entry_ts=pd.NaT, entry_px=np.nan, exit_ts=pd.NaT, exit_px=np.nan, pts=np.nan,
                               ret_pct=np.nan, box_top=row.box_top, box_bottom=row.box_bottom,
                               stop_px=row.stop_px, tp_px=np.nan))
            continue
        n_filled += 1
        fill = touch.iloc[0]
        entry_px, entry_ts = row.mid, fill["bar_ts"]
        stop_dist = abs(row.stop_px - entry_px)
        tp_px = entry_px + direction * r * stop_dist
        exit_search = day_bars[(day_bars["session_idx"] >= fill["session_idx"]) & day_bars["close"].notna()]
        exit_px = exit_reason = exit_ts = exit_g = None
        for erow in exit_search.itertuples(index=False):
            stop_touched = erow.high >= row.stop_px if side == "short" else erow.low <= row.stop_px
            tp_touched = erow.low <= tp_px if side == "short" else erow.high >= tp_px
            if stop_touched or tp_touched:                       # stop wins a same-bar tie
                exit_px = row.stop_px if stop_touched else tp_px
                exit_reason = "stop" if stop_touched else "tp"
                exit_ts, exit_g = erow.bar_ts, erow.g_idx
                break
        if exit_px is None:
            last = exit_search.iloc[-1]
            exit_px, exit_reason, exit_ts, exit_g = last["close"], "close", last["bar_ts"], last["g_idx"]
        busy_until = int(exit_g)
        pts = direction * (exit_px - entry_px)
        ret_pct = direction * (exit_px / entry_px - 1) * 100
        trades.append(dict(date=row.date, t_ts=row.bar_ts, filled=True, exit_reason=exit_reason, entry_ts=entry_ts,
                           entry_px=entry_px, exit_ts=exit_ts, exit_px=exit_px, pts=pts, ret_pct=ret_pct,
                           box_top=row.box_top, box_bottom=row.box_bottom, stop_px=row.stop_px, tp_px=tp_px))
    t = pd.DataFrame(trades, columns=TRADE_COLS)
    counts = dict(n_patterns_detected=n_patterns, n_skipped_open=n_skipped_open, n_setups=n_setups, n_filled=n_filled)
    return t, counts


def random_entry_control(bars_by_date, trades, side, r, cost, n_seeds=N_SEEDS, seed=CONTROL_SEED):
    """A16-style control (Thread A convention): same days as the FILLED real trades, same side,
    same R, entry at a uniformly random 5-minute bar's OPEN in [10:00,15:30] instead of the
    midpoint touch, same stop distance as the matched real trade; 200 draws from one seeded
    generator (net of `cost`). Returns (per-seed mean net %, per-seed mean net pts)."""
    filled = trades[trades["filled"]]
    if filled.empty:
        return np.full(n_seeds, np.nan), np.full(n_seeds, np.nan)
    direction = -1.0 if side == "short" else 1.0
    mods = np.arange(ENTRY_WINDOW[0], ENTRY_WINDOW[1] + 1, BAR_LEN)
    rng = np.random.default_rng(seed)
    pct_means, pts_means = [], []
    for _ in range(n_seeds):
        pct_list, pts_list = [], []
        for tr in filled.itertuples(index=False):
            day_bars = bars_by_date.get(tr.date)
            if day_bars is None:
                continue
            m = int(rng.choice(mods))
            cand = day_bars[(day_bars["bar_mod"] == m) & day_bars["close"].notna()]
            if cand.empty:
                continue
            crow = cand.iloc[0]
            entry_px = float(crow["open"])
            stop_dist = abs(tr.stop_px - tr.entry_px)
            stop_px = entry_px - direction * stop_dist
            tp_px = entry_px + direction * r * stop_dist
            exit_search = day_bars[(day_bars["session_idx"] >= crow["session_idx"]) & day_bars["close"].notna()]
            exit_px = None
            for erow in exit_search.itertuples(index=False):
                stop_touched = erow.high >= stop_px if side == "short" else erow.low <= stop_px
                tp_touched = erow.low <= tp_px if side == "short" else erow.high >= tp_px
                if stop_touched or tp_touched:
                    exit_px = stop_px if stop_touched else tp_px
                    break
            if exit_px is None:
                exit_px = float(exit_search.iloc[-1]["close"])
            pts_list.append(direction * (exit_px - entry_px) - cost)
            pct_list.append(direction * (exit_px / entry_px - 1) * 100 - 100 * cost / entry_px)
        pct_means.append(np.mean(pct_list) if pct_list else np.nan)
        pts_means.append(np.mean(pts_list) if pts_list else np.nan)
    return np.array(pct_means), np.array(pts_means)


def summarize(window_name, side, r, bos, trades, counts, all_dates, ctrl_pct, ctrl_pts):
    filled = trades[trades["filled"]].copy()
    n = len(filled)
    if n:
        filled["net_pts_cost1"] = filled["pts"] - COST1
        filled["net_pts_cost2"] = filled["pts"] - COST2
        filled["net_pct_cost1"] = filled["ret_pct"] - 100 * COST1 / filled["entry_px"]
        filled["net_pct_cost2"] = filled["ret_pct"] - 100 * COST2 / filled["entry_px"]
    row = dict(window=window_name, trial=f"{side}|R{r}|bos_{bos}", side=side, r=r, bos=bos,
               n_patterns_detected=counts["n_patterns_detected"], n_skipped_open=counts["n_skipped_open"],
               n_setups=counts["n_setups"], n_filled=counts["n_filled"],
               fill_rate=(counts["n_filled"] / counts["n_setups"]) if counts["n_setups"] else np.nan,
               n=n, win=(100 * (filled["pts"] > 0).mean()) if n else np.nan,
               net_pts_cost1=filled["net_pts_cost1"].mean() if n else np.nan,
               net_pts_cost2=filled["net_pts_cost2"].mean() if n else np.nan,
               net_pct_cost1=filled["net_pct_cost1"].mean() if n else np.nan,
               net_pct_cost2=filled["net_pct_cost2"].mean() if n else np.nan,
               median_net_pts_cost1=filled["net_pts_cost1"].median() if n else np.nan,
               worst_trade_pts_cost1=filled["net_pts_cost1"].min() if n else np.nan,
               worst_day_pts_cost1=filled.groupby("date")["net_pts_cost1"].sum().min() if n else np.nan)
    net_pct1 = filled["net_pct_cost1"].to_numpy() if n else np.array([])
    row["sharpe_calday"] = stats.calendar_day_sharpe(net_pct1, filled["date"], all_dates)
    row["sr_trade"] = stats.per_trade_sharpe(net_pct1)
    row["p_boot_day"] = stats.one_sided_p(net_pct1, stats.day_blocks(filled["date"])) if n else np.nan
    row["p_boot_month"] = stats.one_sided_p(net_pct1, stats.month_blocks(filled["date"])) if n else np.nan
    valid = ~np.isnan(ctrl_pct)
    row["control_mean_pct_cost1"] = float(np.nanmean(ctrl_pct)) if valid.any() else np.nan
    row["control_mean_pts_cost1"] = float(np.nanmean(ctrl_pts)) if valid.any() else np.nan
    row["frac_seeds_beaten"] = float(np.mean(row["net_pct_cost1"] > ctrl_pct[valid])) if (n and valid.any()) else np.nan
    row["spec"] = SPEC_NOTE
    return row, net_pct1


def main(inp, out):
    if inp != "extended":
        raise ValueError(f"pipeline.units.fvg only supports --in extended (got {inp!r})")
    td = sessions.trading_days_from_vix()
    frame, _dropped, _meta = sessions.build_extended(trading_days=td)
    bars = build_bars(frame)
    bars_by_date = {d: g.reset_index(drop=True) for d, g in bars.groupby("date")}
    setups_by_side = {side: detect_side(bars, side) for side in ("short", "long")}

    rows, trade_frames = [], []
    for win_name, start, end in WINDOWS:
        start_ts, end_ts = pd.Timestamp(start), pd.Timestamp(end)
        all_dates = [d for d in td if start_ts <= d <= end_ts]
        win_rows, win_nets = [], []
        for side in ("short", "long"):
            s_win = setups_by_side[side]
            s_win = s_win[(s_win["date"] >= start_ts) & (s_win["date"] <= end_ts)]
            for bos in ("on", "off"):
                s_bos = s_win[s_win["structure_break"]] if bos == "on" else s_win
                for r in (1, 2):
                    trades, counts = simulate(bars_by_date, s_bos, side, r)
                    ctrl_pct, ctrl_pts = random_entry_control(bars_by_date, trades, side, r, COST1)
                    row, net_pct1 = summarize(win_name, side, r, bos, trades, counts, all_dates, ctrl_pct, ctrl_pts)
                    win_rows.append(row)
                    win_nets.append(net_pct1)
                    trade_frames.append(trades.assign(window=win_name, trial=row["trial"], side=side))
        sr_pool = [stats.per_trade_sharpe(x) for x in win_nets]
        for row, x in zip(win_rows, win_nets):
            if len(x) >= 3:
                dsr, sr0, _ = stats.deflated_sharpe(x, sr_trials=sr_pool, n=DSR_N)
            else:
                dsr, sr0 = np.nan, np.nan
            row["dsr_N33"], row["sr0_N33"] = dsr, sr0
        rows.extend(win_rows)

    res = pd.DataFrame(rows)
    res.to_csv(out, index=False, float_format="%.6f")
    trades_path = out[:-4] + "_trades.csv" if out.endswith(".csv") else out + "_trades.csv"
    tr_all = pd.concat(trade_frames, ignore_index=True) if trade_frames else pd.DataFrame(columns=TRADE_COLS)
    lead = ["window", "trial", "date", "side", "entry_ts", "entry_px", "exit_ts", "exit_px", "exit_reason", "pts", "ret_pct"]
    extra = [c for c in tr_all.columns if c not in lead]
    tr_all = tr_all[lead + extra]
    tr_all.to_csv(trades_path, index=False, float_format="%.6f")
    print(res.to_string(index=False, float_format=lambda x: f"{x:.4f}"))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", default="extended")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    _gh.run(lambda: main(a.inp, a.out), a.out)
