"""Real 0DTE prices: model calibration and re-evaluation (A41, pre-registered 2026-09-13 15:40 UTC,
before any real option bar exists on the branch; NOT tuned to look good).

    python -m pipeline.units.realopt --in extended --out out/realopt_reeval.csv

Input `data/ext/spy_0dte_1min_2024-02_2026-09.csv.gz` (`tools/fetch_spy_0dte_local.py`, DATA.md):
1-minute bars of SPY same-day-expiry option contracts within +/-3% of the 09:30 price, UTC
timestamps, SPY dollars. It does NOT exist on this branch yet (the owner's fetch runs on a
machine the research container's proxy cannot reach): without it, this unit prints `[SKIP] ...`
and writes ALL THREE output files with a header row only, exit 0, so `make all`'s non-empty-
output check passes and nothing downstream blocks -- the SAME contract `pipeline.units.letf`
(A38) uses, copied here verbatim per the task that produced this file: header-only outputs on
ANY exception (missing file, bad data, a bug) and exit 0, never a `.error` file, UNLIKE every
other fleet unit in this codebase (`pipeline.units._gh.run`'s A32 convention: empty file +
`<out>.error` + exit 2). A pre-registered-but-not-yet-runnable candidate must never fail
`make all`.

Two pieces (ACCEPTANCE A41), both diagnostic/re-pricing only -- neither adds a trial to
`pipeline/trials.py`'s family ("the trial count does not grow (these are re-pricings of counted
trials, not new trials)"):

CALIBRATION (`out/realopt_calibration.csv`): for every session in the option file and each of
{09:31, 10:00, 13:00, 15:00, 15:30} ET, the nearest-to-2%-ITM call and put's real bar close
divided by the Black-Scholes premium at k=1 x prior-close VIX = implied k, plus the share of
contracts with no bar in that minute (illiquidity). Median/IQR of implied k are reported by VIX
tercile (over the file's own sessions) and by minute.

RE-EVALUATION (`out/realopt_reeval.csv` + `out/realopt_reeval_trades.csv`): every option leg
already priced by the model on sessions >= 2024-02-01 is re-priced with real bars -- the two
pre-registered D4 holdout signals, the 15 POST-SELECTION rows (if their per-trade files exist),
A39's T1/T2/T3 -- at three added-cost rows (+$0.00 / +$0.10 / +$0.20 round trip = 0/1/2 SPX
points), against the model's own number on the SAME re-priced trades, labelled "model optimistic
here" / "model pessimistic here". Nothing here is promoted; every row is stamped `note =
"sub-window, not a verdict"` (the amendment's own words).

Every ambiguity the amendment left open is fixed here and restated in the `spec` column
(SPEC_NOTE below); worth flagging up front:
(1) Skip/failure contract copied from `pipeline.units.letf` verbatim (see module docstring
    above and the task that produced this file): header-only outputs + exit 0 on the missing
    input file OR any other exception, never `.error`.
(2) "the SPY price at that minute" (calibration's spot AND the strike target for both
    calibration and re-evaluation) is read as the EXACT 1-minute bar's close at that minute-of-
    day on `sessions.build_extended`'s frame -- the SAME convention `pipeline.units.gapliq` uses
    for its own fixed 10:00/09:31 entries (`px_1000`/`px_0931`) -- applied uniformly to all five
    calibration minutes (09:31/10:00/13:00/15:00/15:30) rather than `signals.day_table`'s +/-5-
    minute-tolerance "decision price" convention, because day_table does not precompute 09:31 or
    10:00 and a single uniform rule across five minutes is simpler than mixing two conventions.
    Divided by 10 to dollars per the amendment's own instruction (the branch's post-2020 minute
    feed is SPX-point-scaled per A6, and 1 SPX point = $0.10 SPY); this assumes the ext manifest
    for this period declares instrument SPY, matching every other unit's use of the same feed.
(3) The model premium at calibration time is `pipeline.options.price` called directly (NO bid/
    ask spread added) at k=1 x prior-close VIX, matching the amendment's literal text ("real bar
    close / Black-Scholes premium at k=1"); this is deliberately NOT `pipeline.options.trade`,
    which adds half the quoted spread on entry -- calibration measures the RAW model against the
    RAW real close, not a tradeable entry price.
(4) A session present in the option file but absent from `sessions.build_extended`'s frame (e.g.
    the branch's other minute-price ext file is itself short of that date) contributes NO
    calibration rows for that date -- skipped, not fabricated, since neither the spot price nor
    the model premium can be computed without it; likewise a (date, minute) with no underlying
    bar at all is skipped. A (date, right) with no LISTED strike at all that day (no contract
    ever printed) also contributes no row -- this is different from `missing=True`, which means a
    specific strike/right IS listed that day but has no bar in that exact minute (the illiquidity
    signal the amendment asks for).
(5) VIX terciles are computed over the session-level prior-close VIX of every date that produced
    at least one calibration row ("terciles ... over the file's sessions", read literally), via
    quantile rank (robust to duplicate VIX values without silently reducing to <3 groups the way
    a naive `pd.qcut(..., labels=[...])` would raise on).
(6) "Summary rows appended (or a second block)" is read as a literal second block in the SAME
    `out/realopt_calibration.csv` file: the per-(date, minute, right) table, one blank line, then
    a second table (`group_type, group_value, n, median_implied_k, iqr_implied_k,
    missing_share`) with one row per VIX tercile, one row per minute, and one `overall` row -- the
    reading closest to the amendment's own parenthetical. The skip path writes only the first
    block's header (no summary block), matching every other header-only output in this unit.
(7) Re-evaluation entry-minute/direction/kind: for the two pre-registered D4 signals and any
    POST-SELECTION row with a per-trade file, the per-trade CSV's own `entry_mod`/`kind` columns
    are used row by row (a real signal's entry drifts by a bar or two around the nominal decision
    minute under A11). A39's T1/T2/T3 trades file (`out/gapliq_candidates_trades.csv`) carries no
    entry_mod/kind column, so the FIXED entry minute and option kind each trial pre-registered
    (`pipeline.units.gapliq.MOD_1000`/`MOD_0931`, kind 'c'/'c'/'p') are reused directly from that
    module instead of re-derived; the exit minute-of-day and prior-close VIX needed only for the
    MODEL comparison number (never for the real bars) are looked up from a freshly built
    `signals.day_table` by date.
(8) The 15 POST-SELECTION rows: `pipeline.playbook.build` (called from `pipeline.insample`) only
    ever prices the two signals it is handed (the D1 winner and the gap-up call), so on this
    branch NO `out/holdout_d4_<name>_s1_cash_k1.0.csv` exists for any POST-SELECTION candidate.
    This unit looks for that exact file, by the exact naming convention `pipeline.playbook.build`
    itself uses, for every POST-SELECTION candidate named in `out/reconcile_candidates.csv`;
    finding none, it prints a `[NOTE]` stating so and reports NOTHING for part (b) -- the
    amendment's own escape clause ("if their per-trade rows exist ... otherwise state that they
    do not and skip"), rather than recomputing the signal in-process (not asked for here).
(9) Real-bar entry/exit fallback: entry = the exact 1-minute bar's close at the entry minute; if
    absent, the next LATER bar's OPEN that session (any distance later -- 0DTE contracts can be
    illiquid); if neither exists, the trade is skipped and counted. Exit = the exact 15:59 bar's
    close; if absent, the LAST available bar's close at or before 15:59 that session (read
    literally from the amendment's own justification, "the 15:59 close is the last tradable
    print"); if no bar exists before 15:59 either, OR no listed contract exists for the needed
    (date, right) at all, the trade is skipped and counted in the SAME `n_skipped_missing` -- the
    amendment names one skip counter, not several.
(10) Costs are a flat dollar amount subtracted from the option's own real dollar P&L (+$0.00 /
     +$0.10 / +$0.20), per the amendment's literal text -- NOT `pipeline.options`'s bid/ask-spread
     mechanism (entry AND exit spread halves), because real bar closes already sit inside the
     spread, which is exactly why the amendment adds a flat dollar instead.
(11) `model_mean_pct` ("the model's number on the SAME trades for comparison") is recomputed via
     `pipeline.options.trade` on the SAME entry/exit minute-of-day, underlying price and VIX as
     the ORIGINAL model row (1.0 pt spread, cash settle, SPX grid), restricted to the exact trade
     subset that survived real re-pricing (a trade skipped for a missing real bar does not enter
     the model average either). It is ONE reference number per signal, identical on all three
     cost rows (the amendment cost-varies only the real-price side). The model k matches whatever
     k this codebase ALREADY used to price that exact signal elsewhere: k=1.0 for the D1 winner
     and any POST-SELECTION row (`pipeline.insample`'s own rule: k=1.3 only for the 780/13:00
     leg), k=1.3 for the 13:00 gap-up call (same rule) and for A39 T1/T2/T3
     (`pipeline.units.gapliq.OPT_K`) -- never the D4 sensitivity sweep.
(12) `label`: "model optimistic here" when the real mean % of premium (at that cost row) is
     strictly less than `model_mean_pct`, "model pessimistic here" when strictly greater (the
     amendment's own two labels); an exact tie (never observed with real float data) reads as
     pessimistic; a signal with zero re-priced trades reads "no re-priced trades" instead.
(13) Every re-evaluation row carries `note = "sub-window, not a verdict"` verbatim -- nothing here
     is scored against BH-FDR or added to `pipeline/trials.py`'s family.
(14) `p_boot_day`/`sharpe_calday` use `pipeline.stats`'s existing day-block one-sided bootstrap
     (seed 11, n_boot 2000 -- the module defaults) and `calendar_day_sharpe` over the NYSE
     trading days from 2024-02-01 through the option file's last date, shared across every signal
     since the sub-window is common to all of them.
(15) 0DTE guard: rows in the option file whose `expiry` differs from its own session `date`
     (should not occur given the file's own same-day-expiry spec, unverifiable before the file
     exists) are dropped defensively before any pricing.
"""
import argparse
import os
import sys
import traceback

import numpy as np
import pandas as pd

from pipeline import insample, options, sessions, signals, stats
from pipeline.units import gapliq

EXT_OPT_PATH = "data/ext/spy_0dte_1min_2024-02_2026-09.csv.gz"   # single-file layout (message text)
EXT_OPT_GLOB = "data/ext/spy_0dte_1min_*.csv.gz"                  # or per-year shards written by the fetch helper


def option_shards(ext_path=EXT_OPT_PATH):
    """The option file as one path or as per-year shards (tools/fetch_spy_0dte_local.py writes
    <prefix><year>.csv.gz so no file exceeds GitHub's 100 MB); sorted, temp files excluded."""
    import glob
    paths = sorted(q for q in glob.glob(EXT_OPT_GLOB) if not q.endswith(".tmp.csv"))
    if ext_path and os.path.exists(ext_path) and ext_path not in paths:
        paths.append(ext_path)
    return paths


def read_option_bars(paths):
    return pd.concat([pd.read_csv(q, dtype={"right": str}) for q in paths], ignore_index=True)
CALIB_OUT = "out/realopt_calibration.csv"
REEVAL_START = pd.Timestamp("2024-02-01")
REAL_EXIT_MOD = 15 * 60 + 59      # 959, the last tradable print before physical settlement (A41's own text)
MINUTES = [("09:31", 9 * 60 + 31), ("10:00", 10 * 60), ("13:00", 13 * 60), ("15:00", 15 * 60), ("15:30", 15 * 60 + 30)]
GAP_NAME = "13:00|call|gap>0.3%"                 # Thread A's pre-registered second D2/D4 holdout signal
POST_WINDOW = "2020-06-01..2026-09-11"           # reconcile.py's literal `window` string for POST-SELECTION rows
COST_ROWS = [("+$0.00", 0.0), ("+$0.10", 0.10), ("+$0.20", 0.20)]   # 0 / 1 / 2 SPX-point round trips (A41)
GAPLIQ_K = gapliq.OPT_K                          # 1.3, reused as-is (see docstring point 11)
CALIB_COLS = ["date", "minute", "right", "strike", "underlying", "real_close", "model_k1", "implied_k", "missing"]
CALIB_SUMMARY_COLS = ["group_type", "group_value", "n", "median_implied_k", "iqr_implied_k", "missing_share"]
OUT_COLS = ["signal", "cost_label", "added_cost_dollars", "n", "n_skipped_missing", "win",
            "mean_pct_of_premium", "median_pct", "worst_pct", "model_mean_pct", "label",
            "p_boot_day", "sharpe_calday", "note", "spec"]
TRADE_COLS = ["signal", "date", "entry_mod", "kind", "strike", "entry_close", "exit_close",
              "entry_fallback", "exit_fallback", "raw_pnl_dollars", "pct_raw", "model_pct"]

SPEC_NOTE = (
    "FIXED (pre-registration, A41): calibration -- for every session in the option file and each "
    "of {09:31,10:00,13:00,15:00,15:30} ET, the nearest-to-2%-ITM call/put's real 1-minute bar "
    "close (exact-minute match on the branch's session-builder frame, /10 to dollars) divided by "
    "pipeline.options.price at k=1 x prior-close VIX = implied k; median/IQR by VIX tercile (over "
    "the file's own sessions) and by minute, plus the missing (no-bar) share, in a second block of "
    "the same csv. Re-evaluation -- every option leg already priced by the model on sessions >= "
    "2024-02-01 (the two pre-registered D4 holdout signals, any POST-SELECTION row with a "
    "per-trade file, A39 T1/T2/T3) is re-priced with real bars: entry = the option's exact-minute "
    "bar close at the trade's own entry minute (next later bar's open if missing), exit = the "
    "exact 15:59 bar close (last bar at/before 15:59 if missing); a trade with neither is skipped "
    "and counted in n_skipped_missing. Strike = nearest LISTED strike that day to the unrounded 2% "
    "ITM model target. Costs: +$0.00/+$0.10/+$0.20 flat, three rows per signal. model_mean_pct is "
    "pipeline.options.trade's own number on the exact same re-priced trades (k=1.0 for the D1 "
    "winner/POST-SELECTION rows, k=1.3 for the 13:00 gap-up call and A39 T1/T2/T3, matching each "
    "signal's existing convention elsewhere in this codebase), never the D4 sensitivity sweep. "
    "label: 'model optimistic here' if real < model, 'model pessimistic here' if real > model. "
    "Every row carries note='sub-window, not a verdict': nothing here is promoted, added to "
    "pipeline/trials.py's family, or scored against BH-FDR -- the trial count does not grow "
    "(re-pricings of counted trials, not new trials). On ANY exception (including the option file "
    "being absent) this unit writes header-only outputs and exits 0, exactly like "
    "pipeline.units.letf (A38) -- never a `.error` file -- this candidate must never fail `make "
    "all` before its data exists.")


# ---------------------------------------------------------------------------------------------
# Core pricing helpers (unit-tested directly, see test_realopt.py)
# ---------------------------------------------------------------------------------------------

def model_premium(S, K, mins_to_close, vix_prev, kind, k=1.0):
    """Black-Scholes premium at k x prior-close VIX (A7's model, k=1 for calibration)."""
    iv = k * float(vix_prev) / 100.0
    return options.price(S, K, mins_to_close, iv, kind)


def implied_k(real_close, model):
    """real / model; NaN when the real close is missing or the model premium is not positive."""
    if real_close is None or (isinstance(real_close, float) and np.isnan(real_close)) or model <= 0:
        return np.nan
    return float(real_close) / float(model)


def target_strike(S, kind):
    """Unrounded 2% ITM target in the underlying's own units (A8); the nearest LISTED strike is
    picked separately (`nearest_listed`) rather than snapping to a theoretical grid, since real
    listed strikes need not fall on any particular grid."""
    return options.strike(S, kind, itm=0.02, grid=None)


def nearest_listed(strikes, target):
    """The listed strike (from a real option file) closest to `target`; None if `strikes` is
    empty (no contract of that right listed that day)."""
    arr = np.asarray(sorted(set(float(s) for s in strikes)), float)
    if len(arr) == 0:
        return None
    return float(arr[np.argmin(np.abs(arr - target))])


def vix_terciles(session_vix):
    """Quantile-rank tercile labels ('T1'..'T3', low to high VIX) over `session_vix` (one value
    per session); robust to duplicate values (never raises the way `pd.qcut(..., labels=[...])`
    does on a repeated bin edge -- it can simply produce fewer than 3 groups instead)."""
    q = pd.qcut(session_vix.rank(method="first"), 3, duplicates="drop")
    codes = q.cat.codes
    return codes.map({i: f"T{i + 1}" for i in range(q.cat.categories.size)})


# ---------------------------------------------------------------------------------------------
# Calibration
# ---------------------------------------------------------------------------------------------

def underlying_by_minute(frame, mod):
    """Exact 1-minute bar close at minute-of-day `mod`, one value per session, in dollars (/10;
    see docstring point 2)."""
    return frame.loc[frame["mod"] == mod].groupby("date")["close"].first() / 10.0


def calibration_row(date, minute_label, mod, right, opt_day, S, vix_prev):
    """One calibration row for (date, minute, right), or None if no contract of that right is
    listed that day at all (see docstring point 4)."""
    kind = "c" if right == "C" else "p"
    target = target_strike(S, kind)
    strikes = opt_day.loc[opt_day["right"] == right, "strike"]
    K = nearest_listed(strikes, target)
    if K is None:
        return None
    bar = opt_day[(opt_day["right"] == right) & (opt_day["strike"] == K) & (opt_day["mod"] == mod)]
    missing = bar.empty
    real_close = float(bar["close"].iloc[0]) if not missing else np.nan
    mins_to_close = options.CLOSE_MOD - mod
    model = model_premium(S, K, mins_to_close, vix_prev, kind, k=1.0)
    return dict(date=date, minute=minute_label, right=right, strike=K, underlying=S,
                real_close=real_close, model_k1=model, implied_k=implied_k(real_close, model),
                missing=bool(missing))


def run_calibration(opt_df, day, frame):
    """Calibration rows for every (session, minute, right) that has a real contract listed
    (docstring point 4 for the sessions/minutes that are skipped instead)."""
    rows = []
    under = {mlabel: underlying_by_minute(frame, mod) for mlabel, mod in MINUTES}
    for date in sorted(opt_df["date"].unique()):
        date = pd.Timestamp(date)
        if date not in day.index or pd.isna(day.loc[date, "vix_prev"]):
            continue
        vix_prev = float(day.loc[date, "vix_prev"])
        og = opt_df[opt_df["date"] == date]
        for mlabel, mod in MINUTES:
            S = under[mlabel].get(date, np.nan)
            if pd.isna(S):
                continue
            for right in ("C", "P"):
                row = calibration_row(date, mlabel, mod, right, og, float(S), vix_prev)
                if row is not None:
                    rows.append(row)
    return pd.DataFrame(rows, columns=CALIB_COLS)


def calibration_summary(calib, day):
    """Median/IQR of implied k by VIX tercile and by minute, plus the missing share in each group
    (docstring points 5-6); one `overall` row too."""
    if not len(calib):
        return pd.DataFrame(columns=CALIB_SUMMARY_COLS)
    dates = pd.DatetimeIndex(sorted(calib["date"].unique()))
    terc = vix_terciles(day.loc[dates, "vix_prev"])
    calib = calib.copy()
    calib["vix_tercile"] = pd.DatetimeIndex(calib["date"]).map(terc)
    rows = []
    for group_type, col in (("vix_tercile", "vix_tercile"), ("minute", "minute")):
        for val, g in calib.groupby(col):
            ok = g.loc[~g["missing"], "implied_k"]
            rows.append(dict(group_type=group_type, group_value=str(val), n=len(g),
                             median_implied_k=float(ok.median()) if len(ok) else np.nan,
                             iqr_implied_k=float(ok.quantile(0.75) - ok.quantile(0.25)) if len(ok) else np.nan,
                             missing_share=float(g["missing"].mean())))
    ok_all = calib.loc[~calib["missing"], "implied_k"]
    rows.append(dict(group_type="overall", group_value="ALL", n=len(calib),
                     median_implied_k=float(ok_all.median()) if len(ok_all) else np.nan,
                     iqr_implied_k=float(ok_all.quantile(0.75) - ok_all.quantile(0.25)) if len(ok_all) else np.nan,
                     missing_share=float(calib["missing"].mean())))
    return pd.DataFrame(rows, columns=CALIB_SUMMARY_COLS)


def write_calibration(path, calib, summary):
    """One csv, two blocks separated by a blank line (docstring point 6)."""
    with open(path, "w", newline="") as f:
        calib.to_csv(f, index=False, float_format="%.6f")
        f.write("\n")
        summary.to_csv(f, index=False, float_format="%.6f")


# ---------------------------------------------------------------------------------------------
# Re-evaluation
# ---------------------------------------------------------------------------------------------

def _entry_price(contract, mod):
    exact = contract[contract["mod"] == mod]
    if len(exact):
        return float(exact["close"].iloc[0]), False
    later = contract[contract["mod"] > mod].sort_values("mod")
    if len(later):
        return float(later["open"].iloc[0]), True
    return None, False


def _exit_price(contract, mod):
    exact = contract[contract["mod"] == mod]
    if len(exact):
        return float(exact["close"].iloc[0]), False
    earlier = contract[contract["mod"] < mod].sort_values("mod")
    if len(earlier):
        return float(earlier["close"].iloc[-1]), True
    return None, False


def reprice_trades(signal, dates, entry_mods, exit_mods, kinds, entry_px_pts, exit_px_pts, vix_prevs, opt_df, model_k):
    """Re-price one signal's trades with real bars; returns (trades_df, n_skipped) — see docstring
    points 7 and 9 for the entry/exit fallback rule and what counts as a skip."""
    rows, n_skipped = [], 0
    opt_by_date = {d: g for d, g in opt_df.groupby("date")}
    for date, entry_mod, exit_mod, kind, epts, xpts, vix_prev in zip(
            dates, entry_mods, exit_mods, kinds, entry_px_pts, exit_px_pts, vix_prevs):
        date = pd.Timestamp(date)
        right = "C" if kind == "c" else "P"
        og = opt_by_date.get(date)
        S = float(epts) / 10.0
        target = target_strike(S, kind)
        strikes = og.loc[og["right"] == right, "strike"] if og is not None else pd.Series([], dtype=float)
        K = nearest_listed(strikes, target)
        if og is None or K is None:
            n_skipped += 1
            continue
        contract = og[(og["right"] == right) & (og["strike"] == K)]
        entry_close, entry_fb = _entry_price(contract, int(entry_mod))
        if entry_close is None:
            n_skipped += 1
            continue
        exit_close, exit_fb = _exit_price(contract, REAL_EXIT_MOD)
        if exit_close is None:
            n_skipped += 1
            continue
        model_ret, _, _ = options.trade(epts, xpts, int(entry_mod), int(exit_mod), vix_prev, kind,
                                        k=model_k, itm=0.02, spread_pts=1.0, grid=options.GRID["SPX"], settle="cash")
        rows.append(dict(signal=signal, date=date, entry_mod=int(entry_mod), kind=kind, strike=K,
                         entry_close=entry_close, exit_close=exit_close, entry_fallback=entry_fb,
                         exit_fallback=exit_fb, raw_pnl_dollars=exit_close - entry_close,
                         pct_raw=(exit_close / entry_close - 1) * 100, model_pct=model_ret * 100))
    return pd.DataFrame(rows, columns=TRADE_COLS), n_skipped


def summarize_signal(signal, trades, n_skipped, all_dates):
    """One row per cost row (+$0.00/+$0.10/+$0.20) for `signal` (docstring points 10-14)."""
    n = len(trades)
    model_mean_pct = float(trades["model_pct"].mean()) if n else np.nan
    rows = []
    for cost_label, added in COST_ROWS:
        if n:
            net_dollar = trades["raw_pnl_dollars"] - added
            net_pct = trades["pct_raw"] - 100 * added / trades["entry_close"]
            mean_pct = float(net_pct.mean())
            label = "model optimistic here" if mean_pct < model_mean_pct else "model pessimistic here"
            rows.append(dict(signal=signal, cost_label=cost_label, added_cost_dollars=added, n=n,
                             n_skipped_missing=n_skipped, win=100 * (net_dollar > 0).mean(),
                             mean_pct_of_premium=mean_pct, median_pct=float(net_pct.median()),
                             worst_pct=float(net_pct.min()), model_mean_pct=model_mean_pct, label=label,
                             p_boot_day=stats.one_sided_p(net_pct.to_numpy(), stats.day_blocks(trades["date"])),
                             sharpe_calday=stats.calendar_day_sharpe(net_pct.to_numpy(), trades["date"], all_dates),
                             note="sub-window, not a verdict", spec=SPEC_NOTE))
        else:
            rows.append(dict(signal=signal, cost_label=cost_label, added_cost_dollars=added, n=0,
                             n_skipped_missing=n_skipped, win=np.nan, mean_pct_of_premium=np.nan,
                             median_pct=np.nan, worst_pct=np.nan, model_mean_pct=np.nan,
                             label="no re-priced trades", p_boot_day=np.nan, sharpe_calday=np.nan,
                             note="sub-window, not a verdict", spec=SPEC_NOTE))
    return rows


def _slug(name):
    """Exactly `pipeline.playbook.build`'s own per-trade filename slug."""
    return name.replace("|", "_").replace(">", "gt").replace("%", "pct").replace(":", "")


def d4_path(name, spread=1.0, settle="cash", k=1.0):
    return f"out/holdout_d4_{_slug(name)}_s{spread:.0f}_{settle}_k{k}.csv"


def post_selection_names():
    """Candidate names of the 15 POST-SELECTION rows, or [] if reconcile's holdout step hasn't run
    yet (docstring point 8)."""
    path = "out/reconcile_candidates.csv"
    if not os.path.exists(path):
        return []
    cand = pd.read_csv(path)
    if "window" not in cand or "label" not in cand:
        return []
    sub = cand[(cand["window"] == POST_WINDOW) & (cand["label"] == "POST-SELECTION")]
    return sorted(sub["candidate"].unique().tolist())


def process_d4_signal(name, model_k, opt_df, all_dates):
    """Re-price one D4-style signal (a per-trade file at `d4_path(name)`) on sessions >=
    2024-02-01; returns (trades, summary_rows, path); trades/summary_rows are None if the file
    does not exist."""
    path = d4_path(name)
    if not os.path.exists(path):
        return None, None, path
    df = pd.read_csv(path)
    df = df[pd.to_datetime(df["date"]) >= REEVAL_START].reset_index(drop=True)
    if len(df):
        trades, n_skipped = reprice_trades(name, df["date"], df["entry_mod"], df["exit_mod"], df["kind"],
                                           df["entry_px"], df["exit_px"], df["vix_prev"], opt_df, model_k)
    else:
        trades, n_skipped = pd.DataFrame(columns=TRADE_COLS), 0
    return trades, summarize_signal(name, trades, n_skipped, all_dates), path


def process_gapliq(day, opt_df, all_dates):
    """A39 T1/T2/T3 from out/gapliq_candidates_trades.csv on sessions >= 2024-02-01 (docstring
    point 7: fixed entry minute/kind reused from pipeline.units.gapliq, exit minute-of-day and
    prior-close VIX looked up from `day` by date since the trades file itself carries neither)."""
    path = "out/gapliq_candidates_trades.csv"
    trial_meta = {name: (gapliq.MOD_1000 if entry_col == "px_1000" else gapliq.MOD_0931, kind)
                 for name, _sig, entry_col, _dirn, kind, _t in gapliq.TRIALS}
    out_trades, out_rows = [], []
    if not os.path.exists(path):
        print(f"[NOTE] A41 realopt: {path} missing; cannot re-price A39 T1/T2/T3.")
        return out_trades, out_rows
    gtr = pd.read_csv(path)
    for trial in ("T1", "T2", "T3"):
        entry_mod, kind = trial_meta[trial]
        sub = gtr[(gtr["trial"] == trial) & (gtr["window"] == "HOLDOUT")
                 & (pd.to_datetime(gtr["date"]) >= REEVAL_START)].reset_index(drop=True)
        if len(sub):
            dvals = pd.to_datetime(sub["date"])
            in_day = dvals.isin(day.index)
            n_no_ref = int((~in_day).sum())    # a real trade date with no session in `day` (feed gap)
            sub = sub[in_day.to_numpy()].reset_index(drop=True)
            dvals = pd.to_datetime(sub["date"])
            trades, n_skipped = reprice_trades(trial, sub["date"], np.full(len(sub), entry_mod),
                                               day.loc[dvals, "last_mod"].to_numpy(), [kind] * len(sub),
                                               sub["entry_px"], sub["exit_px"],
                                               day.loc[dvals, "vix_prev"].to_numpy(), opt_df, GAPLIQ_K)
            n_skipped += n_no_ref
        else:
            trades, n_skipped = pd.DataFrame(columns=TRADE_COLS), 0
        out_trades.append(trades)
        out_rows.extend(summarize_signal(trial, trades, n_skipped, all_dates))
    return out_trades, out_rows


def load_option_file(path):
    df = (read_option_bars(option_shards(path)) if not os.path.exists(path) else pd.read_csv(path, dtype={"right": str}))
    ts_ny = pd.to_datetime(df["ts"], utc=True).dt.tz_convert(sessions.NY)
    df["date"] = ts_ny.dt.tz_localize(None).dt.normalize()
    df["mod"] = ts_ny.dt.hour * 60 + ts_ny.dt.minute
    df["expiry"] = pd.to_datetime(df["expiry"]).dt.normalize()
    df["strike"] = df["strike"].astype(float)
    df = df[df["date"] == df["expiry"]]     # 0DTE guard (docstring point 15)
    return df.reset_index(drop=True)


def _trades_path(out):
    return out[:-4] + "_trades.csv" if out.endswith(".csv") else out + "_trades.csv"


def _write_header_only(out, calib_out=CALIB_OUT):
    pd.DataFrame(columns=OUT_COLS).to_csv(out, index=False)
    pd.DataFrame(columns=TRADE_COLS).to_csv(_trades_path(out), index=False)
    pd.DataFrame(columns=CALIB_COLS).to_csv(calib_out, index=False)


def main(inp, out, ext_path=EXT_OPT_PATH, calib_out=CALIB_OUT):
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    if inp != "extended":
        raise ValueError(f"pipeline.units.realopt only supports --in extended (got {inp!r})")
    shards = option_shards(ext_path)
    if not shards:
        print(f"[SKIP] A41 waits for {ext_path} (DATA.md)")
        _write_header_only(out, calib_out)
        return
    opt_df = load_option_file(ext_path)
    if opt_df.empty:
        raise ValueError(f"{ext_path} has no same-day-expiry rows")

    td = sessions.trading_days_from_vix()
    frame, _dropped, meta = sessions.build_extended(trading_days=td)
    vix = pd.read_parquet("data/raw/vix_daily.parquet")
    day = signals.day_table(frame, vix, dividends=meta["dividends"] if meta else None, trading_days=td,
                            roll_dates=meta["roll_dates"] if meta else ())

    calib = run_calibration(opt_df, day, frame)
    write_calibration(calib_out, calib, calibration_summary(calib, day))

    opt_last_date = opt_df["date"].max()
    all_dates = [d for d in td if REEVAL_START <= d <= opt_last_date]

    all_trades, all_summ = [], []
    winner_name = insample.winner_from_decision()
    for name, model_k in ((winner_name, 1.0), (GAP_NAME, 1.3)):
        trades, summ, path = process_d4_signal(name, model_k, opt_df, all_dates)
        if trades is None:
            print(f"[NOTE] A41 realopt: {path} missing; cannot re-price {name!r} (D4 per-trade file not found).")
            continue
        all_trades.append(trades)
        all_summ.extend(summ)

    post_names = post_selection_names()
    found_post = [n for n in post_names if os.path.exists(d4_path(n))]
    if post_names and not found_post:
        print(f"[NOTE] A41 realopt: 0 of {len(post_names)} POST-SELECTION rows have a per-trade file "
              f"(out/holdout_d4_<name>_s1_cash_k1.0.csv) -- pipeline.playbook.build only ever prices the "
              f"two pre-registered D4 signals, so these do not exist on this branch; skipped per the "
              f"amendment's own escape clause.")
    elif not post_names:
        print("[NOTE] A41 realopt: out/reconcile_candidates.csv has no POST-SELECTION rows yet "
              "(`pipeline.reconcile holdout` has not run); skipped.")
    for name in found_post:
        trades, summ, _path = process_d4_signal(name, 1.0, opt_df, all_dates)
        if trades is not None:
            all_trades.append(trades)
            all_summ.extend(summ)

    gap_trades, gap_rows = process_gapliq(day, opt_df, all_dates)
    all_trades.extend(gap_trades)
    all_summ.extend(gap_rows)

    res = pd.DataFrame(all_summ, columns=OUT_COLS) if all_summ else pd.DataFrame(columns=OUT_COLS)
    res.to_csv(out, index=False, float_format="%.6f")
    # drop 0-row frames before concat (a pandas FutureWarning otherwise; they add no rows either way)
    non_empty = [t for t in all_trades if len(t)]
    tr_all = pd.concat(non_empty, ignore_index=True) if non_empty else pd.DataFrame(columns=TRADE_COLS)
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
        # A38's contract, copied verbatim (see module docstring): header-only outputs, never a
        # .error file, exit 0 -- this pre-registered-but-not-yet-runnable unit must never fail
        # `make all`.
        traceback.print_exc()
        _write_header_only(a.out)
    sys.exit(0)
