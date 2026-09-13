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
`GATE (B-a): PASS/FAIL` is printed and decided on checks (1)-(3) ONLY (both ranges; PASS requires
all six rows). CONTEXT rows (4), never gating: bars-per-session median (rebuild vs the owner's
34R file, independently, on their overlap 2025-06-09 -> 2026-03-17) and the 5-minute-resampled
close correlation between them (same bucketing convention as the original gate -- OPEN timestamp,
America/New_York wall clock, last close per bucket, Pearson correlation on the overlap) -- kept in
the output for the reader, with `threshold`/`ok` left blank (NaN) since A40c does not gate on them.

XAUUSD: the owner's OANDA_XAUUSD_5000R.csv ($5 range bars) is the ONLY XAU input this run (A40);
it is cached AS-IS (every bar kept, no rebuild attempted, no gate -- there is no independent
minute source behind it in THIS unit to gate against) with an added session_date = the UTC
calendar date of its own (open) timestamp, per the brief's literal instruction for this file
("session_date = UTC date" -- XAUUSD/OANDA has no NYSE session, so a plain UTC calendar day is
used here, unlike the NY-trading-day session_date used for the two SPY series).

SCOPE NOTE (Amendment A40b, mid-run, 2026-09-13): a longer 2006-03..2020-05 Oanda XAU_USD minute
source was found after this unit's first run; a SEPARATE, not-yet-written unit will rebuild THAT
into TRAIN range bars, with the owner's 5000R file reserved, unseen, as the TEST-only gold window.
This unit's job is unchanged by that amendment: cache the owner's 5000R file untouched (this file
is `pipeline.units.sweep`'s gold input once it is enabled there, per that unit's own docstring).

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


def check_self_consistency(bars, r, tol=0.005):
    """A40c check (1): every completed bar's high-low equals `r` to the cent; every consecutive
    pair of bars within the same session has open[i+1] == close[i] to the cent. Returns
    (n_bad, n_hl_bad, n_open_close_bad, n_completed, n_consecutive_pairs)."""
    high, low = bars["high"].to_numpy(float), bars["low"].to_numpy(float)
    open_, close = bars["open"].to_numpy(float), bars["close"].to_numpy(float)
    partial, session = bars["partial"].to_numpy(bool), bars["session_date"].to_numpy()
    completed = ~partial
    hl_bad = int((completed & (np.abs(high - low - r) > tol)).sum())
    same_session_next = session[:-1] == session[1:]
    gap = np.abs(open_[1:] - close[:-1])
    oc_bad = int((same_session_next & (gap > tol)).sum())
    return hl_bad + oc_bad, hl_bad, oc_bad, int(completed.sum()), int(same_session_next.sum())


def check_min_bar_count(bars, r):
    """A40c check (2): every session's bar count >= (that session's own rebuilt high - low) /
    range (a monotone lower bound: price cannot cross a given distance in fewer bars than
    distance/range). Returns (n_sessions_violating, n_sessions)."""
    g = bars.groupby("session_date").agg(n_bars=("close", "size"), sess_high=("high", "max"), sess_low=("low", "min"))
    min_required = (g["sess_high"] - g["sess_low"]) / r
    bad = int((g["n_bars"] + 1e-9 < min_required).sum())
    return bad, int(len(g))


def check_determinism(win, r):
    """A40c check (3): `build_range_bars` run twice on the identical input, serialised to parquet
    bytes in memory, compared byte-for-byte. Returns True iff identical."""
    import io
    buf1, buf2 = io.BytesIO(), io.BytesIO()
    build_range_bars(win, r).to_parquet(buf1, index=False)
    build_range_bars(win, r).to_parquet(buf2, index=False)
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
    gate_rows, gate_ok = gate_b_a(win, cached, owner_34r)
    pd.DataFrame(gate_rows).to_csv(out, index=False, float_format="%.6f")
    print(pd.DataFrame(gate_rows).to_string(index=False))
    print(f"GATE (B-a): {'PASS' if gate_ok else 'FAIL'}")

    xau = load_owner_xau5000r()
    xau.to_parquet(XAU_CACHE, index=False)
    print(f"XAUUSD 5000R gold cache: {len(xau):,} bars, {xau['session_date'].nunique():,} UTC calendar days "
          f"({xau['session_date'].min()} -> {xau['session_date'].max()})")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", default="extended")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    _gh.run(lambda: main(a.inp, a.out), a.out)
