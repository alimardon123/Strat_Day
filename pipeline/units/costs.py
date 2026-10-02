"""The real cost of the programme's 0DTE instrument, measured at bid and ask (A51 as clarified by A51a,
pre-registered 2026-10-02, before any quote exists on the branch and before any code). A MEASUREMENT, not a
candidate: ZERO new trials, nothing here can be promoted, no published number or label is revised.

    python -m pipeline.units.costs --in data/ext --out out/costs_decision.csv

`--in` is the directory holding `spy_0dte_quotes_1min_<YYYY-MM>.csv.gz` (columns ts,expiry,strike,right,bid,ask,
bid_size,ask_size; ts = UTC `YYYY-MM-DD HH:MM:SS` on a whole minute = the instant the consolidated BBO applies),
`quotes_manifest.json` and the trade shards `spy_0dte_1min_*.csv.gz` (V2 only). The other six outputs are written
next to `--out`, in its directory, under their fixed names: costs_surface (M1), costs_decision + costs_sessions
(M2), costs_depth (M3), costs_reread (M4), costs_trackc (M5), costs_validation (V1-V3).

BEHAVIOUR WHEN DATA IS ABSENT OR BROKEN (A38/A41 convention for the absent case, A32 for the broken one):
  * no quote shard: prints `[SKIP] A51 waits for <in>/spy_0dte_quotes_1min_*.csv.gz`, writes HEADER-ONLY versions
    of all seven outputs, exits 0, no `.error`. The canonical frame is not built on this path.
  * shards present but the manifest missing/invalid, or V1/V2/V3 fails: M1-M5 are header-only, costs_validation
    carries the check rows (the failing ones included), and the unit raises, so `pipeline.units._gh.run` leaves
    `<out>.error` and exits 2 (it also truncates `<out>` itself, the decision file, to zero bytes). "On any V1-V3
    failure nothing is published" (A51): visible failure, never silent.

Units: every cost is reported in SPX index points = 10 x SPY dollars (`SPX_PER_SPY`), the survival rule's unit;
dollars are kept where A51 asks for them. Floats are written with "%.6f", rows are sorted by explicit keys, the
only randomness is `np.random.default_rng(11)` (one fresh generator per bootstrap cell), so two runs are
byte-identical.

Where each A51 measurement lives:
  M1 `surface_legs` + `surface_table`          M2 `decision_legs` + `session_table` + `decision_row`
  M3 `depth_legs` + `depth_table`              M4 `run_reread` / `reread_table` (pipeline.units.costs_reread)
  M5 `trackc_sessions` + `trackc_table`        V1 `check_v1`   V2 `check_v2`   V3 `check_v3`

Every point A51/A51a leave open is fixed here, restated in the `spec` column of costs_decision.csv and in the
hand-back (SPEC_NOTE below is the fixed text):
(1) Prevailing quote at instant t (A51 + A51a): the latest row with ts <= t, same NY session, same contract, no
    older than the staleness limit; otherwise the leg is missing (counted, never filled). The limit is a FUNCTION
    OF THE MANIFEST: `rows_on_change` true (Databento cbbo-1m emits a row only when the BBO changes, so a missing
    row means "unchanged") -> 30 minutes; false or absent -> A51's 5 minutes. "No older than" is inclusive: a
    row exactly at the limit is valid, one second past it is not. A row with an empty/NaN bid or ask is the
    vendor's empty-book record = no quote at that instant: it is KEPT as the prevailing row and the leg is
    missing, never filled from an older priced row. A row with ts > t is never visible (no look-ahead). Duplicate
    (contract, ts) rows: the last one in file order wins. Rows whose `expiry` is not the NY date of their ts are
    dropped with a [NOTE] (the file is same-day contracts only; realopt's 0DTE guard).
(2) Underlying S at t = the canonical frame's close of the bar ENDING at t (bar mod = mod(t) - 1) / 10. A bar
    missing from the frame makes the leg missing.
(3) Session universe. DECISION = NY dates 2026-03-02..2026-09-11 that are in the canonical frame OR in the quote
    file, minus the manifest's `excluded_sessions` (A51a: vendor-degraded or missing days, excluded from EVERY
    statistic M1-M5 and V1-V3: they leave the session universe before anything is computed). A DECISION session with no
    quote at all therefore counts as 10 missing legs in the coverage gate - a missing day can never hide. Quote-
    file sessions outside the window enter M1 only, by calendar quarter ("2025Q4"), as context, never Cm.
    `n_sessions_excluded_vendor` = manifest-excluded dates inside the window that would otherwise have been
    DECISION sessions (in the frame or the file).
(4) M1/M3 strike = the listed strike (strikes present in that session's quotes for that right) nearest the target.
    Exact ties (within 1e-9 dollars) go AWAY FROM SPOT, i.e. to the strike farther from S: for an ITM target
    (call S(1-m), put S(1+m)) that is the deeper-ITM strike, for an OTM target the further-OTM one. ATM (m = 0)
    has no "farther from spot" (both neighbours are equally far), so the tie goes to the ITM side, the direction
    A8 rounds the programme's own instrument: call -> the lower strike, put -> the higher one.
(5) M2 strike = A8 on the $1 grid, call K = floor(0.98 S), put K = ceil(1.02 S), exact integers stay (checked: the
    float products are exact for every 2-decimal price). There is NO nearest-listed fallback: a strike without a
    prevailing quote at entry or at 15:55 makes the leg missing. Cm_intraday is taken over the legs M2 itself
    uses (entry AND exit quote present), so both statistics describe the same legs.
(6) R7 fields for c_s (a cost per session, not a quote): min/p10/median/mean/p90/max of c_s; share_one_cent = share
    of sessions with c_s <= 0.1 points (both quotes one cent wide is the cost floor: RT = 0.01 dollar);
    share_locked_crossed = share of sessions with c_s <= 0. Leg level, same file: share_legs_locked_crossed = share
    of present legs whose entry or exit quote has ask <= bid. For M1 cells (a spread per session) share_one_cent =
    spread <= $0.01 and share_locked_crossed = ask <= bid; a locked/crossed spread therefore counts in both.
(7) M3 strikes follow (4), not A8. A leg is "present" when entry and exit quotes and both S exist; it is excluded
    (counted in n_excluded, left out of every statistic of its row) when its IV does not solve on [1e-4, 5.0] by
    brentq. delta = +1/-1 when mid - intrinsic <= 0.005 (+1e-9 float guard), no solve needed. `cheapest` = the
    lowest mean TC per (right, instant), ties to the smaller m.
(8) M5 reuses sellvol.body_strike / leg_strike / TRIALS / LEG_ROLES on per-session frames of the quote rows (strike,
    right, mod): A43's causal rule (a strike is a candidate only if it has a quote at or before the entry
    instant) and A43's tie rule (toward the smaller strike), NOT (4). A43's bar-close minute m is the instant m+1
    (571 -> 09:32, 810 -> 13:31); exit is the 16:00 instant. wing_width = the wider side (sellvol point 4).
    A session is skipped (n_skipped) when S, a strike, or any of the 8 leg quotes is missing, or max_loss <= 0;
    a non-positive QUOTED credit is kept and counted (n_credit_nonpositive). The day-block p is on net dollars
    per share, one session per block (NaN below 20 sessions, stats.MIN_BLOCKS).
(9) V2 is scored over the contract-minutes that have a prevailing quote at BOTH the bar start ts and the bar end
    ts + 1 minute (same denominator for both shares), a bar close within [bid - 0.01, ask + 0.01] (+1e-9);
    pass iff share_end >= share_start and share_end >= 0.25. The declared alignment is "end": A51a confirms the
    vendor stamps the END of its interval, which is `ts` as A51 defines it, so no shift is applied. A tie passes
    only if the 0.25 floor is met (A51 says "higher"; an exact tie cannot happen on real data).
(10) V1 pools every DECISION-window M1 leg with m >= 1.5 (ITM), calls and puts separately; the locked/crossed
    share of the pool is reported in `detail`.
(11) A manifest must name `vendor`, `schema`, `ts_semantics` (non-empty strings); `rows_on_change` must be a JSON
    boolean when present; `excluded_sessions` must be YYYY-MM-DD strings. Shard sha256/row counts are not checked
    (A51 fixes no key names for them).
"""
import argparse
import functools
import glob
import json
import math
import os
import re
from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy.optimize import brentq

from pipeline import options, sessions, stats
from pipeline.units import _gh, sellvol

NY = sessions.NY

# ---------------------------------------------------------------------------------------------
# Fixed specification (A51 / A51a)
# ---------------------------------------------------------------------------------------------

QUOTE_GLOB = "spy_0dte_quotes_1min_*.csv.gz"
TRADE_GLOB = "spy_0dte_1min_*.csv.gz"
MANIFEST_NAME = "quotes_manifest.json"
QUOTE_FILE_COLS = ["ts", "expiry", "strike", "right", "bid", "ask", "bid_size", "ask_size"]
QUOTE_USE_COLS = ["ts", "expiry", "strike", "right", "bid", "ask"]       # sizes are validated, not used
TRADE_FILE_COLS = ["ts", "expiry", "strike", "right", "open", "high", "low", "close", "volume"]
TS_FORMAT = "%Y-%m-%d %H:%M:%S"

SPX_PER_SPY = 10.0                  # SPX-equivalent index points per SPY dollar (sessions.load_ext scales SPY x10)
MAX_AGE_S = 5 * 60                  # A51: quote no older than 5 minutes
MAX_AGE_ON_CHANGE_S = 30 * 60       # A51a: ... 30 minutes when the vendor emits rows only on change
TIE_EPS = 1e-9                      # two strikes closer than this to equidistant from the target are tied
ONE_CENT = 0.01
EPS = 1e-9

DECISION_START = pd.Timestamp("2026-03-02")
DECISION_END = pd.Timestamp("2026-09-11")
DECISION_LABEL = "DECISION"
WINDOW_TEXT = "2026-03-02..2026-09-11"

INSTANT_LABELS = ["09:32", "10:01", "11:01", "13:01", "13:31", "15:01", "15:31", "15:55", "16:00"]   # ET
ENTRY_LABELS = ["10:01", "11:01", "13:01", "15:01", "15:31"]
EXIT_LABEL = "15:55"
M5_EXIT_LABEL = "16:00"
RIGHTS = ("C", "P")
M1_MONEYNESS = [-1.5, -1.0, -0.5, 0.0, 0.5, 1.0, 1.5, 2.0, 2.5]    # percent, negative = OTM, positive = ITM
DEPTH_MONEYNESS = [0.0, 0.5, 1.0, 1.5, 2.0, 2.5]
LEGS_PER_SESSION = len(ENTRY_LABELS) * len(RIGHTS)                  # 10 decision legs per session
MISSING_LIMIT = 0.20                # A51: more than 20 % of session x leg decision legs missing -> INCOMPLETE
BOOT_SEED, N_BOOT = 11, 2000        # A51: 2,000 session resamples, seed 11, 90 % interval
IV_BOUNDS = (1e-4, 5.0)
DELTA_ONE_TOL = 0.005               # delta = +-1 when mid - intrinsic <= this (A51 M3)
V1_MIN_ITM = 1.5
V1_RANGE = (-0.10, 0.25)
V2_MIN_SHARE = 0.25
V2_PAD = 0.01
N_MIN_TRACKC = 200                  # A51 M5: UNDERPOWERED below this
BAND_HIGH, BAND_LOW = 1.0, 0.5      # A51 "What each outcome means"


def _hhmm(label):
    h, m = label.split(":")
    return int(h) * 60 + int(m)


def label_of(mod):
    return f"{mod // 60:02d}:{mod % 60:02d}"


MOD = {label: _hhmm(label) for label in INSTANT_LABELS}             # ET minute of day of each instant

NS_PER_DAY = 86_400 * 10 ** 9
SEC_PER_DAY = 86_400
STRIKE_SCALE = 10 ** 7              # contract id packing: ((day * 2 + is_put) * 1e7) + strike in milli-dollars
KEY_SCALE = 10 ** 6                 # sort key = contract id * 1e6 + seconds since UTC midnight of the NY date

SURFACE_COLS = ["window", "instant", "right", "moneyness_pct", "n_sessions", "n", "missing_share", "min", "p10",
                "median", "mean", "p90", "max", "share_one_cent", "share_locked_crossed", "median_usd", "mean_usd"]
DECISION_COLS = ["window", "n_sessions", "n_sessions_window", "n_sessions_excluded_vendor", "n_leg_slots",
                 "n_legs_missing", "missing_share", "cm", "cm_lo", "cm_hi", "cm_intraday", "label", "band", "min",
                 "p10", "median", "mean", "p90", "max", "share_one_cent", "share_locked_crossed",
                 "share_legs_locked_crossed", "meaning", "vendor", "schema", "ts_semantics", "rows_on_change",
                 "quote_max_age_min", "spec"]
SESSIONS_COLS = (["date", "n_legs", "c_s", "c_intraday", "n_legs_locked_crossed"]
                 + [f"rt_{label.replace(':', '')}_{right}" for label in ENTRY_LABELS for right in RIGHTS])
DEPTH_COLS = ["right", "instant", "moneyness_pct", "n_sessions", "n", "n_missing", "n_excluded", "rt_mean",
              "rt_median", "delta_mean", "delta_median", "h_mean", "h_median", "tc_mean", "tc_median", "tc_lo",
              "tc_hi", "cheapest"]
# Must equal pipeline.units.costs_reread.COLS (the M4 module's own column list); test_costs checks it when that
# module is importable. A mismatch raises in `reread_table` rather than writing two different headers.
REREAD_COLS = ["family", "trial", "window", "source_file", "n", "cm", "net_at_cm", "p_day_at_cm", "fdr_pass_at_cm",
               "published_excess_over_control", "dsr_N", "dsr_at_cm", "cond_failed", "label",
               "cm_intraday", "net_at_cm_intraday", "p_day_at_cm_intraday",
               "published_net_1pt", "reread_net_at_1pt", "published_p_day", "reread_p_day_at_1pt",
               "published_dsr", "reread_dsr_at_1pt", "reproduces_published", "note"]
TRACKC_COLS = ["structure", "entry_instant", "exit_instant", "n_sessions_window", "n", "n_skipped",
               "n_credit_nonpositive", "mean_net_usd", "median_net_usd", "mean_pct_maxloss", "median_pct_maxloss",
               "worst_day_usd", "win_rate", "p_boot_day", "mean_gross_usd", "mean_cost_usd", "mean_credit_usd",
               "mean_max_loss_usd", "breakeven_leg_rt_usd", "label"]
VALIDATION_COLS = ["check", "what", "n", "value_1", "value_2", "threshold", "pass", "detail"]
OUTPUT_COLS = {"surface": SURFACE_COLS, "decision": DECISION_COLS, "sessions": SESSIONS_COLS, "depth": DEPTH_COLS,
               "reread": REREAD_COLS, "trackc": TRACKC_COLS, "validation": VALIDATION_COLS}
OUTPUT_NAMES = {"surface": "costs_surface.csv", "sessions": "costs_sessions.csv", "depth": "costs_depth.csv",
                "reread": "costs_reread.csv", "trackc": "costs_trackc.csv", "validation": "costs_validation.csv"}

MEANING = {
    ">=1.0": "Cm >= 1.0 pt (A51): the 1.0-point cost assumption was not conservative; every negative stands and "
             "was, if anything, optimistic.",
    "[0.5,1.0)": "0.5 <= Cm < 1.0 pt (A51): the assumption was conservative by up to half a point; the re-read "
                 "is reported, and FINDING.md's '1-2 index points' is corrected by a later amendment citing this "
                 "output.",
    "<0.5": "Cm < 0.5 pt (A51): the assumption was conservative by more than half a point; every future "
            "registration uses the measured cost instead of 1.0.",
}
MEANING_INCOMPLETE = ("INCOMPLETE (A51 coverage gate): more than 20% of the session x leg decision legs are missing; "
                      "no outcome band is assigned and M4 does not run.")

SPEC_NOTE = (
    "FIXED (pre-registration, A51 + A51a): quote file spy_0dte_quotes_1min_*.csv.gz (ts = UTC instant the "
    "consolidated BBO applies); underlying S = canonical-frame close of the bar ending at the instant / 10; every "
    "cost in SPX points = 10 x SPY dollars. Prevailing quote = latest row with ts <= t, same session and "
    "contract, no older than 30 minutes when the manifest declares rows_on_change, else 5 minutes (A51a); an "
    "empty bid or ask is no quote and the leg is missing, never filled; sessions the manifest excludes are "
    "excluded from every statistic. Decision window 2026-03-02..2026-09-11; other sessions in the file are M1 "
    "context by calendar quarter and never enter Cm. M2: 2% ITM with A8 rounding away from spot on the $1 grid "
    "(call floor(0.98 S), put ceil(1.02 S)) at 10:01/11:01/13:01/15:01/15:31, calls and puts, exit 15:55 on the "
    "same contract, RT = (ask - mid) at entry + (mid - bid) at exit, c_s = mean RT over the session's present "
    "legs, Cm = median over sessions of c_s with a 90% session bootstrap (2,000 resamples, seed 11); more than "
    "20% of session x leg decision legs missing -> INCOMPLETE and M4 does not run. Cm_intraday = median over "
    "sessions of the mean full spread of the same legs at entry. M1: nearest listed strike to the target, ties "
    "away from spot, at 09:32/10:01/11:01/13:01/13:31/15:01/15:31/15:55/16:00. M3: ATM and 0.5-2.5% ITM, BS delta "
    "at the mid-implied vol (r = 0, T = minutes to 16:00 / (365 x 24 x 60)), delta = +-1 when mid - intrinsic <= "
    "$0.005, h = (mid_x - mid_e) - delta (S_x - S_e), TC = (RT - h) / |delta|. M5: A43's S1/S2/S3 at 09:32/"
    "13:31/09:32 priced at mids, exit at the 16:00 instant, charged every leg's half-spread both ways; "
    "UNDERPOWERED below 200. V1-V3 failing publishes nothing. Information, never a verdict: zero trials.")


class CostsFailure(RuntimeError):
    """A51 refuses to publish: the manifest is missing/invalid or a validation check failed. The message lists
    the failing checks; `_gh.run` turns it into `<out>.error` and exit 2."""


@dataclass(frozen=True)
class Manifest:
    vendor: str
    schema: str
    ts_semantics: str
    rows_on_change: bool
    excluded: frozenset            # date_days of the sessions the vendor reports as degraded or missing (A51a)


# ---------------------------------------------------------------------------------------------
# Time, sessions, underlying
# ---------------------------------------------------------------------------------------------

def _days(ts):
    """Days since 1970-01-01 of a date-like (a naive midnight Timestamp or 'YYYY-MM-DD')."""
    return int(pd.Timestamp(ts).normalize().value // NS_PER_DAY)


def _day_ts(days):
    return pd.Timestamp(int(days) * NS_PER_DAY)


WINDOW_DAYS = (_days(DECISION_START), _days(DECISION_END))


def in_window(days):
    return WINDOW_DAYS[0] <= days <= WINDOW_DAYS[1]


def _quarter_label(days):
    t = _day_ts(days)
    return f"{t.year}Q{(t.month - 1) // 3 + 1}"


@functools.lru_cache(maxsize=None)
def instant_seconds(date_days, mod):
    """UTC epoch seconds of the ET wall-clock minute-of-day `mod` on the NY session `date_days`; DST comes from the
    America/New_York tz database per session date (10:01 ET is 15:01 UTC in January, 14:01 UTC in July)."""
    d = _day_ts(date_days)
    wall = pd.Timestamp(year=d.year, month=d.month, day=d.day, hour=mod // 60, minute=mod % 60)
    return int(wall.tz_localize(NY).tz_convert("UTC").value // 10 ** 9)


def et_to_utc(date, mod):
    """`instant_seconds` as a UTC Timestamp (`date` = 'YYYY-MM-DD' or a Timestamp)."""
    return pd.Timestamp(instant_seconds(_days(date), mod), unit="s", tz="UTC")


def instant_seconds_vec(days, mods):
    days = np.asarray(days)
    mods = np.broadcast_to(np.asarray(mods), days.shape)
    return np.array([instant_seconds(int(d), int(m)) for d, m in zip(days, mods)], dtype=np.int64)


def underlying_lookup(frame, mods):
    """S_of(date_days, instant_mod) in SPY dollars: the canonical frame's close of the bar that ENDS at the
    instant (bar mod = instant mod - 1), divided by 10 (the frame is in SPX points); NaN when the bar is absent.
    `mods` = every instant minute-of-day the caller will ask about."""
    need = sorted({int(m) - 1 for m in mods})
    f = frame.loc[frame["mod"].isin(need), ["date", "mod", "close"]]
    days = f["date"].to_numpy().astype("datetime64[D]").astype(np.int64)
    table = {(int(d), int(m)): float(c) for d, m, c in zip(days, f["mod"], f["close"])}

    def S_of(date_days, instant_mod):
        c = table.get((int(date_days), int(instant_mod) - 1))
        return np.nan if c is None else c / SPX_PER_SPY
    return S_of


def frame_days(frame):
    return set(int(d) for d in frame["date"].drop_duplicates().to_numpy().astype("datetime64[D]").astype(np.int64))


def session_groups(quote_days, f_days):
    """[(label, [date_days])]: DECISION = window sessions present in the frame or the quote file (a window session
    with no quote at all must count as missing, not vanish); every other quote-file session by calendar quarter
    (M1 context only)."""
    decision = sorted(d for d in set(quote_days) | set(f_days) if in_window(d))
    context = {}
    for d in sorted(set(quote_days)):
        if not in_window(d):
            context.setdefault(_quarter_label(d), []).append(d)
    return [(DECISION_LABEL, decision)] + [(k, context[k]) for k in sorted(context)]


# ---------------------------------------------------------------------------------------------
# Quote loading and the prevailing-quote book
# ---------------------------------------------------------------------------------------------

def _parse_stamps(ts, expiry):
    """(tsec, date_days, mod, same_day) per row. Each distinct string is parsed once (a minute repeats ~10^2 times
    in a shard). `date_days`/`mod` are the NY session date and ET minute of day of the UTC stamp."""
    codes, uniq = pd.factorize(pd.Series(ts, dtype=object))
    if (codes < 0).any():
        raise ValueError("empty ts value in the quote/trade file")
    uts = pd.DatetimeIndex(pd.to_datetime(uniq, format=TS_FORMAT, utc=True)).as_unit("ns")
    uny = uts.tz_convert(NY)
    u_sec = uts.asi8 // 10 ** 9
    u_day = uny.tz_localize(None).normalize().asi8 // NS_PER_DAY
    u_mod = np.asarray(uny.hour * 60 + uny.minute)
    ecodes, euniq = pd.factorize(pd.Series(expiry, dtype=object))
    if (ecodes < 0).any():
        raise ValueError("empty expiry value in the quote/trade file")
    e_day = pd.DatetimeIndex(pd.to_datetime(euniq, format="%Y-%m-%d")).as_unit("ns").asi8 // NS_PER_DAY
    date_days = u_day[codes]
    return u_sec[codes], date_days, u_mod[codes], e_day[ecodes] == date_days


def _rights(right):
    r = pd.Series(right, dtype=object).astype(str).str.strip().str.upper()
    if not r.isin(RIGHTS).all():
        raise ValueError(f"right must be C or P, got {sorted(set(r) - set(RIGHTS))[:5]}")
    return (r == "P").to_numpy(np.int8)


def prepare_quotes(raw, source="quotes"):
    """Raw quote rows (the file's columns) -> canonical frame: date_days (NY session date), is_put, strike, tsec (UTC
    epoch seconds of ts), mod (ET minute of day), bid, ask. Empty/NaN prices stay NaN: such a row is the vendor's
    empty-book record and must remain the prevailing row (A51a), never be dropped. Rows whose expiry is not the NY
    date of their ts are dropped with a [NOTE]."""
    missing = [c for c in QUOTE_USE_COLS if c not in raw.columns]
    if missing:
        raise ValueError(f"{source} missing required column(s): {missing}")
    tsec, date_days, mod, same = _parse_stamps(raw["ts"].to_numpy(), raw["expiry"].to_numpy())
    out = pd.DataFrame({"date_days": date_days, "is_put": _rights(raw["right"].to_numpy()),
                        "strike": pd.to_numeric(raw["strike"], errors="raise").to_numpy(float),
                        "tsec": tsec, "mod": mod.astype(np.int16),
                        "bid": pd.to_numeric(raw["bid"], errors="raise").to_numpy(float),
                        "ask": pd.to_numeric(raw["ask"], errors="raise").to_numpy(float)})
    if not np.isfinite(out["strike"]).all():
        raise ValueError(f"{source}: non-finite strike")
    if not same.all():
        print(f"[NOTE] A51 costs: {source}: dropped {int((~same).sum())} row(s) whose expiry is not the NY date of ts")
        out = out[same]
    return out.reset_index(drop=True)


def read_quote_shards(paths):
    parts = []
    for path in sorted(paths):
        head = pd.read_csv(path, nrows=0).columns
        missing = [c for c in QUOTE_FILE_COLS if c not in head]
        if missing:
            raise ValueError(f"{os.path.basename(path)} missing required column(s): {missing}")
        raw = pd.read_csv(path, usecols=QUOTE_USE_COLS, dtype={"ts": str, "expiry": str, "right": str})
        parts.append(prepare_quotes(raw, source=os.path.basename(path)))
    q = pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()
    if q.empty:
        raise ValueError("the quote shards hold no usable rows")
    return q


def contract_ids(date_days, is_put, strike):
    return ((np.asarray(date_days, np.int64) * 2 + np.asarray(is_put, np.int64)) * STRIKE_SCALE
            + np.rint(np.asarray(strike, float) * 1000.0).astype(np.int64))


def max_age_seconds(rows_on_change):
    """A51a: the staleness limit is a function of the manifest flag."""
    return MAX_AGE_ON_CHANGE_S if rows_on_change else MAX_AGE_S


class QuoteBook:
    """Quote rows sorted by (contract, ts) for O(log n) prevailing-quote lookups. A contract is (NY session date,
    right, strike), so "same session" is part of the key."""

    def __init__(self, q, max_age_s=MAX_AGE_S):
        self.max_age_s = int(max_age_s)
        date_days = q["date_days"].to_numpy(np.int64)
        cid = contract_ids(date_days, q["is_put"].to_numpy(), q["strike"].to_numpy())
        tsec = q["tsec"].to_numpy(np.int64)
        key = cid * KEY_SCALE + (tsec - date_days * SEC_PER_DAY)
        order = np.argsort(key, kind="stable")
        key = key[order]
        keep = np.ones(len(key), bool)
        keep[:-1] = key[:-1] != key[1:]                     # duplicate (contract, ts): the last row in file order wins
        sel = order[keep]
        self.n_duplicates = int(len(key) - keep.sum())
        self.key, self.cid, self.tsec = key[keep], cid[sel], tsec[sel]
        self.bid, self.ask = q["bid"].to_numpy(float)[sel], q["ask"].to_numpy(float)[sel]

    def lookup(self, date_days, is_put, strike, t):
        """The quote prevailing at instant `t` (UTC epoch seconds) for each query: the latest row with ts <= t in the
        same session and contract, no older than `max_age_s` (inclusive). (bid, ask) float arrays; NaN where the leg
        is missing - no row, too old, or the prevailing row has an empty bid or ask (never filled from an older
        row)."""
        strike = np.asarray(strike, float)
        n = len(strike)
        bid, ask = np.full(n, np.nan), np.full(n, np.nan)
        if n == 0 or len(self.key) == 0:
            return bid, ask
        date_days = np.asarray(date_days, np.int64)
        t = np.asarray(t, np.int64)
        good = np.isfinite(strike)
        cid = contract_ids(date_days, is_put, np.where(good, strike, 0.0))
        pos = np.searchsorted(self.key, cid * KEY_SCALE + (t - date_days * SEC_PER_DAY), side="right") - 1
        p = np.clip(pos, 0, len(self.key) - 1)
        ok = good & (pos >= 0) & (self.cid[p] == cid) & (t - self.tsec[p] <= self.max_age_s)
        bid[ok], ask[ok] = self.bid[p][ok], self.ask[p][ok]
        empty = ~(np.isfinite(bid) & np.isfinite(ask))
        bid[empty], ask[empty] = np.nan, np.nan
        return bid, ask


def listed_strikes(q):
    """{(date_days, is_put): sorted unique strikes present in that session's quotes for that right}."""
    out = {}
    for (d, p), g in q.groupby(["date_days", "is_put"])["strike"]:
        out[(int(d), int(p))] = np.unique(g.to_numpy(float))
    return out


def attach_quotes(df, book, suffix, mods):
    """Add bid_<suffix>/ask_<suffix>: the quote prevailing at each row's session at ET minute `mods` on column K."""
    t = instant_seconds_vec(df["date_days"].to_numpy(), mods)
    bid, ask = book.lookup(df["date_days"].to_numpy(), (df["right"] == "P").to_numpy(), df["K"].to_numpy(float), t)
    df[f"bid_{suffix}"], df[f"ask_{suffix}"] = bid, ask
    return df


# ---------------------------------------------------------------------------------------------
# Strikes
# ---------------------------------------------------------------------------------------------

def tie_away(right, m):
    """+1 = take the HIGHER strike on an exact tie, -1 = the LOWER: the one away from spot (module docstring 4).
    Calls' ITM side is down, puts' is up; an OTM target (m < 0) flips it; ATM (m = 0) takes the ITM side."""
    itm_side = -1 if right == "C" else 1
    return itm_side if m >= 0 else -itm_side


def nearest_away(ks, targets, away):
    """The listed strike (sorted unique array `ks`) nearest each target; an exact tie (within TIE_EPS dollars) goes
    to the higher strike where `away` > 0, else to the lower."""
    ks = np.asarray(ks, float)
    t = np.asarray(targets, float)
    away = np.broadcast_to(np.asarray(away), t.shape)
    i = np.searchsorted(ks, t)
    lo = ks[np.clip(i - 1, 0, len(ks) - 1)]
    hi = ks[np.clip(i, 0, len(ks) - 1)]
    d_lo, d_hi = np.abs(t - lo), np.abs(hi - t)
    tie = np.abs(d_hi - d_lo) <= TIE_EPS
    return np.where(np.where(tie, away > 0, d_hi < d_lo), hi, lo)


def a8_strike(S, right):
    """A8 on the $1 grid, rounded AWAY from spot: call K = floor(0.98 S), put K = ceil(1.02 S); an exact integer
    product stays (S in SPY dollars). NaN if S is."""
    if not np.isfinite(S):
        return np.nan
    return float(math.floor(0.98 * S)) if right == "C" else float(math.ceil(1.02 * S))


def strike_table(days, labels, rights, moneyness, S_of, listed):
    """One row per (session, instant, right, m): S at the instant and the listed strike nearest the target
    (call S(1 - m/100), put S(1 + m/100); m > 0 ITM), NaN when S or the session's strikes are missing."""
    recs = []
    ms = np.asarray(moneyness, float)
    for d in days:
        for label in labels:
            mod = MOD[label]
            S = S_of(d, mod)
            for right in rights:
                ks = listed.get((d, int(right == "P")))
                if ks is None or len(ks) == 0 or not np.isfinite(S):
                    K = np.full(len(ms), np.nan)
                else:
                    target = S * (1.0 - ms / 100.0) if right == "C" else S * (1.0 + ms / 100.0)
                    K = nearest_away(ks, target, np.array([tie_away(right, m) for m in ms]))
                recs.extend((d, label, mod, right, float(m), S, float(k)) for m, k in zip(ms, K))
    return pd.DataFrame(recs, columns=["date_days", "instant", "mod", "right", "m", "S", "K"]).astype(
        {"date_days": np.int64, "mod": np.int64, "m": float, "S": float, "K": float})


# ---------------------------------------------------------------------------------------------
# Statistics helpers
# ---------------------------------------------------------------------------------------------

def r7(values):
    """The R7 distribution fields (min, p10, median, mean, p90, max) of the finite `values`."""
    x = np.asarray(values, float)
    x = x[np.isfinite(x)]
    if not len(x):
        return {k: np.nan for k in ("min", "p10", "median", "mean", "p90", "max")}
    return {"min": float(x.min()), "p10": float(np.percentile(x, 10)), "median": float(np.median(x)),
            "mean": float(x.mean()), "p90": float(np.percentile(x, 90)), "max": float(x.max())}


def session_bootstrap(values, stat, seed=BOOT_SEED, n_boot=N_BOOT):
    """90 % session-bootstrap interval of `stat` (np.median / np.mean): `n_boot` resamples of the sessions with
    replacement from a FRESH np.random.default_rng(seed) (`rng.integers(0, n, (n_boot, n))`), 5th and 95th
    percentile of the resampled statistic."""
    v = np.asarray(values, float)
    v = v[np.isfinite(v)]
    if not len(v):
        return np.nan, np.nan
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(v), size=(n_boot, len(v)))
    lo, hi = np.percentile(stat(v[idx], axis=1), [5, 95])
    return float(lo), float(hi)


def band_of(cm):
    """A51's outcome bands for Cm in index points."""
    if not np.isfinite(cm):
        return "n/a"
    if cm >= BAND_HIGH:
        return ">=1.0"
    if cm >= BAND_LOW:
        return "[0.5,1.0)"
    return "<0.5"


# ---------------------------------------------------------------------------------------------
# M1 -- the spread surface
# ---------------------------------------------------------------------------------------------

def surface_legs(book, listed, S_of, groups, labels=INSTANT_LABELS, moneyness=M1_MONEYNESS):
    """Leg table of M1: one row per (window group, session, instant, right, m) with the nearest listed strike's
    prevailing quote (bid/ask NaN = missing)."""
    parts = []
    for window, days in groups:
        if not days:
            continue
        st = strike_table(days, labels, RIGHTS, moneyness, S_of, listed)
        st.insert(0, "window", window)
        parts.append(st)
    if not parts:
        return pd.DataFrame({"window": pd.Series(dtype=object), "date_days": pd.Series(dtype=np.int64),
                             "instant": pd.Series(dtype=object), "mod": pd.Series(dtype=np.int64),
                             "right": pd.Series(dtype=object), "m": pd.Series(dtype=float),
                             "S": pd.Series(dtype=float), "K": pd.Series(dtype=float),
                             "bid": pd.Series(dtype=float), "ask": pd.Series(dtype=float)})
    legs = pd.concat(parts, ignore_index=True)
    t = instant_seconds_vec(legs["date_days"].to_numpy(), legs["mod"].to_numpy())
    legs["bid"], legs["ask"] = book.lookup(legs["date_days"].to_numpy(), (legs["right"] == "P").to_numpy(),
                                           legs["K"].to_numpy(float), t)
    return legs


def surface_table(legs):
    """M1: per (window, instant, right, moneyness) over sessions - n, missing share and the R7 fields in SPX points
    (+ the median/mean in dollars)."""
    rows = []
    for (window, instant, right, m), g in legs.groupby(["window", "instant", "right", "m"], sort=False):
        ok = g[np.isfinite(g["bid"]) & np.isfinite(g["ask"])]
        usd = (ok["ask"] - ok["bid"]).to_numpy(float)
        n = len(ok)
        row = {"window": window, "instant": instant, "right": right, "moneyness_pct": float(m),
               "n_sessions": len(g), "n": n, "missing_share": 1.0 - n / len(g)}
        row.update(r7(usd * SPX_PER_SPY))
        row.update(share_one_cent=float((usd <= ONE_CENT + EPS).mean()) if n else np.nan,
                   share_locked_crossed=float((ok["ask"] <= ok["bid"]).mean()) if n else np.nan,
                   median_usd=float(np.median(usd)) if n else np.nan, mean_usd=float(usd.mean()) if n else np.nan)
        rows.append(row)
    out = pd.DataFrame(rows, columns=SURFACE_COLS)
    out["_w"] = (out["window"] != DECISION_LABEL).astype(int)
    out["_i"] = out["instant"].map({l: i for i, l in enumerate(INSTANT_LABELS)})
    out["_r"] = out["right"].map({r: i for i, r in enumerate(RIGHTS)})
    out = out.sort_values(["_w", "window", "_i", "_r", "moneyness_pct"]).drop(columns=["_w", "_i", "_r"])
    return out.reset_index(drop=True)


# ---------------------------------------------------------------------------------------------
# M2 -- the decision statistic Cm
# ---------------------------------------------------------------------------------------------

def decision_legs(book, S_of, days):
    """M2 leg table: per DECISION session, the five entry instants x calls/puts (10 legs): A8 strike from S at the
    entry instant, entry quote at the instant, exit quote at 15:55 on the SAME contract. RT = (ask - mid) at entry +
    (mid - bid) at exit, mid = (bid + ask) / 2, in SPX points."""
    recs = []
    for d in days:
        for label in ENTRY_LABELS:
            S = S_of(d, MOD[label])
            for right in RIGHTS:
                recs.append((d, label, MOD[label], right, S, a8_strike(S, right)))
    df = pd.DataFrame(recs, columns=["date_days", "instant", "mod", "right", "S", "K"]).astype(
        {"date_days": np.int64, "mod": np.int64, "S": float, "K": float})
    df = attach_quotes(df, book, "e", df["mod"].to_numpy())
    df = attach_quotes(df, book, "x", MOD[EXIT_LABEL])
    df["present"] = (np.isfinite(df["bid_e"]) & np.isfinite(df["ask_e"])
                     & np.isfinite(df["bid_x"]) & np.isfinite(df["ask_x"]))
    mid_e, mid_x = (df["bid_e"] + df["ask_e"]) / 2, (df["bid_x"] + df["ask_x"]) / 2
    df["rt"] = SPX_PER_SPY * ((df["ask_e"] - mid_e) + (mid_x - df["bid_x"]))
    df["spread_e"] = SPX_PER_SPY * (df["ask_e"] - df["bid_e"])
    df["crossed"] = (df["ask_e"] <= df["bid_e"]) | (df["ask_x"] <= df["bid_x"])
    return df


def session_table(legs, days):
    """M2 per-session table, WIDE format: one row per DECISION session (also those with no present leg, n_legs = 0,
    c_s blank), c_s = mean RT over the session's present legs, c_intraday = mean full entry spread of the same
    legs, one rt_<HHMM>_<C|P> column per decision leg (blank = missing)."""
    by_day = {d: g for d, g in legs.groupby("date_days")} if len(legs) else {}
    rows = []
    for d in days:
        g = by_day.get(d)
        row = {"date": _day_ts(d).strftime("%Y-%m-%d"), "n_legs": 0, "c_s": np.nan, "c_intraday": np.nan,
               "n_legs_locked_crossed": 0}
        if g is not None:
            p = g[g["present"]]
            row.update(n_legs=len(p), n_legs_locked_crossed=int(p["crossed"].sum()))
            if len(p):
                row.update(c_s=float(p["rt"].mean()), c_intraday=float(p["spread_e"].mean()))
            for _, leg in p.iterrows():
                row[f"rt_{leg['instant'].replace(':', '')}_{leg['right']}"] = float(leg["rt"])
        rows.append(row)
    return pd.DataFrame(rows, columns=SESSIONS_COLS)


def decision_row(legs, sess, n_window, n_excluded, man):
    """The one-row summary (costs_decision.csv): Cm = median over sessions of c_s, its 90 % session bootstrap,
    Cm_intraday, the coverage gate (> 20 % of session x leg slots missing -> INCOMPLETE), R7 fields, A51's outcome
    band and the manifest's vendor/schema/ts_semantics/rows_on_change."""
    slots = LEGS_PER_SESSION * n_window
    present = int(legs["present"].sum()) if len(legs) else 0
    missing = slots - present
    missing_share = missing / slots if slots else np.nan
    incomplete = (not slots) or missing_share > MISSING_LIMIT
    c = sess["c_s"].dropna().to_numpy(float)
    cm = float(np.median(c)) if len(c) else np.nan
    lo, hi = session_bootstrap(c, np.median)
    intraday = sess["c_intraday"].dropna().to_numpy(float)
    crossed_legs = (float(legs.loc[legs["present"], "crossed"].mean()) if present else np.nan)
    label = "INCOMPLETE" if incomplete else "COMPLETE"
    band = band_of(cm)
    row = {"window": WINDOW_TEXT, "n_sessions": len(c), "n_sessions_window": n_window,
           "n_sessions_excluded_vendor": n_excluded, "n_leg_slots": slots, "n_legs_missing": missing,
           "missing_share": missing_share, "cm": cm, "cm_lo": lo, "cm_hi": hi,
           "cm_intraday": float(np.median(intraday)) if len(intraday) else np.nan,
           "label": label, "band": band}
    row.update(r7(c))
    row.update(share_one_cent=float((c <= ONE_CENT * SPX_PER_SPY + EPS).mean()) if len(c) else np.nan,
               share_locked_crossed=float((c <= 0).mean()) if len(c) else np.nan,
               share_legs_locked_crossed=crossed_legs,
               meaning=MEANING_INCOMPLETE if incomplete else MEANING[band],
               vendor=man.vendor, schema=man.schema, ts_semantics=man.ts_semantics,
               rows_on_change=man.rows_on_change, quote_max_age_min=max_age_seconds(man.rows_on_change) / 60.0,
               spec=SPEC_NOTE)
    return row


# ---------------------------------------------------------------------------------------------
# M3 -- which depth is cheapest
# ---------------------------------------------------------------------------------------------

def entry_delta(mid, S, K, mins_to_close, right):
    """Black-Scholes entry delta (r = 0, T = minutes to 16:00 / (365 x 24 x 60), pipeline.options' clock) at the
    mid-implied volatility (brentq on [1e-4, 5.0]). +-1 when mid - intrinsic <= $0.005 (no solve). NaN when the
    volatility does not solve (the caller excludes and counts the leg)."""
    kind = "c" if right == "C" else "p"
    intrinsic = max(S - K, 0.0) if kind == "c" else max(K - S, 0.0)
    if mid - intrinsic <= DELTA_ONE_TOL + EPS:
        return 1.0 if kind == "c" else -1.0

    def gap(sigma):
        return options.price(S, K, mins_to_close, sigma, kind) - mid

    lo, hi = IV_BOUNDS
    f_lo, f_hi = gap(lo), gap(hi)
    if not (np.isfinite(f_lo) and np.isfinite(f_hi)) or f_lo * f_hi > 0:
        return np.nan
    try:
        sigma = brentq(gap, lo, hi)
    except (ValueError, RuntimeError):
        return np.nan
    bs = options.bs_call if kind == "c" else options.bs_put
    return float(bs(S, K, mins_to_close / options.MINUTES_PER_YEAR, sigma)[1])


def depth_legs(book, S_of, days, listed):
    """M3 leg table: ATM and 0.5-2.5 % ITM, the five entry instants, exit 15:55 on the same contract. Per leg: RT,
    entry delta (see `entry_delta`), the static-hedged option P&L h = (mid_x - mid_e) - delta (S_x - S_e) and
    TC = (RT - h) / |delta|, all in SPX points."""
    df = strike_table(days, ENTRY_LABELS, RIGHTS, DEPTH_MONEYNESS, S_of, listed)
    df = attach_quotes(df, book, "e", df["mod"].to_numpy())
    df = attach_quotes(df, book, "x", MOD[EXIT_LABEL])
    df["S_x"] = np.array([S_of(d, MOD[EXIT_LABEL]) for d in df["date_days"]], dtype=float)
    df["present"] = (np.isfinite(df["bid_e"]) & np.isfinite(df["ask_e"]) & np.isfinite(df["bid_x"])
                     & np.isfinite(df["ask_x"]) & np.isfinite(df["S"]) & np.isfinite(df["S_x"]))
    mid_e, mid_x = (df["bid_e"] + df["ask_e"]) / 2, (df["bid_x"] + df["ask_x"]) / 2
    delta = np.full(len(df), np.nan)
    for i in np.flatnonzero(df["present"].to_numpy()):
        r = df.iloc[i]
        delta[i] = entry_delta(float(mid_e.iloc[i]), float(r["S"]), float(r["K"]), options.CLOSE_MOD - int(r["mod"]),
                               r["right"])
    df["delta"] = delta
    df["solved"] = df["present"] & np.isfinite(df["delta"]) & (np.abs(df["delta"]) > 0)
    df["rt"] = SPX_PER_SPY * ((df["ask_e"] - mid_e) + (mid_x - df["bid_x"]))
    df["h"] = SPX_PER_SPY * ((mid_x - mid_e) - df["delta"] * (df["S_x"] - df["S"]))
    df["tc"] = (df["rt"] - df["h"]) / df["delta"].abs()
    return df


def depth_table(legs):
    """M3: per (right, instant, m) - n, n_missing, n_excluded (IV did not solve), mean and median of RT, delta, h
    and TC over the n solved legs, the 90 % session bootstrap of mean TC, and `cheapest` (lowest mean TC per
    right and instant, reported only)."""
    rows = []
    for (right, instant, m), g in legs.groupby(["right", "instant", "m"], sort=False):
        ok = g[g["solved"]]
        row = {"right": right, "instant": instant, "moneyness_pct": float(m), "n_sessions": len(g), "n": len(ok),
               "n_missing": int((~g["present"]).sum()), "n_excluded": int((g["present"] & ~g["solved"]).sum())}
        for name, col in (("rt", "rt"), ("delta", "delta"), ("h", "h"), ("tc", "tc")):
            row[f"{name}_mean"] = float(ok[col].mean()) if len(ok) else np.nan
            row[f"{name}_median"] = float(ok[col].median()) if len(ok) else np.nan
        row["tc_lo"], row["tc_hi"] = session_bootstrap(ok["tc"].to_numpy(float), np.mean)
        rows.append(row)
    out = pd.DataFrame(rows, columns=[c for c in DEPTH_COLS if c != "cheapest"])
    out["_i"] = out["instant"].map({l: i for i, l in enumerate(INSTANT_LABELS)})
    out["_r"] = out["right"].map({r: i for i, r in enumerate(RIGHTS)})
    out = out.sort_values(["_r", "_i", "moneyness_pct"]).reset_index(drop=True)
    out["cheapest"] = False
    for _, idx in out.groupby(["right", "instant"]).groups.items():
        tc = out.loc[idx, "tc_mean"]
        if tc.notna().any():
            out.loc[tc.idxmin(), "cheapest"] = True
    return out.drop(columns=["_i", "_r"])[DEPTH_COLS]


# ---------------------------------------------------------------------------------------------
# M5 -- A43 re-priced at real quotes
# ---------------------------------------------------------------------------------------------

def day_frames(q, days):
    """{date_days: DataFrame(strike, right, mod)} of the quote rows of `days` - the shape sellvol's strike functions
    read (`mod` = ET minute of the quote's ts)."""
    out = {}
    sel = q.loc[q["date_days"].isin(list(days)), ["date_days", "strike", "is_put", "mod"]]
    for d, g in sel.groupby("date_days"):
        out[int(d)] = pd.DataFrame({"strike": g["strike"].to_numpy(float),
                                    "right": np.where(g["is_put"].to_numpy() == 1, "P", "C"),
                                    "mod": g["mod"].to_numpy(int)})
    return out


def structure_strikes(options_day, S, entry_mod, wing_pct, short_pct):
    """A43's four strikes by sellvol's own functions (causal availability: only strikes with a quote at or before
    the entry instant; ties toward the smaller strike): {role: (right, K)} or None if any cannot be resolved."""
    if short_pct is None:
        k_body = sellvol.body_strike(options_day, S, entry_mod)
        if k_body is None:
            return None
        strikes = {"short_call": ("C", k_body), "short_put": ("P", k_body)}
    else:
        kc = sellvol.leg_strike(options_day, "C", S * (1 + short_pct), entry_mod)
        kp = sellvol.leg_strike(options_day, "P", S * (1 - short_pct), entry_mod)
        if kc is None or kp is None:
            return None
        strikes = {"short_call": ("C", kc), "short_put": ("P", kp)}
    klc = sellvol.leg_strike(options_day, "C", S * (1 + wing_pct), entry_mod)
    klp = sellvol.leg_strike(options_day, "P", S * (1 - wing_pct), entry_mod)
    if klc is None or klp is None:
        return None
    strikes["long_call"], strikes["long_put"] = ("C", klc), ("P", klp)
    return strikes


def price_structure(quotes, strikes):
    """Arithmetic of one 4-leg day. `quotes` = {role: (bid_e, ask_e, bid_x, ask_x)} per share in dollars. gross =
    sum over legs of sign x (mid_x - mid_e), sign -1 for the two short legs (a short earns entry - exit) and +1 for
    the longs; cost = every leg's half-spread at entry plus at exit; net = gross - cost (= selling at the bid and
    buying at the ask both ways). credit = bid(short call) + bid(short put) - ask(long call) - ask(long put);
    max_loss = the wider wing - credit."""
    gross = cost = 0.0
    for role in sellvol.LEG_ROLES:
        bid_e, ask_e, bid_x, ask_x = quotes[role]
        sign = -1.0 if role.startswith("short") else 1.0
        gross += sign * ((bid_x + ask_x) / 2 - (bid_e + ask_e) / 2)
        cost += (ask_e - bid_e) / 2 + (ask_x - bid_x) / 2
    credit = quotes["short_call"][0] + quotes["short_put"][0] - quotes["long_call"][1] - quotes["long_put"][1]
    wing = max(strikes["long_call"][1] - strikes["short_call"][1], strikes["short_put"][1] - strikes["long_put"][1])
    return {"credit": credit, "wing_width": wing, "max_loss": wing - credit, "gross": gross, "cost": cost,
            "net": gross - cost}


def trackc_sessions(book, S_of, days, frames, trials=None):
    """One row per (structure, DECISION session) priced at quotes, or skipped (status 'skipped'): A43's S1/S2/S3
    (`sellvol.TRIALS`) at the instant their bar closes (mod + 1) and the 16:00 instant."""
    rows = []
    for name, a43_mod, wing_pct, short_pct in (trials or sellvol.TRIALS):
        entry_mod, exit_mod = a43_mod + 1, MOD[M5_EXIT_LABEL]
        for d in days:
            row = {"structure": name, "date_days": d, "status": "skipped"}
            rows.append(row)
            S = S_of(d, entry_mod)
            options_day = frames.get(d)
            if options_day is None or not np.isfinite(S):
                continue
            strikes = structure_strikes(options_day, S, entry_mod, wing_pct, short_pct)
            if strikes is None:
                continue
            roles = list(sellvol.LEG_ROLES)
            is_put = np.array([strikes[r][0] == "P" for r in roles])
            K = np.array([strikes[r][1] for r in roles], float)
            dd = np.full(len(roles), d, np.int64)
            be, ae = book.lookup(dd, is_put, K, np.full(len(roles), instant_seconds(d, entry_mod), np.int64))
            bx, ax = book.lookup(dd, is_put, K, np.full(len(roles), instant_seconds(d, exit_mod), np.int64))
            if not (np.isfinite(be).all() and np.isfinite(ae).all() and np.isfinite(bx).all()
                    and np.isfinite(ax).all()):
                continue
            res = price_structure({r: (be[i], ae[i], bx[i], ax[i]) for i, r in enumerate(roles)}, strikes)
            if res["max_loss"] <= 0:
                continue
            row.update(res, status="ok")
    return pd.DataFrame(rows)


def trackc_table(rows, n_window, trials=None):
    """M5: per structure - n, n_skipped, mean/median net per share in dollars and in % of max loss, worst day,
    win rate, one-sided day-block p (`stats.one_sided_p`, sessions as blocks), breakeven per-leg round-trip cost at
    mids = mean gross / 4, UNDERPOWERED below 200 sessions."""
    out = []
    for name, a43_mod, _wing, _short in (trials or sellvol.TRIALS):
        g = rows[(rows["structure"] == name) & (rows["status"] == "ok")] if len(rows) else rows
        n = len(g)
        row = {"structure": name, "entry_instant": label_of(a43_mod + 1), "exit_instant": M5_EXIT_LABEL,
               "n_sessions_window": n_window, "n": n, "n_skipped": n_window - n}
        if n:
            net = g["net"].to_numpy(float)
            pct = net / g["max_loss"].to_numpy(float) * 100.0
            blocks = stats.day_blocks([_day_ts(d) for d in g["date_days"]])
            row.update(n_credit_nonpositive=int((g["credit"] <= 0).sum()), mean_net_usd=float(net.mean()),
                       median_net_usd=float(np.median(net)), mean_pct_maxloss=float(pct.mean()),
                       median_pct_maxloss=float(np.median(pct)), worst_day_usd=float(net.min()),
                       win_rate=float((net > 0).mean()), p_boot_day=stats.one_sided_p(net, blocks),
                       mean_gross_usd=float(g["gross"].mean()), mean_cost_usd=float(g["cost"].mean()),
                       mean_credit_usd=float(g["credit"].mean()), mean_max_loss_usd=float(g["max_loss"].mean()),
                       breakeven_leg_rt_usd=float(g["gross"].mean() / len(sellvol.LEG_ROLES)))
        row["label"] = "UNDERPOWERED" if n < N_MIN_TRACKC else "MEASURED"
        out.append(row)
    return pd.DataFrame(out, columns=TRACKC_COLS)


# ---------------------------------------------------------------------------------------------
# M4 -- the re-read (another module), gated on the coverage label
# ---------------------------------------------------------------------------------------------

def run_reread(cm, cm_intraday):
    from pipeline.units import costs_reread
    return costs_reread.reread(cm, cm_intraday)


def reread_table(decision):
    """M4 (A51): run the re-read at Cm and Cm_intraday - only when Cm is not INCOMPLETE (A51 coverage gate);
    header-only otherwise. The returned frame must carry exactly REREAD_COLS."""
    if decision["label"] == "INCOMPLETE":
        return pd.DataFrame(columns=REREAD_COLS)
    df = run_reread(float(decision["cm"]), float(decision["cm_intraday"]))
    if list(df.columns) != REREAD_COLS:
        raise ValueError(f"costs_reread.reread returned columns {list(df.columns)}, expected REREAD_COLS "
                         f"{REREAD_COLS}")
    return df


# ---------------------------------------------------------------------------------------------
# Validation V1-V3
# ---------------------------------------------------------------------------------------------

def vrow(check, what, n, value_1, value_2, threshold, passed, detail):
    return {"check": check, "what": what, "n": n, "value_1": value_1, "value_2": value_2, "threshold": threshold,
            "pass": bool(passed), "detail": detail}


def check_v1(legs):
    """V1, scale and mapping: over every DECISION-window M1 leg that is at least 1.5 % ITM (all instants, all
    sessions), the median of (mid - intrinsic) must lie in [-$0.10, +$0.25] for calls and for puts separately (a
    price-scale error or a swapped right lands far outside). The locked-or-crossed share is reported."""
    sel = legs[(legs["window"] == DECISION_LABEL) & (legs["m"] >= V1_MIN_ITM)
               & np.isfinite(legs["bid"]) & np.isfinite(legs["ask"])]
    mid = (sel["bid"] + sel["ask"]) / 2
    intrinsic = np.where(sel["right"] == "C", np.maximum(sel["S"] - sel["K"], 0.0),
                         np.maximum(sel["K"] - sel["S"], 0.0))
    excess = pd.Series(mid.to_numpy() - intrinsic, index=sel.index)
    med = {r: (float(excess[sel["right"] == r].median()) if (sel["right"] == r).any() else np.nan) for r in RIGHTS}
    lo, hi = V1_RANGE
    passed = all(np.isfinite(v) and lo <= v <= hi for v in med.values())
    crossed = float((sel["ask"] <= sel["bid"]).mean()) if len(sel) else np.nan
    return vrow("V1", "median(mid - intrinsic), >= 1.5% ITM, calls | puts, dollars", len(sel), med["C"], med["P"],
                f"both in [{lo:.2f}, {hi:+.2f}]", passed,
                f"locked_crossed_share={crossed:.6f}; n_calls={int((sel['right'] == 'C').sum())}; "
                f"n_puts={int((sel['right'] == 'P').sum())}")


def check_v2(book, bars):
    """V2, timestamp alignment: for the trade bars (ts = bar START) that have a prevailing quote at BOTH the bar's
    start and its end (ts + 60 s), the share of bar closes within [bid - 0.01, ask + 0.01] scored against the quote
    at the end (the declared alignment) and against the quote at the start. Pass iff share_end >= share_start and
    share_end >= 25 %."""
    what = "share of bar closes in [bid-0.01, ask+0.01]: quote at bar end | quote at bar start"
    thr = f"share_end >= share_start and share_end >= {V2_MIN_SHARE:.2f}"
    if not len(bars):
        return vrow("V2", what, 0, np.nan, np.nan, thr, False,
                    "no trade bars in the decision-window sessions of the quote file")
    d, p, k = bars["date_days"].to_numpy(), bars["is_put"].to_numpy(), bars["strike"].to_numpy(float)
    ts, close = bars["tsec"].to_numpy(np.int64), bars["close"].to_numpy(float)
    bid_e, ask_e = book.lookup(d, p, k, ts + 60)
    bid_s, ask_s = book.lookup(d, p, k, ts)
    both = np.isfinite(bid_e) & np.isfinite(ask_e) & np.isfinite(bid_s) & np.isfinite(ask_s)
    n = int(both.sum())
    if not n:
        return vrow("V2", what, 0, np.nan, np.nan, thr, False,
                    f"{len(bars)} trade bars, none with a prevailing quote at both the bar start and the bar end")
    in_end = (close >= bid_e - V2_PAD - EPS) & (close <= ask_e + V2_PAD + EPS)
    in_start = (close >= bid_s - V2_PAD - EPS) & (close <= ask_s + V2_PAD + EPS)
    share_end, share_start = float(in_end[both].mean()), float(in_start[both].mean())
    passed = share_end >= share_start and share_end >= V2_MIN_SHARE
    return vrow("V2", what, n, share_end, share_start, thr, passed, f"n_trade_bars={len(bars)}; n_scored={n}")


def check_v3(decision):
    """V3, coverage: as in M2 - pass iff Cm is not INCOMPLETE (more than 20 % of session x leg decision legs
    missing)."""
    return vrow("V3", "missing share of session x leg decision legs", decision["n_leg_slots"], decision["missing_share"],
                np.nan, f"<= {MISSING_LIMIT:.2f}", decision["label"] != "INCOMPLETE",
                f"n_legs_missing={decision['n_legs_missing']}; label={decision['label']}")


# ---------------------------------------------------------------------------------------------
# Trade shards (V2) and the manifest
# ---------------------------------------------------------------------------------------------

def read_trade_bars(paths, day_set):
    """Trade bars (ts = bar START, UTC) of the sessions in `day_set`, read in chunks: date_days, is_put, strike,
    tsec, close."""
    keep = np.array(sorted(day_set), np.int64)
    parts = []
    for path in sorted(paths):
        head = pd.read_csv(path, nrows=0).columns
        missing = [c for c in TRADE_FILE_COLS if c not in head]
        if missing:
            raise ValueError(f"{os.path.basename(path)} missing required column(s): {missing}")
        for chunk in pd.read_csv(path, usecols=["ts", "expiry", "strike", "right", "close"],
                                 dtype={"ts": str, "expiry": str, "right": str}, chunksize=500_000):
            tsec, date_days, _mod, same = _parse_stamps(chunk["ts"].to_numpy(), chunk["expiry"].to_numpy())
            sel = same & np.isin(date_days, keep)
            if not sel.any():
                continue
            parts.append(pd.DataFrame({
                "date_days": date_days[sel], "is_put": _rights(chunk["right"].to_numpy())[sel],
                "strike": chunk["strike"].to_numpy(float)[sel], "tsec": tsec[sel],
                "close": chunk["close"].to_numpy(float)[sel]}))
    cols = ["date_days", "is_put", "strike", "tsec", "close"]
    return pd.concat(parts, ignore_index=True) if parts else pd.DataFrame(columns=cols)


def read_manifest(ext_dir):
    """(Manifest or None, [problems]) from <ext_dir>/quotes_manifest.json (the A6 rule: the unit refuses to run
    without it)."""
    path = os.path.join(ext_dir, MANIFEST_NAME)
    if not os.path.exists(path):
        return None, [f"{path} missing - the unit refuses to run the quote file without its manifest (A6 rule)"]
    try:
        with open(path) as f:
            man = json.load(f)
    except ValueError as e:
        return None, [f"{path} is not valid JSON: {e}"]
    if not isinstance(man, dict):
        return None, [f"{path} must hold a JSON object"]
    problems = []
    for key in ("vendor", "schema", "ts_semantics"):
        if not isinstance(man.get(key), str) or not man[key].strip():
            problems.append(f"manifest key {key!r} is missing or not a non-empty string")
    roc = man.get("rows_on_change", False)
    if not isinstance(roc, bool):
        problems.append(f"manifest key 'rows_on_change' must be a JSON boolean, got {roc!r}")
    excluded = man.get("excluded_sessions", [])
    days = set()
    if not isinstance(excluded, list):
        problems.append("manifest key 'excluded_sessions' must be a list of YYYY-MM-DD strings")
    else:
        for x in excluded:
            if not (isinstance(x, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", x)):
                problems.append(f"excluded_sessions entry {x!r} is not a YYYY-MM-DD string")
                continue
            try:
                days.add(_days(x))
            except ValueError:
                problems.append(f"excluded_sessions entry {x!r} is not a calendar date")
    if problems:
        return None, problems
    return Manifest(man["vendor"], man["schema"], man["ts_semantics"], roc, frozenset(days)), []


# ---------------------------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------------------------

def measure(q, frame, man, trade_paths):
    """Every A51 measurement and check from the canonical quote frame `q`, the canonical minute `frame`, the
    manifest and the trade shards. Returns a dict of DataFrames plus `validation` (list of check rows). Nothing is
    written here."""
    f_days = frame_days(frame)
    q_days = set(int(d) for d in q["date_days"].unique())
    n_excluded = len({d for d in man.excluded if in_window(d) and (d in q_days or d in f_days)})
    q_days -= man.excluded      # A51a: excluded sessions leave the session universe, and every statistic below
    f_days -= man.excluded      # iterates that universe (the DECISION days or a context quarter), so none reads them
    book = QuoteBook(q, max_age_seconds(man.rows_on_change))
    listed = listed_strikes(q)
    groups = session_groups(q_days, f_days)
    days = groups[0][1]
    inst_mods = list(MOD.values()) + [m + 1 for _n, m, _w, _s in sellvol.TRIALS]
    S_of = underlying_lookup(frame, inst_mods)

    surf_legs = surface_legs(book, listed, S_of, groups)
    dec_legs = decision_legs(book, S_of, days)
    sess = session_table(dec_legs, days)
    decision = decision_row(dec_legs, sess, len(days), n_excluded, man)
    depth = depth_table(depth_legs(book, S_of, days, listed))
    trackc = trackc_table(trackc_sessions(book, S_of, days, day_frames(q, days)), len(days))

    bars = read_trade_bars(trade_paths, set(days) & q_days) if trade_paths else pd.DataFrame()
    v2 = (check_v2(book, bars) if trade_paths else
          vrow("V2", "share of bar closes in [bid-0.01, ask+0.01]", 0, np.nan, np.nan, "trade shards present", False,
               f"no {TRADE_GLOB} trade shard found"))
    validation = [check_v1(surf_legs), v2, check_v3(decision)]
    return {"surface": surface_table(surf_legs), "decision": pd.DataFrame([decision], columns=DECISION_COLS),
            "sessions": sess, "depth": depth, "trackc": trackc, "validation": validation}


def output_paths(out):
    """All seven output paths, derived from the directory of `--out` (the decision file is `--out` itself)."""
    d = os.path.dirname(out) or "."
    paths = {k: os.path.join(d, v) for k, v in OUTPUT_NAMES.items()}
    paths["decision"] = out
    return paths


def write_frame(path, df, cols):
    df[cols].to_csv(path, index=False, float_format="%.6f")        # a missing column raises KeyError, never silently


def write_header_only(paths, validation=None):
    """Header-only versions of all seven outputs; the validation file carries `validation` rows if given."""
    for key, cols in OUTPUT_COLS.items():
        if key == "validation" and validation:
            write_frame(paths[key], pd.DataFrame(validation, columns=cols), cols)
        else:
            pd.DataFrame(columns=cols).to_csv(paths[key], index=False)


def quote_shard_paths(ext_dir):
    return sorted(p for p in glob.glob(os.path.join(ext_dir, QUOTE_GLOB)))


def build_frame(ext_dir):
    td = sessions.trading_days_from_vix()
    frame, _dropped, _meta = sessions.build_extended(trading_days=td, ext_dir=ext_dir)
    return frame


def main(inp, out, frame=None):
    paths = output_paths(out)
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    shards = quote_shard_paths(inp)
    if not shards:
        print(f"[SKIP] A51 waits for {os.path.join(inp, QUOTE_GLOB)}")
        write_header_only(paths)
        return
    man, problems = read_manifest(inp)
    if man is None:
        write_header_only(paths, [vrow("MANIFEST", f"{MANIFEST_NAME} present and valid", 0, np.nan, np.nan,
                                       "required (A6)", False, "; ".join(problems))])
        raise CostsFailure("A51 manifest check failed: " + "; ".join(problems))
    try:
        q = read_quote_shards(shards)
        frame = build_frame(inp) if frame is None else frame
        res = measure(q, frame, man, sorted(glob.glob(os.path.join(inp, TRADE_GLOB))))
        failed = [r for r in res["validation"] if not r["pass"]]
        if failed:
            write_header_only(paths, res["validation"])
            raise CostsFailure("A51 validation failed, nothing published: "
                               + "; ".join(f"{r['check']} ({r['detail']})" for r in failed))
        decision = res["decision"].iloc[0].to_dict()
        res["reread"] = reread_table(decision)
        for key in ("surface", "decision", "sessions", "depth", "reread", "trackc"):
            write_frame(paths[key], res[key], OUTPUT_COLS[key])
        write_frame(paths["validation"], pd.DataFrame(res["validation"], columns=VALIDATION_COLS), VALIDATION_COLS)
    except CostsFailure:
        raise
    except Exception:
        write_header_only(paths)         # never leave stale or missing outputs behind an unexpected failure
        raise
    print(res["decision"].drop(columns=["spec"]).T.to_string(header=False))
    print(pd.DataFrame(res["validation"], columns=VALIDATION_COLS).to_string(index=False,
                                                                           float_format=lambda x: f"{x:.4f}"))


def run_unit(inp, out, frame=None):
    _gh.run(lambda: main(inp, out, frame=frame), out)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", default="data/ext")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    run_unit(a.inp, a.out)
