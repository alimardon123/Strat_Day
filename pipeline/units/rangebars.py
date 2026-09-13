"""Track B, step B1 — range-bar rebuild from 1-minute SPY + gate B-a against the owner's
TradingView export, plus the cached XAUUSD gold range-bar series (A40, owner's request
2026-09-13 12:26 UTC, pre-registered before any run).

    python -m pipeline.units.rangebars --in extended --out out/trackB_rangebars_gate.csv

Data (A40's data paragraph). SPY $0.34 and $1.00 range bars are rebuilt from the branch's
regular-session (09:30-16:00 ET) 1-minute SPY bars, 2020-07-27 -> 2026-09-11 (sessions.
build_extended's ext era -- Oanda ends 2020-05-13; the ext feed's own first bar is 2020-07-27,
same as fvg.py's/gapliq.py's HOLDOUT start). `sessions.build_extended` stores every price in SPX
POINTS (A6: SPY x 10, so every downstream cost/strike constant stays in one unit); this unit
divides every OHLC value by that same scale (10.0, `meta["scale"]`) back to SPY DOLLARS before
building range bars, per A40's literal instruction ("prices are in SPX points ... convert back to
SPY dollars / 10 before building").

Range-bar construction rule, as OBSERVED directly in the owner's own file (data/ext/tv_samples/
AMEX_SPY_34R.csv), never assumed: every bar's high-low equals the range EXACTLY; bars are
consecutive (checked: TradingView's own file has NO gap between one bar's close and the next
bar's open once threading is accounted for -- see below); a fast move produces SEVERAL
consecutive full-range bars back to back (observed directly: up to 3 rows sharing one integer-
second Unix timestamp, with a .001/.002 suffix TradingView uses only to order same-instant
sub-bars -- i.e. several bars can form within a single source print). Reconstructing this from
1-MINUTE OHLC (not tick data -- the branch has no tick feed) needs an intra-minute PATH
assumption; A40 fixes it literally: open -> the nearer of high/low -> the other extreme -> close
(4 anchor points per source minute, in that order, even where close coincides with an extreme).
The whole session's anchor points are concatenated in chronological order (one 4-point group per
minute, so minute i's own open point IS the transition target from minute i-1's close -- a real,
if usually tiny, inter-minute gap is walked like any other segment) and walked ONCE: the currently
-open bar's running high/low extend along each straight segment between consecutive anchor
points; the instant high-low first reaches the range, the bar closes at that EXACT price (a new
high closes an up-bar, a new low closes a down-bar) and the next bar opens there immediately,
continuing to walk the remainder of the SAME segment if there is room left in it -- this is
exactly what produces several consecutive full bars from one large minute move, verified by hand
against the owner's own numbers in the coder's transcript (a single source minute's move can
close 2-3 bars in a row, matching the density observed in the owner's own file). This does NOT
claim to exactly reproduce the owner's own file bar-for-bar (their file was almost certainly built
from real sub-minute prints, since most of ITS bars fall exactly on a source-bar boundary but its
own consecutive-bar chaining does not thread the way a pure 4-point-per-minute reconstruction
would -- their feed clearly has finer-than-1-minute resolution we do not have); that is exactly
why gate B-a is a statistical gate (bar-count ratio + resampled-close correlation), not a byte
match. Bars never span a session boundary: a session's first bar opens at that session's own
first-minute open; the session's last, still-forming bar is closed at the session's last
processed price (the last minute's close) and flagged partial=True, never carried into the next
session. ts_open/ts_close are the minute-of-day at which the anchor point that opened / closed a
bar was produced (1-minute, not tick, resolution: several bars fully formed within one minute
share one ts_open==ts_close, exactly like the owner's own same-timestamp rows; this unit emits one
row per bar with no fractional-second suffix -- row order preserves the sequence). Partial
(session-ending) bars are NOT excluded from the cached series: they carry genuine OHLC prices and
dropping them would also silently remove the causal predecessor of the next session's first bars.

Owner's `time` column (data/ext/tv_samples/manifest.json: "Unix seconds UTC"): resolved as bar
OPEN, not close, on direct inspection of AMEX_SPY_34R.csv against the owner's own AMEX_SPY_1.csv
(1-minute) file: (a) the very first range bar of the overlap's first session has
time = 1749475800 = 2025-06-09 09:30:00 ET EXACTLY, that session's own opening minute -- a bar's
OPEN timestamp must equal that; a CLOSE timestamp cannot (a bar cannot close in its own opening
instant); (b) the file's LAST row (time = 2026-03-17 15:56:51 ET, well before the 16:00 close) is
exactly what a live chart's "still-forming" current bar looks like when an export is taken
mid-session -- it carries an OPEN stamp because it has not closed yet; a CLOSE stamp would have
nothing to attach to. This also matches this codebase's own convention elsewhere (sessions.py:
Oanda bars are stamped at their own open). Gate B-a therefore buckets BOTH series by their OPEN
timestamp (see below) rather than mixing an open convention for one series and a close convention
for the other.

Gate B-a -- REDEFINED as Amendment A40c (2026-09-13, mid-run; the original bars-per-session-ratio
/ resampled-correlation gate against the owner's 34R file FAILED for a diagnosed reason, not a
rebuild bug: the owner's own TradingView export is itself not a faithful range-bar series --
median 16 bars/session against a monotone minimum of 14.6 (barely legal), discontinuous opens with
5th/95th-percentile jumps of +/-$1 (a real range bar's next open must equal the prior close
exactly), sub-millisecond duplicate timestamps, and only about 0.5 correlation with realised
volatility. Comparing our rebuild against a flawed reference cannot be a rebuild-correctness gate,
so A40c replaces it with three checks on the REBUILD'S OWN internal consistency plus determinism,
and demotes the owner-comparison to CONTEXT (reported, never gating). Per the task brief: this
gate is not tuned to pass -- A40 fixes the range values and the path rule, and A40c fixes what
"correct" means here; only the CHECKS changed, not the construction in `build_range_bars`/
`_walk_session` above.
  (1) self-consistency, per range: every COMPLETED (partial=False) bar's high-low equals the range
      to the cent (abs diff <= 0.005); and, for every pair of consecutive bars within the SAME
      session, the later bar's open equals the earlier bar's close to the cent (both are direct
      restatements of how `_walk_session` is built, so this checks the CACHE file matches its own
      construction, not just the in-memory result).
  (2) minimum bar count, per range: every session's bar count >= (that session's own high - low,
      taken across its rebuilt bars) / range -- a monotone lower bound (price cannot cross a given
      total distance in fewer than distance/range range-bars) that catches a rebuild dropping bars
      it should have emitted.
  (3) determinism: `build_range_bars` run twice on the identical input, per range, serialised to
      parquet bytes in memory (`io.BytesIO`) and compared byte-for-byte.
`GATE (B-a): PASS/FAIL` is decided on checks (1)-(3) ONLY (both ranges; SPY alone needs all six
SPY rows to pass). CONTEXT rows (4), never gating: bars-per-session median (rebuild vs the owner's
34R file, independently, on their overlap 2025-06-09 -> 2026-03-17) and the 5-minute-resampled
close correlation between them (same bucketing convention as the original gate -- OPEN timestamp,
America/New_York wall clock, last close per bucket, Pearson correlation on the overlap) -- kept in
the output for the reader, with `threshold`/`ok` left blank (NaN) since A40c does not gate on them.

Gate B-a FOR GOLD (A40c's task brief, same three numbered checks, same run): self-consistency
(every completed bar's high-low equals $5.00 to the cent, and open[i+1]==close[i] to the cent for
consecutive bars in the SAME trading week), per-week bar count (every week's bar count >= that
week's own rebuilt high-low / $5, the identical monotone lower bound restated over `week_id`
rather than `session_date`) and determinism (rebuild twice, byte-identical parquet) -- computed by
the SAME `check_self_consistency`/`check_min_bar_count`/`check_determinism` helpers SPY uses, with
a `session_col` argument added to the first two (`session_col="week_id"` for gold; the SPY call
sites are unchanged, since the parameter defaults to "session_date"). There is no minute source
behind the owner's 5000R file to gate the gold rebuild against (A40b's own finding: "no overlap
exists between the two sources"), so, per A40c's own item 4, that comparison is CONTEXT ONLY: ONE
row (the task brief's literal instruction), packing both numbers into `note` since this csv's
schema is one metric per row -- median bars per trading week of the rebuild's OWN TEST window
(2017-2020) versus median bars per week of the owner's 5000R file (its own full 2025-06..2026-03
span), each series' own week id computed the SAME way (`_weekly_session_ids`, the identical
12-hour-gap rule, applied to the rebuild's `ts_close` and to the owner file's own bar-open
timestamps alike -- it has no NYSE-session concept to key off either). `GATE (B-a): PASS/FAIL` is
therefore decided over ALL NINE gating rows -- SPY's six plus gold's three -- printed together as
one combined table, per the task brief ("Print GATE (B-a) on SPY + gold gate rows").

XAUUSD OWNER FILE (CONTEXT ONLY as of A40c): the owner's OANDA_XAUUSD_5000R.csv ($5 range bars)
was A40's only planned XAU input; it is still cached AS-IS here (every bar kept, no rebuild
attempted, no gate -- there is no independent minute source behind it in THIS unit to gate
against) with an added session_date = the UTC calendar date of its own (open) timestamp, per the
brief's literal instruction for this file ("session_date = UTC date" -- XAUUSD/OANDA has no NYSE
session, so a plain UTC calendar day is used here, unlike the NY-trading-day session_date used
for the two SPY series). A40c demotes this file to CONTEXT: `pipeline.units.sweep` no longer
reads it at all (see the GOLD REBUILD paragraph below); it stays cached purely for the reader
and for the one bars-per-week context row in gate_gold below.

GOLD REBUILD (Amendment A40b found the source, A40c fixed the windows; both implemented in THIS
run): TRAIN = Oanda XAU_USD 1-minute 2006-03-19 -> 2016-12-31, TEST = 2017-01-01 -> 2020-05-14,
both read from `data/raw/oanda_XAU_USD.parquet` (DATA.md; fetched by
`pipeline.units.fetch_oanda_xau`, columns ts UTC/open/high/low/close/volume, 4,884,366 rows) and
rebuilt into $5.00 range bars by the SAME per-minute walk as SPY (`_walk_session`, entirely
unchanged: open -> nearer extreme -> other extreme -> close per source minute; see the algorithm
paragraph above). A40c replaced A40b's TEST window (the owner's untouched 5000R file) because no
minute source overlaps it (A40b's own finding) -- gold's TEST must also be a rebuild, per A40c's
literal text, so BOTH windows here come from the one Oanda minute source and the owner's 5000R
file is never read as a trial input (see above). The source's own coverage begins/ends exactly at
these two window boundaries, so `load_gold_minutes`'s date filter is defensive, not a real cut.
Gold has no NYSE trading day, so A40c's task brief fixes "session" (the boundary a bar may never
thread across) as the TRADING WEEK: a new session begins whenever the gap to the PRIOR minute
exceeds 12 hours (`_weekly_session_ids` -- this feed's own weekly Fri ~21:00 UTC close -> Sun
~22:00 UTC open gap is close to 25h, exactly the pattern DATA.md's own clock verification reports
for this file, and every intra-week feed gap on a 24-hour instrument is far under 12h).
`build_range_bars_gold` walks each week's minutes exactly like `build_range_bars` walks a
session's, emitting a `week_id` column used ONLY by the A40c per-week gate checks below (never
cached); the cached `session_date` column is instead set, AFTER the walk, to each bar's own
ts_close's UTC CALENDAR DATE (the task brief's literal instruction) -- independent of the week
boundary, since a single week straddles several UTC calendar dates and every other per-bar
session_date in this file already means "this bar's own day", not "this bar's own session-build
group". ts_open/ts_close are cast to tz-naive UTC wall-clock timestamps (same dtype as the SPY
caches' tz-naive ts_open/ts_close -- NY wall clock there, UTC wall clock here, but matching
column name/dtype is what "the same columns as the SPY caches" means, and it is what keeps
`pipeline.units.sweep`'s window filters from comparing a tz-aware column against a tz-naive
`pd.Timestamp`). Cached, BAR_COLS only (week_id dropped before the parquet write), to
`data/raw/trackB_xau_r5.parquet`.

On any exception: `pipeline.units._gh.run`'s convention (A32) -- empty --out file plus
<out>.error with the traceback, exit code 2 (unchanged from fvg.py/gapliq.py's own precedent;
Amendment A40's item-2 "exit 0" convention applies only to `pipeline.units.sweep`, not here).
"""
import argparse
import os

import numpy as np
import pandas as pd

from pipeline import sessions
from pipeline.units import _gh

OWNER_34R = "data/ext/tv_samples/AMEX_SPY_34R.csv"
OWNER_XAU_5000R = "data/ext/tv_samples/OANDA_XAUUSD_5000R.csv"
SPY_CACHE = {0.34: "data/raw/trackB_spy_r034.parquet", 1.00: "data/raw/trackB_spy_r100.parquet"}
XAU_CACHE = "data/raw/trackB_xau_r5000.parquet"
RANGES = (0.34, 1.00)
BUILD_START, BUILD_END = "2020-07-27", "2026-09-11"      # A40's SPY rebuild window
OVERLAP_START, OVERLAP_END = "2025-06-09", "2026-03-17"  # context rows only (A40c): the owner's 34R file's own span
DEFAULT_SPY_SCALE = 10.0   # SPX points per SPY dollar (A6), used only if meta is unavailable
BAR_COLS = ["ts_open", "ts_close", "open", "high", "low", "close", "session_date", "partial"]

GOLD_RAW = "data/raw/oanda_XAU_USD.parquet"           # DATA.md: fetch_oanda_xau, ts UTC, 2006-03-19..2020-05-14
GOLD_CACHE = "data/raw/trackB_xau_r5.parquet"          # A40c's rebuilt gold series (pipeline.units.sweep's gold input)
GOLD_RANGE = 5.00
GOLD_TRAIN_START, GOLD_TRAIN_END = "2006-03-19", "2016-12-31"  # A40c gold windows
GOLD_TEST_START, GOLD_TEST_END = "2017-01-01", "2020-05-14"    # A40c gold windows
GOLD_OWNER_CONTEXT_LABEL = "2025-06..2026-03"          # the owner's 5000R file's own span, context only


def _walk_session(o, h, l, c, ts, session_date, r):
    """One session's range bars at range `r`, per the module docstring's walk algorithm.
    o/h/l/c/ts are same-length plain Python lists (already .tolist()'d minute bars, chronological
    within the session); returns a list of (ts_open, ts_close, open, high, low, close,
    session_date, partial) tuples, the last one always partial=True (A40: closed at the session's
    last processed price, never carried into the next session)."""
    n = len(o)
    if n == 0:
        return []
    prices = [0.0] * (4 * n)
    times = [None] * (4 * n)
    for i in range(n):
        oi, hi, li, ci, ti = o[i], h[i], l[i], c[i], ts[i]
        nearer, farther = (li, hi) if abs(oi - li) <= abs(oi - hi) else (hi, li)
        j = 4 * i
        prices[j], prices[j + 1], prices[j + 2], prices[j + 3] = oi, nearer, farther, ci
        times[j] = times[j + 1] = times[j + 2] = times[j + 3] = ti
    out = []
    cur_open, cur_open_ts = prices[0], times[0]
    cur_high = cur_low = cur_open
    prev_price, prev_ts = cur_open, times[0]
    for k in range(1, len(prices)):
        target, t = prices[k], times[k]
        if target == prev_price:
            prev_ts = t
            continue
        if target > prev_price:
            while target > cur_high:
                level = cur_low + r
                if target < level:
                    cur_high = target
                    break
                out.append((cur_open_ts, t, cur_open, level, cur_low, level, session_date, False))
                cur_open, cur_open_ts = level, t
                cur_high = cur_low = level
                if target == level:
                    break
        else:
            while target < cur_low:
                level = cur_high - r
                if target > level:
                    cur_low = target
                    break
                out.append((cur_open_ts, t, cur_open, cur_high, level, level, session_date, False))
                cur_open, cur_open_ts = level, t
                cur_high = cur_low = level
                if target == level:
                    break
        prev_price, prev_ts = target, t
    out.append((cur_open_ts, prev_ts, cur_open, cur_high, cur_low, prev_price, session_date, True))
    return out


def build_range_bars(frame, r):
    """frame: minute rows (already in SPY dollars) with columns date, mod, open, high, low,
    close. One row per completed (or session-closing partial) range bar at range `r`, columns per
    BAR_COLS. See module docstring for the construction rule and every resolved ambiguity."""
    frame = frame.sort_values(["date", "mod"])
    bar_ts = frame["date"] + pd.to_timedelta(frame["mod"], unit="m")
    frame = frame.assign(bar_ts=bar_ts)
    rows = []
    for d, g in frame.groupby("date", sort=True):
        rows.extend(_walk_session(g["open"].tolist(), g["high"].tolist(), g["low"].tolist(),
                                   g["close"].tolist(), g["bar_ts"].tolist(), d, r))
    return pd.DataFrame(rows, columns=BAR_COLS)


def _weekly_session_ids(ts):
    """Gold's "session" (A40c task brief, literal): the trading week -- a new id begins whenever
    the gap to the PRIOR minute exceeds 12 hours (see module docstring's GOLD REBUILD paragraph
    for the verification). `ts` must already be sorted ascending; returns an integer Series, one
    id per input row, monotone non-decreasing."""
    return (pd.Series(ts).diff() > pd.Timedelta(hours=12)).cumsum()


def load_gold_minutes(path=GOLD_RAW):
    """Oanda XAU_USD 1-minute bars (A40c's gold rebuild source; DATA.md), filtered to the A40c
    TRAIN+TEST span 2006-03-19..2020-05-14 -- the source's own full coverage, so this filter is
    defensive (guards against the raw file drifting under this unit), not a real cut."""
    d = pd.read_parquet(path)
    start = pd.Timestamp(GOLD_TRAIN_START, tz="UTC")
    end = pd.Timestamp(GOLD_TEST_END, tz="UTC") + pd.Timedelta(days=1)
    d = d[(d["ts"] >= start) & (d["ts"] < end)]
    return d.sort_values("ts").reset_index(drop=True)


def build_range_bars_gold(frame, r=GOLD_RANGE):
    """Gold range-bar rebuild (A40c). `frame`: minute rows with columns ts (UTC, tz-aware), open,
    high, low, close (already sorted ascending). Identical per-minute walk to `build_range_bars`/
    `_walk_session` (see module docstring for the algorithm -- UNCHANGED, only the session
    boundary differs): "session" = the trading week (`_weekly_session_ids`), not the NYSE day.
    Returns one row per completed (or week-ending partial) bar with columns BAR_COLS plus
    `week_id` (the walk's own session-boundary label, kept ONLY for the A40c per-week gate checks
    below, dropped before caching); `session_date` is set AFTER the walk to the UTC CALENDAR DATE
    of the bar's own close (module docstring), independent of `week_id`. ts_open/ts_close are
    cast to tz-naive (see module docstring)."""
    frame = frame.sort_values("ts").reset_index(drop=True)
    week_id = _weekly_session_ids(frame["ts"])
    rows = []
    for wid, g in frame.groupby(week_id, sort=True):
        rows.extend(_walk_session(g["open"].tolist(), g["high"].tolist(), g["low"].tolist(),
                                   g["close"].tolist(), g["ts"].tolist(), wid, r))
    bars = pd.DataFrame(rows, columns=["ts_open", "ts_close", "open", "high", "low", "close", "week_id", "partial"])
    for c in ("ts_open", "ts_close"):
        bars[c] = pd.DatetimeIndex(bars[c]).tz_localize(None)
    bars["session_date"] = pd.DatetimeIndex(bars["ts_close"]).normalize()
    return bars[BAR_COLS + ["week_id"]]


def load_owner_34r(path=OWNER_34R):
    """Owner's TradingView 34R export: `time` = Unix seconds UTC at bar OPEN (see module
    docstring). Adds ts_open_ny (tz-naive America/New_York) and session_date (its NY calendar
    date, for the bars-per-session gate)."""
    d = pd.read_csv(path, usecols=["time", "open", "high", "low", "close"])
    ts_utc = pd.to_datetime(d["time"], unit="s", utc=True)
    ts_ny = ts_utc.dt.tz_convert(sessions.NY).dt.tz_localize(None)
    d = d.assign(ts_open_ny=ts_ny, session_date=ts_ny.dt.normalize())
    return d.sort_values("ts_open_ny").reset_index(drop=True)


def load_owner_xau5000r(path=OWNER_XAU_5000R):
    """Owner's TradingView XAUUSD 5000R ($5) export, cached AS-IS (every bar kept, no rebuild);
    session_date = the UTC calendar date of its own (open) timestamp, per the brief."""
    d = pd.read_csv(path)
    ts_utc = pd.to_datetime(d["time"], unit="s", utc=True)
    d = d.assign(session_date=ts_utc.dt.tz_localize(None).dt.normalize())
    return d.sort_values("time").reset_index(drop=True)


def check_self_consistency(bars, r, tol=0.005, session_col="session_date"):
    """A40c check (1): every completed bar's high-low equals `r` to the cent; every consecutive
    pair of bars within the same session has open[i+1] == close[i] to the cent. `session_col` is
    the boundary a bar may never thread across -- "session_date" (NYSE day) for SPY, "week_id"
    (trading week, `_weekly_session_ids`) for gold. Returns (n_bad, n_hl_bad, n_open_close_bad,
    n_completed, n_consecutive_pairs)."""
    high, low = bars["high"].to_numpy(float), bars["low"].to_numpy(float)
    open_, close = bars["open"].to_numpy(float), bars["close"].to_numpy(float)
    partial, session = bars["partial"].to_numpy(bool), bars[session_col].to_numpy()
    completed = ~partial
    hl_bad = int((completed & (np.abs(high - low - r) > tol)).sum())
    same_session_next = session[:-1] == session[1:]
    gap = np.abs(open_[1:] - close[:-1])
    oc_bad = int((same_session_next & (gap > tol)).sum())
    return hl_bad + oc_bad, hl_bad, oc_bad, int(completed.sum()), int(same_session_next.sum())


def check_min_bar_count(bars, r, session_col="session_date"):
    """A40c check (2): every session's bar count >= (that session's own rebuilt high - low) /
    range (a monotone lower bound: price cannot cross a given distance in fewer bars than
    distance/range). `session_col` as in `check_self_consistency` ("week_id" for gold). Returns
    (n_sessions_violating, n_sessions)."""
    g = bars.groupby(session_col).agg(n_bars=("close", "size"), sess_high=("high", "max"), sess_low=("low", "min"))
    min_required = (g["sess_high"] - g["sess_low"]) / r
    bad = int((g["n_bars"] + 1e-9 < min_required).sum())
    return bad, int(len(g))


def check_determinism(win, r, builder=build_range_bars):
    """A40c check (3): `builder` (default `build_range_bars`; gold passes `build_range_bars_gold`)
    run twice on the identical input, serialised to parquet bytes in memory, compared
    byte-for-byte. Returns True iff identical."""
    import io
    buf1, buf2 = io.BytesIO(), io.BytesIO()
    builder(win, r).to_parquet(buf1, index=False)
    builder(win, r).to_parquet(buf2, index=False)
    return buf1.getvalue() == buf2.getvalue()


def gate_b_a(win, cached, owner_34r):
    """A40c's gate B-a: rows for checks (1)-(3) (gating, `counts_toward_gate`=True) per range,
    plus CONTEXT rows (4, never gating) comparing the r=0.34 rebuild against the owner's 34R file
    on their overlap 2025-06-09 -> 2026-03-17. Returns (rows, overall_ok) where overall_ok is
    decided from the gating rows only."""
    rows = []
    for r in RANGES:
        bars = cached[r]
        n_bad, hl_bad, oc_bad, n_completed, n_pairs = check_self_consistency(bars, r)
        rows.append(dict(check=f"self_consistency_r{r:.2f}", value=n_bad, threshold=0, ok=(n_bad == 0),
                          counts_toward_gate=True,
                          note=f"hl_bad={hl_bad}/{n_completed} completed bars, open_close_bad={oc_bad}/{n_pairs} consecutive pairs"))
        mb_bad, n_sessions = check_min_bar_count(bars, r)
        rows.append(dict(check=f"min_bar_count_r{r:.2f}", value=mb_bad, threshold=0, ok=(mb_bad == 0),
                          counts_toward_gate=True, note=f"sessions violating n_bars>=(H-L)/range: {mb_bad}/{n_sessions}"))
        det_ok = check_determinism(win, r)
        rows.append(dict(check=f"determinism_r{r:.2f}", value=int(det_ok), threshold=1, ok=det_ok,
                          counts_toward_gate=True, note="rebuild twice, byte-identical parquet"))

    start, end = pd.Timestamp(OVERLAP_START), pd.Timestamp(OVERLAP_END)
    reb = cached[0.34][(cached[0.34]["session_date"] >= start) & (cached[0.34]["session_date"] <= end)]
    own = owner_34r[(owner_34r["session_date"] >= start) & (owner_34r["session_date"] <= end)]
    reb_n, own_n = reb.groupby("session_date").size(), own.groupby("session_date").size()
    common = reb_n.index.intersection(own_n.index)
    rows.append(dict(check="context_bars_per_session_median_rebuild_r034", value=float(reb_n.median()) if len(reb_n) else np.nan,
                      threshold=np.nan, ok=np.nan, counts_toward_gate=False, note=f"{len(reb_n)} sessions in overlap"))
    rows.append(dict(check="context_bars_per_session_median_owner_34R", value=float(own_n.median()) if len(own_n) else np.nan,
                      threshold=np.nan, ok=np.nan, counts_toward_gate=False, note=f"{len(own_n)} sessions in overlap, {len(common)} common with rebuild"))
    reb5 = (reb.assign(bucket=reb["ts_open"].dt.floor("5min")).sort_values("ts_open").groupby("bucket")["close"].last())
    own5 = (own.assign(bucket=own["ts_open_ny"].dt.floor("5min")).sort_values("ts_open_ny").groupby("bucket")["close"].last())
    joined = pd.concat([reb5.rename("rebuilt"), own5.rename("owner")], axis=1).dropna()
    corr = float(joined["rebuilt"].corr(joined["owner"])) if len(joined) >= 2 else np.nan
    rows.append(dict(check="context_resampled_5min_close_corr_r034_vs_owner", value=corr, threshold=np.nan,
                      ok=np.nan, counts_toward_gate=False, note=f"{len(joined)} common 5-min buckets in overlap"))

    gate_rows = [r_ for r_ in rows if r_["counts_toward_gate"]]
    overall_ok = bool(all(r_["ok"] for r_ in gate_rows))
    return rows, overall_ok


def gate_gold(win_gold, gold_bars, r=GOLD_RANGE):
    """A40c's gate B-a extended to gold (module docstring's "Gate B-a FOR GOLD" paragraph): checks
    (1)-(3) only, grouped by `week_id` (gold's own "session"); no owner-file gate is possible (no
    overlapping minute source, A40b), so the owner comparison lives in `gold_context_row` instead.
    Returns rows (gating, `counts_toward_gate`=True)."""
    rows = []
    n_bad, hl_bad, oc_bad, n_completed, n_pairs = check_self_consistency(gold_bars, r, session_col="week_id")
    rows.append(dict(check="self_consistency_xau_r5", value=n_bad, threshold=0, ok=(n_bad == 0),
                      counts_toward_gate=True,
                      note=f"hl_bad={hl_bad}/{n_completed} completed bars, open_close_bad={oc_bad}/{n_pairs} consecutive pairs (per trading week)"))
    mb_bad, n_weeks = check_min_bar_count(gold_bars, r, session_col="week_id")
    rows.append(dict(check="min_bar_count_xau_r5", value=mb_bad, threshold=0, ok=(mb_bad == 0),
                      counts_toward_gate=True, note=f"weeks violating n_bars>=(H-L)/range: {mb_bad}/{n_weeks}"))
    det_ok = check_determinism(win_gold, r, builder=build_range_bars_gold)
    rows.append(dict(check="determinism_xau_r5", value=int(det_ok), threshold=1, ok=det_ok,
                      counts_toward_gate=True, note="rebuild twice, byte-identical parquet"))
    return rows


def gold_context_row(gold_bars, owner_xau):
    """A40c gold context row (never gating): bars per trading week of the rebuild's OWN TEST
    window (2017-2020) versus bars per week of the owner's 5000R file (its own full
    2025-06..2026-03 span) -- ONE row, per the task brief's literal instruction, both numbers
    packed into `note` (this csv's schema is one metric per row). Each series' own week id is
    computed the SAME way (`_weekly_session_ids`'s 12-hour-gap rule) on its own timestamps: the
    rebuild's `ts_close`, the owner file's own bar-open `time`."""
    test_start, test_end = pd.Timestamp(GOLD_TEST_START), pd.Timestamp(GOLD_TEST_END)
    reb = gold_bars[(gold_bars["session_date"] >= test_start) & (gold_bars["session_date"] <= test_end)]
    reb_weeks = reb.groupby("week_id").size()
    own_ts = pd.to_datetime(owner_xau["time"], unit="s", utc=True).sort_values().reset_index(drop=True)
    own_week_id = _weekly_session_ids(own_ts)
    own_weeks = pd.Series(1, index=own_week_id.to_numpy()).groupby(level=0).sum()
    reb_med = float(reb_weeks.median()) if len(reb_weeks) else np.nan
    own_med = float(own_weeks.median()) if len(own_weeks) else np.nan
    return dict(check="context_bars_per_week_rebuild_test_vs_owner_5000R", value=reb_med,
                threshold=np.nan, ok=np.nan, counts_toward_gate=False,
                note=(f"rebuild TEST (2017-2020, xau_r5) median bars/week={reb_med:.1f} over "
                      f"{len(reb_weeks)} weeks; owner 5000R ({GOLD_OWNER_CONTEXT_LABEL}) median "
                      f"bars/week={own_med:.1f} over {len(own_weeks)} weeks"))


def main(inp, out):
    if inp != "extended":
        raise ValueError(f"pipeline.units.rangebars only supports --in extended (got {inp!r})")
    os.makedirs("data/raw", exist_ok=True)
    td = sessions.trading_days_from_vix()
    frame, _dropped, meta = sessions.build_extended(trading_days=td)
    if meta is not None and meta["instrument"] != "SPY":
        raise ValueError(f"rangebars only supports a SPY ext feed (A40's data paragraph); got {meta['instrument']}")
    scale = meta["scale"] if meta is not None else DEFAULT_SPY_SCALE
    start, end = pd.Timestamp(BUILD_START), pd.Timestamp(BUILD_END)
    win = frame[(frame["date"] >= start) & (frame["date"] <= end)].copy()
    for c in ("open", "high", "low", "close"):
        win[c] = win[c] / scale

    cached = {}
    for r in RANGES:
        bars = build_range_bars(win, r)
        bars.to_parquet(SPY_CACHE[r], index=False)
        cached[r] = bars
        print(f"SPY ${r:.2f} range bars: {len(bars):,} bars, {bars['session_date'].nunique():,} sessions "
              f"({bars['session_date'].min()} -> {bars['session_date'].max()})" if len(bars) else
              f"SPY ${r:.2f} range bars: 0 bars (no minute data in {BUILD_START}..{BUILD_END})")

    owner_34r = load_owner_34r()
    gate_rows_spy, ok_spy = gate_b_a(win, cached, owner_34r)

    win_gold = load_gold_minutes()
    gold_bars = build_range_bars_gold(win_gold, GOLD_RANGE)
    gold_bars[BAR_COLS].to_parquet(GOLD_CACHE, index=False)
    print(f"XAUUSD ${GOLD_RANGE:.2f} range bars (rebuild): {len(gold_bars):,} bars, "
          f"{gold_bars['week_id'].nunique():,} trading weeks "
          f"({gold_bars['session_date'].min()} -> {gold_bars['session_date'].max()})")
    gate_rows_gold = gate_gold(win_gold, gold_bars)

    xau = load_owner_xau5000r()
    xau.to_parquet(XAU_CACHE, index=False)
    print(f"XAUUSD 5000R gold cache: {len(xau):,} bars, {xau['session_date'].nunique():,} UTC calendar days "
          f"({xau['session_date'].min()} -> {xau['session_date'].max()})")
    gate_rows_gold.append(gold_context_row(gold_bars, xau))

    gate_rows = gate_rows_spy + gate_rows_gold
    gate_ok = ok_spy and all(r_["ok"] for r_ in gate_rows_gold if r_["counts_toward_gate"])
    pd.DataFrame(gate_rows).to_csv(out, index=False, float_format="%.6f")
    print(pd.DataFrame(gate_rows).to_string(index=False))
    print(f"GATE (B-a): {'PASS' if gate_ok else 'FAIL'}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", default="extended")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    _gh.run(lambda: main(a.inp, a.out), a.out)
