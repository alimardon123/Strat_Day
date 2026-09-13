"""Event-day long volatility on real 0DTE prices (A42, pre-registered 2026-09-13 15:40 UTC,
before any real option bar exists; NOT tuned to look good). Question: does a long call plus a
long put (two separate long positions) bought before a scheduled announcement earn more than its
premium, i.e. is 0DTE implied volatility too LOW into events? Mechanism: the announcement forces
repricing at a known minute; the counterparty is the 0DTE premium seller.

    python -m pipeline.units.eventvol --in extended --out out/eventvol_candidates.csv

Exactly three trials, all counted (A42, family 36 -> 39): E1 baseline, every session, nearest-ATM
call and put bought at the 09:31 bar close, held to the 15:59 close; E2 FOMC statement days only
(the published 2024-2026 schedule below), nearest-ATM call and put bought at the 13:30 bar close,
held to the 15:59 close (n ~ 20 -> UNDERPOWERED by construction, reported, never promoted); E3 the
E2 rule on every non-FOMC session (the matched day-selection control, also a trial -- E2 and E3
exactly partition E1's day population). Costs: $0 / $0.10 / $0.20 round trip, ONE flat amount
charged once per two-leg trade (never split or halved across the two legs -- see point 6 below).

`data/ext/spy_0dte_1min_2024-02_2026-09.csv.gz` (tools/fetch_spy_0dte_local.py) does NOT exist on
this branch yet: without it, this unit prints `[SKIP] ...` and writes both output files with a
header row only, exit 0 -- exactly pipeline.units.letf's (A38) contract, NOT pipeline.units._gh.
run's empty-file+`.error`+exit-2 convention used by the rest of the fleet (A32): a not-yet-runnable,
pre-registered candidate must never fail `make all`. On ANY exception (missing file, bad data, a
bug) the same header-only-outputs-and-exit-0 contract applies.

Every ambiguity the amendment left open is fixed here and restated in the `spec` column
(SPEC_NOTE below); worth flagging up front:
(1) "nearest-ATM call and put" -- the amendment names the reference price only for E1 ("strike
    nearest the SPY price at 09:31 from the branch's minute file via the session builder, ÷10 to
    dollars"): `sessions.build_extended`'s minute frame is Oanda SPX + the ext feed, both in SPX
    POINTS (gapliq.py/letf.py's own convention, confirmed by `pipeline.options.GRID["SPY"] = 10.0`,
    "SPY's $1 grid = 10 SPX-equivalent points", A8/A28) -- so the 09:31 SPX-point close ÷ 10 is the
    SPY-dollar proxy used to pick the nearest strike from the real (dollar-denominated) chain,
    because the 0DTE file itself carries no underlying-price column. E2/E3 read "nearest-ATM call
    and put at the 13:30 bar close" as the SAME method at 13:30 (the trial's own entry minute),
    not a fixed 09:31 reference reused for a 13:30 entry -- the most literal, symmetric reading. A
    single strike K (nearest to the reference price among ALL strikes present that day, either
    right, ties broken toward the smaller strike for determinism) is used for BOTH the call and
    the put leg, matching "nearest-ATM call and put" naming one strike for the pair, not a spread.
(2) Entry: the leg's own 1-minute bar close at the exact entry minute (09:31 / 13:30 NY) if
    present; else the leg's NEXT available bar's open (literal "a leg whose entry bar is missing
    uses the next bar's open", no minute-window cap, unlike signals.day_table's 5-minute-tolerance
    decision prices, because the amendment doesn't name one here); a leg with NO bar at or after
    the entry minute has "neither" and the WHOLE DAY is skipped and counted (n_skipped) -- per
    trial, not per leg, since a lone surviving leg is a single naked option, not the two-leg
    position the amendment prices.
(3) Exit: the leg's own bar close at the exact 15:59 NY minute if present (A41's own reasoning:
    "SPY 0DTE settle physically at 16:00; the 15:59 close is the last tradable print"); else the
    LAST available bar at or before 15:59 (and strictly after the entry minute actually used) is
    read as that leg's last tradable print, mirroring the entry-side fallback's spirit. The
    amendment names no exit-side fallback (real 0DTE options are expected to print into the
    close); a leg with no such bar either is treated the same as a missing leg -- day skipped and
    counted -- for a well-defined, deterministic P&L on every counted trade.
(4) Day population (single window, see point 9): `sessions.trading_days_from_vix()`, the
    codebase's canonical NYSE calendar, restricted to [min(expiry), max(expiry)] of the loaded
    file (not the fetch tool's own START/END constants, so the window always matches whatever the
    file on disk actually covers). E1 = every day in that population; E2 = the fixed FOMC list
    (below) intersected with it; E3 = the population minus E2 -- so E1's day-set is exactly
    E2 UNION E3 by construction, and a day counted skipped for data reasons is charged to exactly
    one trial's n_skipped (E1, and either E2 or E3, never both -- E2/E3 are disjoint).
(5) FOMC dates are the amendment's own published-schedule list, hardcoded (FOMC_DATES below); a
    listed date outside the loaded file's coverage window simply is not part of any trial's day
    population (it is not "skipped", since it was never a candidate day this run).
(6) Costs: A41's $0.10 / $0.20 round trips, PLUS a $0 row (A41's own third "zero added cost since
    bar closes already sit inside the spread" row) -- three rows per trial, ONE flat dollar amount
    subtracted once from the two-leg trade's total P&L (never split, never halved, never applied
    per leg), reading "costs ... per leg-pair" together with "one round trip per trade" in the
    amendment literally: the round trip is priced once for the pair, not once per leg.
(7) P&L: gross_usd = (call_exit + put_exit) - (call_entry + put_entry); gross_pct = gross_usd /
    (call_entry + put_entry) * 100; net_usd = gross_usd - cost; net_pct = gross_pct -
    100*cost/(call_entry+put_entry) (same "net_pct = gross_pct - 100*cost/entry_px" convention as
    letf.py/gapliq.py). All dollar figures are the raw per-share bar prices in the file (SPY
    dollars, A41's own units) with NO x100 contract multiplier -- the pre-registration never names
    a contract count or notional, so this is reported per share, exactly as booked.
(8) `win`/`mean_pct`/`median_pct`/`worst_pct`/`mean_usd` are all NET of that row's own `cost`
    (unlike letf.py/gapliq.py's `win`, which is gross, because there `cost` is a pair of SUFFIXED
    COLUMNS on one row; here `cost` is a ROW, so the natural, useful number at each cost row is
    the net one -- "does this trial still win at this cost").
(9) Windows: the whole file (2024-02 onward) is reported as ONE out-of-sample window by
    construction (no CONTEXT/SELECTION/HOLDOUT split -- there is no real-priced 0DTE history
    before this file, so there is nothing to select on and nothing prior to hold out against).
(10) `sharpe_calday` zero-fills over each TRIAL'S OWN day population (E1: every window day; E2:
    the FOMC days in the window; E3: the window days minus E2) -- letf.py's "has_assets"-population
    convention, not gapliq.py's "every trading day for every trial" convention, because E2 and E3
    are disjoint day-sets by construction and pooling them would double-count or misattribute the
    zero-fill.
(11) DSR at N=39 (A42's own "family 36 -> 39" text) uses, PER COST ROW, this run's own three
    trials' per-trade Sharpe (at that SAME cost) as the SR0 pool -- letf.py's/gapliq.py's "this
    run's own trials only" convention, extended across the cost dimension since cost is a row here
    (a trial's per-trade Sharpe shifts with cost, so the peer pool must be evaluated at the same
    cost to be comparable).
(12) `e2_minus_e3_pct` / `p_e2_vs_e3` are populated on the E2 rows only (NaN on E1/E3), per cost:
    E2's mean_pct minus E3's mean_pct at that SAME cost. `p_e2_vs_e3` is a NEW two-sample day-block
    bootstrap (`two_sample_block_p` below) -- NOT pipeline.stats.one_sided_p/block_bootstrap_p,
    which test one sample's mean against zero -- because E2 and E3 are two independent, disjoint
    day-sets whose MEANS are being compared to each other. It follows
    research/thread_B_inversion/stats_engine.block_bootstrap_p's day-block technique (each side
    centred on the pooled grand mean, so the null is "no true difference"; day-blocks resampled
    with replacement independently on each side; same n_boot=2000, seed=11 as every other
    bootstrap in this codebase, pipeline.stats.N_BOOT/SEED) but reports the TWO-SIDED p (no
    one-sided halving -- the amendment states a directional LOW-MEDIUM prior but not a one-sided
    test convention for a two-sample comparison, unlike the one-sample `p_boot_day` columns, which
    keep Thread B's one-sided halving as-is). NaN when either side has fewer than
    `pipeline.stats.MIN_BLOCKS` (20) distinct days, matching every other bootstrap p in this
    codebase.
(13) `underpowered` = n < 200, identical across a trial's three cost rows (n does not depend on
    cost); this fires by construction for every E2 row (n ~ 20) and is reported, never promoted,
    per the amendment's own text.
"""
import argparse
import os
import sys
import traceback

import numpy as np
import pandas as pd

from pipeline import sessions, stats

DATA_PATH = "data/ext/spy_0dte_1min_2024-02_2026-09.csv.gz"   # single-file layout (message text)
DATA_GLOB = "data/ext/spy_0dte_1min_*.csv.gz"                  # or per-year shards from the fetch helper


def option_shards(data_path=DATA_PATH):
    """One file or per-year shards (< 100 MB each), sorted; temp files excluded."""
    import glob
    paths = sorted(q for q in glob.glob(DATA_GLOB) if not q.endswith(".tmp.csv"))
    if data_path and os.path.exists(data_path) and data_path not in paths:
        paths.append(data_path)
    return paths
REQUIRED_COLS = {"ts", "expiry", "strike", "right", "open", "high", "low", "close", "volume"}
NY = "America/New_York"

MOD_0931 = 9 * 60 + 31      # 571, E1 entry
MOD_1330 = 13 * 60 + 30     # 810, E2/E3 entry
MOD_1559 = 15 * 60 + 59     # 959, every trial's exit ("the last tradable print", A41)

COST0, COST1, COST2 = 0.0, 0.10, 0.20     # round trip, once per two-leg trade (point 6)
COSTS = [COST0, COST1, COST2]
DSR_N = 39                                 # A42's own "family 36 -> 39"
N_BOOT = stats.N_BOOT                      # 2000
BOOT_SEED = stats.SEED                     # 11

FOMC_DATES = [    # ACCEPTANCE A42's published schedule, verbatim
    "2024-01-31", "2024-03-20", "2024-05-01", "2024-06-12", "2024-07-31", "2024-09-18", "2024-11-07", "2024-12-18",
    "2025-01-29", "2025-03-19", "2025-05-07", "2025-06-18", "2025-07-30", "2025-09-17", "2025-10-29", "2025-12-10",
    "2026-01-28", "2026-03-18", "2026-04-29", "2026-06-17", "2026-07-29",
]

TRADE_RAW_COLS = ["date", "strike", "ref_px",
                  "call_entry_px", "call_entry_mod", "call_exit_px", "call_exit_mod",
                  "put_entry_px", "put_entry_mod", "put_exit_px", "put_exit_mod",
                  "premium_total", "exit_total", "gross_usd", "gross_pct"]
TRADE_COLS = ["trial"] + TRADE_RAW_COLS + ["net_usd_cost0", "net_pct_cost0",
                                          "net_usd_cost1", "net_pct_cost1",
                                          "net_usd_cost2", "net_pct_cost2"]
OUT_COLS = ["trial", "cost", "n", "n_skipped", "win", "mean_pct", "median_pct", "worst_pct", "mean_usd",
            "p_boot_day", "sharpe_calday", "dsr_N39", "e2_minus_e3_pct", "p_e2_vs_e3", "underpowered", "spec"]

SPEC_NOTE = (
    "FIXED (pre-registration, A42): E1 every session, nearest-ATM call and put at the 09:31 bar "
    "close, held to 15:59; E2 the published FOMC-statement-day schedule (21 dates, 2024-2026), "
    "nearest-ATM call and put at the 13:30 bar close, held to 15:59 (n ~ 20 -> UNDERPOWERED by "
    "construction, never promoted); E3 the E2 rule on every non-FOMC session (E2 and E3 exactly "
    "partition E1's day population). Nearest-ATM strike: the day's SPX-point minute close at the "
    "trial's own entry minute (sessions.build_extended), divided by 10 for a SPY-dollar reference, "
    "nearest available strike among either right that day, ties toward the smaller strike; the SAME "
    "strike prices both legs. Entry = the leg's bar close at the exact entry minute, else the next "
    "available bar's open; exit = the bar close at the exact 15:59 minute, else the last available "
    "bar at/before 15:59 after entry; a leg with neither at either end skips and counts the whole "
    "day (never a lone naked leg). Costs $0/$0.10/$0.20 round trip, charged ONCE per two-leg trade "
    "(never split or halved across the legs). P&L in SPY dollars (raw per-share bar prices, no x100 "
    "multiplier) and in % of total premium paid; win/mean/median/worst/mean_usd are net of that "
    "row's own cost. Day population: sessions.trading_days_from_vix() restricted to the loaded "
    "file's own [min(expiry), max(expiry)] -- one out-of-sample window by construction, no "
    "CONTEXT/SELECTION/HOLDOUT split. p_boot_day: pipeline.stats.one_sided_p, day blocks, n_boot "
    "2000, seed 11, zero-filled over the trial's OWN day population for sharpe_calday. DSR at N=39 "
    "(family 36->39) per cost row, using this run's own three trials' per-trade Sharpe AT THAT COST "
    "as the SR0 pool. e2_minus_e3_pct/p_e2_vs_e3 (E2 rows only): E2 mean_pct - E3 mean_pct per cost, "
    "with a NEW two-sample day-block bootstrap p (two-sided, n_boot 2000, seed 11, NaN below 20 "
    "distinct days on either side) -- not pipeline.stats's one-sample convention, since E2/E3 are "
    "two disjoint day-sets being compared to each other, not one sample against zero. underpowered "
    "= n < 200. On ANY exception (including the 0DTE file being absent) this unit writes header-only "
    "outputs and exits 0, exactly pipeline.units.letf's (A38) contract, not pipeline.units._gh.run's "
    "empty-file+.error+exit-2 convention used by the rest of the fleet (A32) -- this pre-registered, "
    "not-yet-runnable candidate must never fail `make all` before its data exists.")


def fomc_dates():
    return [pd.Timestamp(d) for d in FOMC_DATES]


def load_0dte(path):
    """Validate and normalise the real 0DTE file (tools/fetch_spy_0dte_local.py's own format):
    ts (UTC) -> NY minute-of-day, expiry -> a plain 'YYYY-MM-DD' session key, right upper-cased."""
    paths = [path] if os.path.exists(path) else option_shards(path)
    df = pd.concat([pd.read_csv(q, dtype={"right": str}) for q in paths], ignore_index=True)
    missing = REQUIRED_COLS - set(df.columns)
    if missing:
        raise ValueError(f"{path} missing required column(s): {sorted(missing)}")
    df = df.copy()
    df["right"] = df["right"].astype(str).str.upper()
    df["expiry"] = pd.to_datetime(df["expiry"]).dt.strftime("%Y-%m-%d")
    ts_ny = pd.to_datetime(df["ts"], utc=True).dt.tz_convert(NY)
    df["mod"] = ts_ny.dt.hour * 60 + ts_ny.dt.minute
    for c in ("strike", "open", "close"):
        df[c] = df[c].astype(float)
    return df[["expiry", "strike", "right", "mod", "open", "close"]]


def ref_price_series(frame, mod):
    """{date -> SPY-dollar reference price} at minute-of-day `mod`: the extended frame's SPX-point
    minute close divided by 10 (module docstring point 1)."""
    s = frame.loc[frame["mod"] == mod].groupby("date")["close"].first()
    return (s / 10.0).to_dict()


def nearest_strike(options_day, ref_px):
    """The strike (either right) closest to `ref_px` among the day's contracts; ties toward the
    smaller strike for determinism. None when the day has no contracts at all."""
    strikes = sorted(set(options_day["strike"].to_numpy(float)))
    if not strikes:
        return None
    return min(strikes, key=lambda s: (abs(s - ref_px), s))


def _leg_prices(rows, entry_mod, exit_mod):
    """One leg's (entry_px, entry_used_mod, exit_px, exit_used_mod), or None if the leg cannot be
    priced (module docstring points 2-3): exact bar close at `entry_mod`, else the next available
    bar's open; exact bar close at `exit_mod`, else the last available bar at/before `exit_mod`
    strictly after the entry actually used. None (never a partial leg) when neither side exists."""
    if not len(rows):
        return None
    rows = rows.sort_values("mod")
    exact_entry = rows.loc[rows["mod"] == entry_mod]
    if len(exact_entry):
        entry_px, entry_used_mod = float(exact_entry["close"].iloc[0]), entry_mod
    else:
        nxt = rows.loc[rows["mod"] > entry_mod]
        if not len(nxt):
            return None
        entry_px, entry_used_mod = float(nxt["open"].iloc[0]), int(nxt["mod"].iloc[0])
    exact_exit = rows.loc[rows["mod"] == exit_mod]
    if len(exact_exit):
        exit_px, exit_used_mod = float(exact_exit["close"].iloc[0]), exit_mod
    else:
        prior = rows.loc[(rows["mod"] <= exit_mod) & (rows["mod"] > entry_used_mod)]
        if not len(prior):
            return None
        exit_px, exit_used_mod = float(prior["close"].iloc[-1]), int(prior["mod"].iloc[-1])
    return entry_px, entry_used_mod, exit_px, exit_used_mod


def pair_trade(options_day, ref_px, entry_mod, exit_mod=MOD_1559):
    """The nearest-ATM call+put pair for one session (module docstring point 1): one strike K
    priced through `_leg_prices` for both rights. None if the strike cannot be found or EITHER leg
    cannot be priced ('a day where either leg has neither is skipped and counted')."""
    K = nearest_strike(options_day, ref_px)
    if K is None:
        return None
    call = _leg_prices(options_day.loc[(options_day["right"] == "C") & (options_day["strike"] == K)],
                       entry_mod, exit_mod)
    put = _leg_prices(options_day.loc[(options_day["right"] == "P") & (options_day["strike"] == K)],
                      entry_mod, exit_mod)
    if call is None or put is None:
        return None
    c_entry, c_entry_mod, c_exit, c_exit_mod = call
    p_entry, p_entry_mod, p_exit, p_exit_mod = put
    premium = c_entry + p_entry
    exit_total = c_exit + p_exit
    return dict(strike=K, ref_px=ref_px,
               call_entry_px=c_entry, call_entry_mod=c_entry_mod, call_exit_px=c_exit, call_exit_mod=c_exit_mod,
               put_entry_px=p_entry, put_entry_mod=p_entry_mod, put_exit_px=p_exit, put_exit_mod=p_exit_mod,
               premium_total=premium, exit_total=exit_total, gross_usd=exit_total - premium,
               gross_pct=(exit_total / premium - 1) * 100 if premium else np.nan)


def build_trades(groups, ref, days, entry_mod, exit_mod=MOD_1559):
    """One row per day where a full two-leg trade could be priced (see pair_trade); returns
    (trades_df, n_skipped) over `days` (the trial's own day population, module docstring point 4)."""
    empty = pd.DataFrame(columns=["strike", "right", "mod", "open", "close"])
    rows, n_skipped = [], 0
    for d in days:
        ref_px = ref.get(d)
        if ref_px is None:
            n_skipped += 1
            continue
        options_day = groups.get(d.strftime("%Y-%m-%d"), empty)
        trade = pair_trade(options_day, ref_px, entry_mod, exit_mod)
        if trade is None:
            n_skipped += 1
            continue
        trade["date"] = d
        rows.append(trade)
    return pd.DataFrame(rows, columns=TRADE_RAW_COLS), n_skipped


def with_costs(trades):
    """Adds net_usd_cost{0,1,2}/net_pct_cost{0,1,2}: cost is ONE flat dollar amount subtracted once
    per two-leg trade (module docstring point 6), never split or halved across the two legs."""
    out = trades.copy()
    for i, c in enumerate(COSTS):
        out[f"net_usd_cost{i}"] = out["gross_usd"] - c
        out[f"net_pct_cost{i}"] = out["gross_pct"] - 100 * c / out["premium_total"]
    return out


def two_sample_block_p(vals_a, dates_a, vals_b, dates_b, n_boot=N_BOOT, seed=BOOT_SEED):
    """Two-sided day-block bootstrap p for mean(A) != mean(B), two INDEPENDENT day-sets (module
    docstring point 12) -- not pipeline.stats's one-sample-against-zero convention. Each side is
    centred on the pooled grand mean (the null: A and B are draws from the same distribution),
    re-blocked by day and resampled with replacement, mirroring
    research/thread_B_inversion/stats_engine.block_bootstrap_p's day-block technique. NaN if
    either side has fewer than pipeline.stats.MIN_BLOCKS (20) distinct days."""
    vals_a, vals_b = np.asarray(vals_a, float), np.asarray(vals_b, float)
    blocks_a, blocks_b = stats.day_blocks(dates_a), stats.day_blocks(dates_b)
    if stats.n_blocks(blocks_a) < stats.MIN_BLOCKS or stats.n_blocks(blocks_b) < stats.MIN_BLOCKS:
        return np.nan
    obs = vals_a.mean() - vals_b.mean()
    grand = np.concatenate([vals_a, vals_b]).mean()
    ca, cb = vals_a - vals_a.mean() + grand, vals_b - vals_b.mean() + grand
    codes_a, uniq_a = pd.factorize(blocks_a)
    codes_b, uniq_b = pd.factorize(blocks_b)
    grp_a = [ca[codes_a == i] for i in range(len(uniq_a))]
    grp_b = [cb[codes_b == i] for i in range(len(uniq_b))]
    na, nb = len(grp_a), len(grp_b)
    rng = np.random.default_rng(seed)
    diffs = np.empty(n_boot)
    for i in range(n_boot):
        pick_a = rng.integers(0, na, na)
        pick_b = rng.integers(0, nb, nb)
        diffs[i] = (np.concatenate([grp_a[j] for j in pick_a]).mean()
                   - np.concatenate([grp_b[j] for j in pick_b]).mean())
    return float((np.abs(diffs) >= abs(obs)).mean())


def summarize_row(name, cost_idx, trades, days):
    """One (trial, cost) row, net of `COSTS[cost_idx]` (module docstring point 8)."""
    net_usd_col, net_pct_col = f"net_usd_cost{cost_idx}", f"net_pct_cost{cost_idx}"
    n = len(trades)
    net_pct = trades[net_pct_col].to_numpy(float) if n else np.array([])
    net_usd = trades[net_usd_col].to_numpy(float) if n else np.array([])
    row = dict(trial=name, cost=COSTS[cost_idx], n=n, n_skipped=None,
              win=(100 * (net_usd > 0).mean()) if n else np.nan,
              mean_pct=net_pct.mean() if n else np.nan,
              median_pct=float(np.median(net_pct)) if n else np.nan,
              worst_pct=net_pct.min() if n else np.nan,
              mean_usd=net_usd.mean() if n else np.nan)
    row["p_boot_day"] = stats.one_sided_p(net_pct, stats.day_blocks(trades["date"])) if n else np.nan
    row["sharpe_calday"] = stats.calendar_day_sharpe(net_pct, trades["date"], days)
    row["underpowered"] = bool(n < 200)
    return row


def main(inp, out, data_path=DATA_PATH):
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    if inp != "extended":
        raise ValueError(f"pipeline.units.eventvol only supports --in extended (got {inp!r})")
    if not option_shards(data_path):
        print(f"[SKIP] A42 waits for {data_path} (tools/fetch_spy_0dte_local.py)")
        _write_header_only(out)
        return

    odte = load_0dte(data_path)
    td = sessions.trading_days_from_vix()
    frame, _dropped, _meta = sessions.build_extended(trading_days=td)
    file_start, file_end = pd.Timestamp(odte["expiry"].min()), pd.Timestamp(odte["expiry"].max())
    window_days = sorted(d for d in td if file_start <= d <= file_end)
    fomc = set(fomc_dates())
    e2_days = sorted(set(window_days) & fomc)
    e3_days = sorted(set(window_days) - fomc)

    ref_0931 = ref_price_series(frame, MOD_0931)
    ref_1330 = ref_price_series(frame, MOD_1330)
    groups = dict(tuple(odte.groupby("expiry")))

    # name, day population, entry minute, reference-price map (module docstring points 1, 4)
    trial_defs = [("E1", window_days, MOD_0931, ref_0931),
                 ("E2", e2_days, MOD_1330, ref_1330),
                 ("E3", e3_days, MOD_1330, ref_1330)]
    trial_trades, trial_n_skipped = {}, {}
    for name, days, entry_mod, ref in trial_defs:
        trades, n_skipped = build_trades(groups, ref, days, entry_mod)
        trial_trades[name] = with_costs(trades)
        trial_n_skipped[name] = n_skipped

    rows = []
    for ci in range(len(COSTS)):
        pool = [stats.per_trade_sharpe(trial_trades[name][f"net_pct_cost{ci}"].to_numpy(float))
               for name, *_ in trial_defs]
        e2_vals = trial_trades["E2"][f"net_pct_cost{ci}"].to_numpy(float)
        e3_vals = trial_trades["E3"][f"net_pct_cost{ci}"].to_numpy(float)
        e2_minus_e3 = float(e2_vals.mean() - e3_vals.mean()) if len(e2_vals) and len(e3_vals) else np.nan
        p_e2_vs_e3 = (two_sample_block_p(e2_vals, trial_trades["E2"]["date"], e3_vals, trial_trades["E3"]["date"])
                     if len(e2_vals) and len(e3_vals) else np.nan)
        for name, days, entry_mod, ref in trial_defs:
            trades = trial_trades[name]
            row = summarize_row(name, ci, trades, days)
            row["n_skipped"] = trial_n_skipped[name]
            row["dsr_N39"] = (stats.deflated_sharpe(trades[f"net_pct_cost{ci}"].to_numpy(float), sr_trials=pool, n=DSR_N)[0]
                              if len(trades) >= 3 else np.nan)
            row["e2_minus_e3_pct"] = e2_minus_e3 if name == "E2" else np.nan
            row["p_e2_vs_e3"] = p_e2_vs_e3 if name == "E2" else np.nan
            row["spec"] = SPEC_NOTE
            rows.append(row)

    res = pd.DataFrame(rows)[OUT_COLS]
    res.to_csv(out, index=False, float_format="%.6f")
    trade_frames = [trial_trades[name].assign(trial=name)[TRADE_COLS] for name, *_ in trial_defs]
    tr_all = pd.concat(trade_frames, ignore_index=True) if trade_frames else pd.DataFrame(columns=TRADE_COLS)
    tr_all.sort_values(["trial", "date"]).to_csv(_trades_path(out), index=False, float_format="%.6f")
    print(res.to_string(index=False, float_format=lambda x: f"{x:.4f}"))


def _trades_path(out):
    """`out/eventvol_candidates.csv` -> `out/eventvol_trades.csv` (the task's own fixed pair of
    filenames, dropping the `_candidates` middle part -- unlike letf.py/gapliq.py, which just
    append `_trades.csv` after stripping `.csv`); any other `--out` value falls back to that
    generic suffix rule (used by the tests' tempfile paths)."""
    if out.endswith("_candidates.csv"):
        return out[:-len("_candidates.csv")] + "_trades.csv"
    return out[:-4] + "_trades.csv" if out.endswith(".csv") else out + "_trades.csv"


def _write_header_only(out):
    pd.DataFrame(columns=OUT_COLS).to_csv(out, index=False)
    pd.DataFrame(columns=TRADE_COLS).to_csv(_trades_path(out), index=False)


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
