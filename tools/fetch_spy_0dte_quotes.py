"""Run this on YOUR machine (the research container has no Databento key and no vendor access).

PURPOSE (ACCEPTANCE.md Amendment A51 and its clarification A51a). A51 reopens the "no real 0DTE quotes" non-goal
for a MEASUREMENT only (zero trials): the real bid/ask cost of the programme's instrument. It needs consolidated
quotes for every SPY contract expiring that day with a strike within +/-4 percent of the session's 09:30 SPY price,
for the DECISION WINDOW 2026-03-02 -> 2026-09-11 (135 sessions). This tool buys them from Databento (dataset
OPRA.PILLAR, schema cbbo-1m) and writes the vendor-neutral input A51 fixes:
  data/ext/spy_0dte_quotes_1min_<YYYY-MM>.csv.gz   monthly shards, each < 100 MB, sorted by ts, strike, right
      columns ts,expiry,strike,right,bid,ask,bid_size,ask_size
      ts       UTC 'YYYY-MM-DD HH:MM:SS' on a whole minute = the vendor's ts_recv = the END of its one-minute
               interval = the instant at which that consolidated best bid and offer applies (A51/A51a)
      expiry   'YYYY-MM-DD', the New York date of ts (same-day contracts only); strike in SPY dollars; right C or P
      bid,ask  dollars; EMPTY where the vendor sent an empty book (= no quote at that instant; the row is kept)
      sizes    contracts
  data/ext/quotes_manifest.json    vendor, dataset, schema, ts_semantics, rows_on_change, band_pct, window,
                                   n_sessions, excluded_sessions, no_data_sessions, unresolved_symbols, per-shard
                                   sha256 and rows, fetched_at, client_version, cost_estimate_usd
      n_sessions = sessions whose quotes are in the shards. excluded_sessions = sessions the vendor reports degraded
      or missing (A51a; not fetched). no_data_sessions = the other sessions of the window with no quotes: pending at
      the vendor, none of their symbols listed, or nothing came back. These are NOT excluded: A51's coverage gate
      must see them as missing legs, so a silent vendor gap can never hide. (no_data_sessions is the one key this
      tool adds to the fixed manifest; readers that do not know it ignore it.)
The vendor emits a record ONLY for a minute in which the BBO or last sale changed, so a missing row means
"unchanged", not "no quote" (A51a: the manifest declares rows_on_change = true).
NOT implemented: A51's optional instants-only fetch; this tool always requests the full 09:30-16:00 session.

ONE-TIME SETUP (an isolated environment; the pipeline's own Python keeps its pinned pandas/numpy):
    python -m venv .venv-quotes && .venv-quotes/bin/pip install databento==0.87.0
The API key is read from the ENVIRONMENT ONLY (there is no --key option; never put it on a command line):
    export DATABENTO_API_KEY=...

HOW THE OWNER RUNS IT (from the repo root):
    .venv-quotes/bin/python tools/fetch_spy_0dte_quotes.py --estimate
    .venv-quotes/bin/python tools/fetch_spy_0dte_quotes.py --download --max-usd 150
    python3 tools/fetch_spy_0dte_quotes.py --validate-only        # pandas only; the system Python is enough
    make all

  --estimate [--start 2026-03-02 --end 2026-09-11]
        Metadata calls only (symbology, dataset condition, cost, billable size are free): derives the sessions from
        data/ext/spx_1min_2020-05_2026-09.csv.gz, builds the candidate OSI symbols (every integer-dollar strike in
        [floor(0.96 P), ceil(1.04 P)], both rights; P = open of the 09:30 ET bar, or of the first bar at or after
        09:30, flagged), keeps those the vendor lists, excludes sessions the vendor reports degraded or missing
        (A51a), and prints total USD, USD per month, billable bytes, sessions and symbols. NOTHING is downloaded.
  --download --max-usd X [--start ... --end ...]
        THE COST GUARD: re-runs the estimate and ABORTS (exit 3, no get_range call, nothing written) if the total
        exceeds X (equal to X proceeds). Otherwise downloads one session at a time, 09:30:00 -> 16:00:01 ET (end is
        exclusive on ts_recv, so the record stamped 16:00:00 is included), caches each session's converted rows
        under data/ext/_quotes_cache/<date>.csv.gz (resumable: a cached session is never requested again),
        then writes the monthly shards and the manifest, then runs the validator. Safe to re-run after a failure.
  --from-dbn FILE --out FILE
        Offline: convert a local DBN file to the vendor-neutral rows with the exact conversion --download uses.
  --validate-only
        Offline, no databento import: manifest present; every shard's sha256 and row count match; columns exact;
        ts on whole minutes; expiry == New York date of ts; right in {C, P}; no duplicate (ts, strike, right); every
        strike inside the band of its session's 09:30 price; every session in the manifest window is either in the
        shards, excluded_sessions or no_data_sessions; no shard file on disk the manifest does not list (delete
        stale ones).
        REPORTED, not failed: share of crossed (bid > ask) and locked (bid == ask) rows. Exit 1 on any hard failure.

Exit codes: 0 ok; 1 failure (validation, vendor error); 2 usage error; 3 cost guard abort.
Retries: 429, 5xx, 408 and timeouts are retried with exponential backoff (Retry-After honoured); the vendor client
has no retries of its own and a 100 s timeout. get_range is called WITHOUT its path= argument (that opens its
file with "x+b" and is not retry-safe); results are converted in memory and written by temp file + os.replace.
"""
import argparse
import datetime as dt
import email.utils
import gzip
import hashlib
import io
import json
import math
import os
import re
import sys
import time
from dataclasses import dataclass, field
from decimal import Decimal
from importlib import metadata as importlib_metadata
from typing import NamedTuple

import numpy as np
import pandas as pd

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXT_DIR = os.path.join(REPO, "data", "ext")
MINUTE_FILE = "spx_1min_2020-05_2026-09.csv.gz"      # the canonical SPY minute file (SPY dollars, ts UTC)
CACHE_SUBDIR = "_quotes_cache"
SHARD_PREFIX = "spy_0dte_quotes_1min_"
MANIFEST_FILE = "quotes_manifest.json"

VENDOR, DATASET, SCHEMA = "Databento", "OPRA.PILLAR", "cbbo-1m"
ROOT = "SPY"
NY = "America/New_York"
BAND_PCT = 4.0                                        # A51: strikes within +/-4 percent of the 09:30 SPY price
WINDOW_START, WINDOW_END = "2026-03-02", "2026-09-11"  # A51's DECISION WINDOW (the downloader's default request)
COLS = ["ts", "expiry", "strike", "right", "bid", "ask", "bid_size", "ask_size"]
MAX_SYMBOLS = 2000                                    # the vendor's per-request symbol limit
MAX_SHARD_BYTES = 100_000_000                         # A51: each shard under 100 MB (decimal, stricter than 100 MiB)
RTH_START, RTH_END = 570, 960                         # minute of day, New York: 09:30 .. 16:00
TS_SEMANTICS = ("ts = ts_recv = end of the vendor's one-minute interval = the instant the consolidated BBO applies; "
                "A51/A51a")
EXCLUDE_CONDITIONS = ("degraded", "missing")   # A51a: the vendor reports these: excluded_sessions, never fetched
NO_DATA_CONDITIONS = ("pending",)              # not yet available: cannot be fetched, but NOT excluded (a visible gap)
MANIFEST_KEYS = ["vendor", "dataset", "schema", "ts_semantics", "rows_on_change", "band_pct", "window", "n_sessions",
                 "excluded_sessions", "unresolved_symbols", "shards", "fetched_at", "client_version",
                 "cost_estimate_usd"]          # required; build_manifest also writes no_data_sessions (optional)
DTYPES = {"ts": str, "expiry": str, "strike": "float64", "right": str, "bid": "float64", "ask": "float64",
          "bid_size": "int64", "ask_size": "int64"}


# ----------------------------------------------------------------------------------------------------------------
# OSI symbols and the strike band (pure)
# ----------------------------------------------------------------------------------------------------------------
class Osi(NamedTuple):
    root: str
    expiry: str      # YYYY-MM-DD
    right: str       # C or P
    strike: float    # dollars


_OSI = re.compile(r"^(.{6})(\d{2})(\d{2})(\d{2})([CP])(\d{8})$")


def osi_symbol(expiry, right, strike, root=ROOT):
    """The exact 21-character OSI symbol: root right-padded to 6, YYMMDD, C/P, strike*1000 as 8 digits
    (SPY, 2024-02-01, C, 480 -> 'SPY   240201C00480000')."""
    right = str(right).upper()
    if right not in ("C", "P"):
        raise ValueError(f"right must be C or P, got {right!r}")
    if not 1 <= len(root) <= 6 or root != root.strip():
        raise ValueError(f"root must be 1-6 characters without padding, got {root!r}")
    day = expiry if isinstance(expiry, dt.date) else dt.date.fromisoformat(str(expiry))
    if not 2000 <= day.year <= 2099:
        raise ValueError(f"OSI carries a two-digit year; {day} is outside 2000-2099")
    mills = round(float(strike) * 1000)
    if abs(float(strike) * 1000 - mills) > 1e-6 or not 0 < mills < 10 ** 8:
        raise ValueError(f"strike {strike!r} is not representable as 8 digits of strike*1000")
    return f"{root:<6}{day:%y%m%d}{right}{mills:08d}"


def parse_osi(symbol):
    """Osi(root, expiry 'YYYY-MM-DD', right, strike) from a 21-character OSI symbol. The expiry is read from the
    symbol itself, never from the vendor's definition schema (its UTC-midnight expiration is the previous day in
    New York)."""
    m = _OSI.match(symbol) if isinstance(symbol, str) else None
    if not m:
        raise ValueError("not an OSI symbol (21 chars: root padded to 6, YYMMDD, C/P, 8-digit strike*1000): "
                         f"{symbol!r}")
    root, yy, mm, dd, right, strike = m.groups()
    try:
        expiry = dt.date(2000 + int(yy), int(mm), int(dd))
    except ValueError:
        raise ValueError(f"OSI symbol {symbol!r} carries an invalid expiry date") from None
    return Osi(root.strip(), expiry.isoformat(), right, int(strike) / 1000.0)


def band_bounds(price, band_pct=BAND_PCT):
    """(lo, hi): the integer-dollar strike range [floor((1 - b) P), ceil((1 + b) P)] for the band b = band_pct / 100.
    Exact decimal arithmetic, so an edge that is an integer in decimal is an integer here."""
    p = Decimal(repr(float(price)))
    b = Decimal(repr(float(band_pct))) / 100
    return math.floor((1 - b) * p), math.ceil((1 + b) * p)


def band_strikes(price, band_pct=BAND_PCT):
    """Every integer-dollar strike in the band (SPY lists a $1 grid), ascending."""
    lo, hi = band_bounds(price, band_pct)
    return list(range(lo, hi + 1))


def candidate_symbols(day, price, root=ROOT):
    """OSI symbols of every candidate contract expiring on `day`: each band strike, calls then puts."""
    return [osi_symbol(day, right, k, root) for k in band_strikes(price) for right in ("C", "P")]


def chunks(seq, n=MAX_SYMBOLS):
    seq = list(seq)
    return [seq[i:i + n] for i in range(0, len(seq), n)]


def session_window(day):
    """(start, end) of a session's request: 09:30:00 and 16:00:01 America/New_York on `day`, tz-aware. The vendor's
    end is exclusive on ts_recv, so 16:00:01 includes the record stamped 16:00:00."""
    return (pd.Timestamp(f"{day} 09:30:00", tz=NY), pd.Timestamp(f"{day} 16:00:01", tz=NY))


# ----------------------------------------------------------------------------------------------------------------
# Sessions from the canonical SPY minute file
# ----------------------------------------------------------------------------------------------------------------
class Session(NamedTuple):
    date: str          # New York date, YYYY-MM-DD
    price: float       # P: open of the 09:30 ET bar, else of the first bar at or after 09:30
    open_minute: int   # minute of day of the bar P came from (570 = 09:30; anything else is flagged)


def load_sessions(ext_dir, start, end):
    """Sessions from `start` to `end` inclusive: a session is a New York weekday date with regular-hours bars
    (09:30 <= t < 16:00) in the canonical SPY minute file. Returns [Session] ascending by date."""
    dt.date.fromisoformat(start), dt.date.fromisoformat(end)
    path = os.path.join(ext_dir, MINUTE_FILE)
    if not os.path.exists(path):
        raise FileNotFoundError(f"{path} missing: the sessions and the 09:30 prices come from the canonical "
                                "minute file")
    d = pd.read_csv(path, usecols=["ts", "open"], dtype={"ts": str}, float_precision="round_trip")
    ts = pd.DatetimeIndex(pd.to_datetime(d["ts"], utc=True)).tz_convert(NY)
    mod = np.asarray(ts.hour * 60 + ts.minute)
    day = np.asarray(ts.strftime("%Y-%m-%d"), dtype=object)
    opn = d["open"].to_numpy(dtype=float)
    keep = (mod >= RTH_START) & (mod < RTH_END) & (np.asarray(ts.dayofweek) < 5) & (day >= start) & (day <= end)
    keep &= np.isfinite(opn)
    f = pd.DataFrame({"t": d["ts"].to_numpy()[keep], "date": day[keep], "mod": mod[keep], "open": opn[keep]})
    first = f.sort_values("t", kind="mergesort").drop_duplicates("date", keep="first").sort_values("date")
    return [Session(str(r.date), float(r.open), int(r.mod)) for r in first.itertuples()]


# ----------------------------------------------------------------------------------------------------------------
# Vendor frame -> vendor-neutral rows (pure)
# ----------------------------------------------------------------------------------------------------------------
def empty_rows():
    return pd.DataFrame({
        "ts": pd.Series([], dtype=object), "expiry": pd.Series([], dtype=object),
        "strike": pd.Series([], dtype="float64"), "right": pd.Series([], dtype=object),
        "bid": pd.Series([], dtype="float64"), "ask": pd.Series([], dtype="float64"),
        "bid_size": pd.Series([], dtype="int64"), "ask_size": pd.Series([], dtype="int64")})[COLS]


def convert_df(df):
    """Rows (COLS, sorted by ts, strike, right) from a DBNStore.to_df() frame of cbbo-1m records.

    ts is the INDEX ts_recv (tz-aware UTC), formatted 'YYYY-MM-DD HH:MM:SS'; expiry, strike and right are parsed from
    the raw OSI `symbol` column; bid/ask are bid_px_00/ask_px_00 in dollars, NaN (written empty) for the vendor's
    empty-book record, which is KEPT; sizes are bid_sz_00/ask_sz_00. Anything that breaks the vendor contract (a
    record off a whole minute, an unmapped symbol, non-float prices) raises rather than being silently altered."""
    need = ["symbol", "bid_px_00", "ask_px_00", "bid_sz_00", "ask_sz_00"]
    missing = [c for c in need if c not in df.columns]
    if missing:
        raise ValueError(f"not a cbbo-1m frame from to_df(): missing columns {missing}")
    if len(df) == 0:
        return empty_rows()
    idx = df.index
    if not isinstance(idx, pd.DatetimeIndex) or idx.tz is None or idx.name != "ts_recv":
        raise ValueError("expected to_df()'s index: a tz-aware DatetimeIndex named 'ts_recv' (A51's ts is ts_recv)")
    for c in ("bid_px_00", "ask_px_00"):
        if not pd.api.types.is_float_dtype(df[c]):
            raise ValueError(f"{c} must be float dollars (to_df(price_type='float')), got {df[c].dtype}")
    ts = idx.tz_convert("UTC")
    if ts.isna().any():
        raise ValueError("ts_recv has missing values")
    off = np.asarray(ts != ts.floor("min"))
    if off.any():
        raise ValueError(f"{int(off.sum())} records are not stamped on a whole minute (first: {ts[off][0]}); "
                         "A51's ts is on whole minutes, so this is not the cbbo-1m the manifest describes")
    sym = df["symbol"]
    if sym.isna().any():
        raise ValueError(f"{int(sym.isna().sum())} records have no mapped raw symbol")
    parsed = {s: parse_osi(s) for s in pd.unique(sym)}
    out = pd.DataFrame({
        "ts": ts.strftime("%Y-%m-%d %H:%M:%S").to_numpy(),
        "expiry": sym.map({s: p.expiry for s, p in parsed.items()}).to_numpy(),
        "strike": sym.map({s: p.strike for s, p in parsed.items()}).to_numpy(dtype=float),
        "right": sym.map({s: p.right for s, p in parsed.items()}).to_numpy(),
        # the vendor's fixed-point 1e-9 grid, so float noise cannot reach the file
        "bid": df["bid_px_00"].to_numpy(dtype=float).round(9),
        "ask": df["ask_px_00"].to_numpy(dtype=float).round(9),
        "bid_size": df["bid_sz_00"].to_numpy().astype("int64"),
        "ask_size": df["ask_sz_00"].to_numpy().astype("int64")})
    return out.sort_values(["ts", "strike", "right"], kind="mergesort").reset_index(drop=True)[COLS]


def dbn_store_rows(store):
    """The one conversion path: a DBNStore (from get_range or a local file) -> vendor-neutral rows."""
    return convert_df(store.to_df(price_type="float", pretty_ts=True, map_symbols=True))


def ny_dates(ts):
    """New York calendar date 'YYYY-MM-DD' of each 'YYYY-MM-DD HH:MM:SS' UTC string in the Series `ts`; NaN where it
    does not parse. Computed on the unique values only."""
    if len(ts) == 0:
        return pd.Series([], dtype=object)
    u = pd.Series(ts.unique())
    parsed = pd.to_datetime(u, format="%Y-%m-%d %H:%M:%S", errors="coerce", utc=True)
    ny = parsed.dt.tz_convert(NY).dt.strftime("%Y-%m-%d")
    return ts.map(dict(zip(u, ny)))


def check_session_rows(rows, day):
    """Download-time guard: every row of a session's request is a same-day contract (expiry == day) stamped on
    that New York date."""
    if len(rows) == 0:
        return
    bad = (rows["expiry"] != day) | (ny_dates(rows["ts"]) != day)
    if bad.any():
        r = rows[bad].iloc[0]
        raise ValueError(f"session {day}: {int(bad.sum())} rows are not same-day contracts stamped that New York "
                         f"date (first: ts {r['ts']}, expiry {r['expiry']})")


# ----------------------------------------------------------------------------------------------------------------
# Writers: deterministic gzip, atomic replace, shards, manifest (pure apart from the files they write)
# ----------------------------------------------------------------------------------------------------------------
def write_csv(df, path, max_bytes=None):
    """Write `df` as CSV to `path` through a temp file and os.replace. A '.gz' path is gzip with a fixed header
    (mtime 0, no embedded name), so equal rows always give equal bytes. With max_bytes, a larger file is refused
    (AssertionError) before it ever appears under its final name."""
    tmp = f"{path}.tmp.{os.getpid()}"
    try:
        if path.endswith(".gz"):
            with open(tmp, "wb") as raw, gzip.GzipFile(filename="", mode="wb", fileobj=raw, compresslevel=6,
                                                       mtime=0) as gz, \
                    io.TextIOWrapper(gz, encoding="utf-8", newline="") as txt:
                df.to_csv(txt, index=False, lineterminator="\n")
        else:
            df.to_csv(tmp, index=False, lineterminator="\n")
        if max_bytes is not None and os.path.getsize(tmp) >= max_bytes:
            raise AssertionError(f"{os.path.basename(path)} is {os.path.getsize(tmp):,} bytes; "
                                 f"each shard must stay under {max_bytes:,}")
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)


def read_rows(path):
    """A cached session or a shard back into a frame with the exact dtypes of COLS (empty bid/ask -> NaN)."""
    df = pd.read_csv(path, dtype=DTYPES, float_precision="round_trip")
    if list(df.columns) != COLS:
        raise ValueError(f"{path}: columns {list(df.columns)} != {COLS}")
    return df


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def write_shards(rows, ext_dir=EXT_DIR):
    """Split `rows` by calendar month of ts (UTC) into <ext_dir>/spy_0dte_quotes_1min_<YYYY-MM>.csv.gz, each sorted
    by ts, strike, right and under MAX_SHARD_BYTES. Returns {filename: {"sha256": ..., "rows": ...}}."""
    rows = rows.sort_values(["ts", "strike", "right"], kind="mergesort").reset_index(drop=True)
    months = rows["ts"].str.slice(0, 7)
    shards = {}
    for month, part in rows.groupby(months, sort=True):
        name = f"{SHARD_PREFIX}{month}.csv.gz"
        path = os.path.join(ext_dir, name)
        write_csv(part[COLS], path, max_bytes=MAX_SHARD_BYTES)
        shards[name] = {"sha256": sha256_file(path), "rows": int(len(part))}
    return shards


def build_manifest(window, n_sessions, excluded_sessions, no_data_sessions, unresolved_symbols, shards, fetched_at,
                   client_version, cost_estimate_usd):
    """The A51/A51a manifest. n_sessions = sessions whose quotes are in the shards; excluded_sessions = sessions the
    vendor reports degraded or missing (A51a); no_data_sessions = sessions with no quotes for any other reason
    (pending, nothing listed, nothing returned), which stay in the session universe so A51's coverage gate counts
    their legs as missing. Together the three lists are every session of the window."""
    return {
        "vendor": VENDOR,
        "dataset": DATASET,
        "schema": SCHEMA,
        "ts_semantics": TS_SEMANTICS,
        "rows_on_change": True,
        "band_pct": BAND_PCT,
        "window": {"start": window[0], "end": window[1]},
        "n_sessions": int(n_sessions),
        "excluded_sessions": sorted(excluded_sessions),
        "no_data_sessions": sorted(no_data_sessions),
        "unresolved_symbols": int(unresolved_symbols),
        "shards": {k: {"sha256": shards[k]["sha256"], "rows": int(shards[k]["rows"])} for k in sorted(shards)},
        "fetched_at": fetched_at,
        "client_version": client_version,
        "cost_estimate_usd": float(cost_estimate_usd),
    }


def write_manifest(manifest, ext_dir=EXT_DIR):
    path = os.path.join(ext_dir, MANIFEST_FILE)
    tmp = f"{path}.tmp.{os.getpid()}"
    try:
        with open(tmp, "w", newline="\n") as f:
            f.write(json.dumps(manifest, indent=1) + "\n")
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)
    return path


# ----------------------------------------------------------------------------------------------------------------
# Validator (pandas only: runs under the system Python, never imports databento)
# ----------------------------------------------------------------------------------------------------------------
@dataclass
class Validation:
    failures: list = field(default_factory=list)
    report: dict = field(default_factory=dict)

    @property
    def ok(self):
        return not self.failures


def _is_iso_date(x):
    try:
        dt.date.fromisoformat(x)
        return isinstance(x, str) and len(x) == 10
    except (TypeError, ValueError):
        return False


def _check_manifest(man, fail):
    """Hard checks on the manifest's own fields (A51 + A51a)."""
    if not isinstance(man, dict):
        fail("manifest is not a JSON object")
        return
    absent = [k for k in MANIFEST_KEYS if k not in man]
    if absent:
        fail(f"manifest lacks keys {absent}")
    for k in ("vendor", "dataset", "schema", "ts_semantics", "fetched_at", "client_version"):
        if k in man and not (isinstance(man[k], str) and man[k].strip()):
            fail(f"manifest {k} must be a non-empty string")
    if "rows_on_change" in man and not isinstance(man["rows_on_change"], bool):
        fail("manifest rows_on_change must be true or false (A51a)")
    if "band_pct" in man and not (isinstance(man["band_pct"], (int, float)) and man["band_pct"] == BAND_PCT):
        fail(f"manifest band_pct must be {BAND_PCT} (A51), got {man['band_pct']!r}")
    w = man.get("window")
    if "window" in man and not (isinstance(w, dict) and _is_iso_date(w.get("start")) and _is_iso_date(w.get("end"))
                                and w["start"] <= w["end"]):
        fail("manifest window must be {'start': 'YYYY-MM-DD', 'end': 'YYYY-MM-DD'} with start <= end")
    if "n_sessions" in man and not (isinstance(man["n_sessions"], int) and man["n_sessions"] >= 0):
        fail("manifest n_sessions must be a non-negative integer")
    ex = man.get("excluded_sessions")
    if "excluded_sessions" in man and not (isinstance(ex, list) and all(_is_iso_date(x) for x in ex)):
        fail("manifest excluded_sessions must be a list of 'YYYY-MM-DD' dates")
    nd = man.get("no_data_sessions", [])
    if not (isinstance(nd, list) and all(_is_iso_date(x) for x in nd)):
        fail("manifest no_data_sessions must be a list of 'YYYY-MM-DD' dates")
    u = man.get("unresolved_symbols")
    if "unresolved_symbols" in man and not (isinstance(u, int) and u >= 0):
        fail("manifest unresolved_symbols must be a non-negative integer")
    sh = man.get("shards")
    if "shards" in man:
        if not (isinstance(sh, dict) and sh):
            fail("manifest shards must be a non-empty {filename: {sha256, rows}} object")
        else:
            for name, e in sh.items():
                if not re.fullmatch(re.escape(SHARD_PREFIX) + r"\d{4}-\d{2}\.csv\.gz", name):
                    fail(f"manifest shard name {name!r} is not {SHARD_PREFIX}<YYYY-MM>.csv.gz")
                if not (isinstance(e, dict) and isinstance(e.get("sha256"), str) and isinstance(e.get("rows"), int)):
                    fail(f"manifest shard {name!r} must carry sha256 (str) and rows (int)")
    if "cost_estimate_usd" in man and not isinstance(man["cost_estimate_usd"], (int, float)):
        fail("manifest cost_estimate_usd must be a number")


def _check_shard(ext_dir, name, entry, band_pct, sessions, fail, acc):
    """Hard checks on one shard; feeds the report accumulator `acc`. Returns the set of session dates it holds."""
    path = os.path.join(ext_dir, name)
    if not os.path.exists(path):
        fail(f"{name}: listed in the manifest but missing on disk")
        return set()
    digest = sha256_file(path)
    if digest != entry.get("sha256"):
        fail(f"{name}: sha256 mismatch (file {digest[:12]}..., manifest {str(entry.get('sha256'))[:12]}...)")
    try:
        cols = list(pd.read_csv(path, nrows=0).columns)
    except Exception as e:  # noqa: BLE001 - any unreadable file is a hard failure, not a crash
        fail(f"{name}: cannot be read ({type(e).__name__}: {e})")
        return set()
    if cols != COLS:
        fail(f"{name}: columns {cols} != {COLS}")
        return set()
    try:
        df = read_rows(path)
    except Exception as e:  # noqa: BLE001
        fail(f"{name}: a value does not parse as its column type ({type(e).__name__}: {e})")
        return set()
    if len(df) != entry.get("rows"):
        fail(f"{name}: {len(df)} rows, manifest says {entry.get('rows')}")
    acc["rows"] += len(df)
    if len(df) == 0:
        fail(f"{name}: no rows")
        return set()

    # ts: 'YYYY-MM-DD HH:MM:00' (whole minute, UTC)
    whole = df["ts"].str.fullmatch(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:00", na=False)
    ny = ny_dates(df["ts"])
    bad_ts = ~whole.astype(bool) | ny.isna()
    if bad_ts.any():
        fail(f"{name}: {int(bad_ts.sum())} rows whose ts is not 'YYYY-MM-DD HH:MM:00' (a whole minute, UTC), "
             f"e.g. {df.loc[bad_ts, 'ts'].iloc[0]!r}")
    month = name[len(SHARD_PREFIX):len(SHARD_PREFIX) + 7]
    off_month = ~bad_ts & (df["ts"].str.slice(0, 7) != month)
    if off_month.any():
        fail(f"{name}: {int(off_month.sum())} rows whose ts is not in {month}")
    # expiry == the New York date of ts (same-day contracts only)
    wrong = ~bad_ts & (ny != df["expiry"])
    if wrong.any():
        r = df[wrong].iloc[0]
        fail(f"{name}: {int(wrong.sum())} rows where expiry != the New York date of ts "
             f"(first: ts {r['ts']}, expiry {r['expiry']})")
    bad_right = ~df["right"].isin(["C", "P"])
    if bad_right.any():
        fail(f"{name}: {int(bad_right.sum())} rows with right not in {{C, P}}")
    dup = df.duplicated(subset=["ts", "strike", "right"], keep="first")
    if dup.any():
        r = df[dup].iloc[0]
        fail(f"{name}: {int(dup.sum())} duplicate (ts, strike, right) rows "
             f"(first: {r['ts']}, {r['strike']}, {r['right']})")
    # value sanity: prices and sizes are non-negative and finite (an empty bid or ask is NaN and allowed)
    for c in ("bid", "ask"):
        v = df[c].to_numpy(dtype=float)
        if (np.isinf(v).any()) or (v[np.isfinite(v)] < 0).any():
            fail(f"{name}: {c} has a negative or infinite value")
    if not np.isfinite(df["strike"].to_numpy(dtype=float)).all() or (df["strike"] <= 0).any():
        fail(f"{name}: strike must be a positive number")
    if (df["bid_size"] < 0).any() or (df["ask_size"] < 0).any():
        fail(f"{name}: a size is negative")

    # reported, never failed: crossed, locked, and rows that are no quote at all
    both = df["bid"].notna() & df["ask"].notna()
    acc["crossed"] += int((both & (df["bid"] > df["ask"])).sum())
    acc["locked"] += int((both & (df["bid"] == df["ask"])).sum())
    acc["no_quote"] += int((~both).sum())

    # band: every strike inside [floor((1 - b) P), ceil((1 + b) P)] of its session's 09:30 price
    pairs = df[["expiry", "strike"]].drop_duplicates()
    known = pairs["expiry"].isin(list(sessions))
    for day in sorted(set(pairs.loc[~known, "expiry"])) if sessions else []:   # no minute file: already reported once
        fail(f"{name}: session {day} has no regular-hours bar in the minute file, so its band cannot be checked")
    pk = pairs[known]
    lohi = pk["expiry"].map(lambda d: band_bounds(sessions[d].price, band_pct))
    lo = lohi.map(lambda t: t[0]).to_numpy(dtype=float)
    hi = lohi.map(lambda t: t[1]).to_numpy(dtype=float)
    outside = (pk["strike"].to_numpy(dtype=float) < lo) | (pk["strike"].to_numpy(dtype=float) > hi)
    if outside.any():
        r = pk[outside].iloc[0]
        b = band_bounds(sessions[r["expiry"]].price, band_pct)
        fail(f"{name}: {int(outside.sum())} (expiry, strike) pairs outside the +/-{band_pct:g}% band of the 09:30 "
             f"price (first: {r['expiry']} strike {r['strike']:g}, band {b[0]}..{b[1]})")
    return set(df["expiry"].unique())


def _date_set(x):
    return {d for d in x if isinstance(d, str)} if isinstance(x, list) else set()


def validate(ext_dir=EXT_DIR):
    """Validation(failures, report) of the quote shards under `ext_dir`. See the module docstring for the checks."""
    v = Validation()
    fail = v.failures.append
    man_path = os.path.join(ext_dir, MANIFEST_FILE)
    if not os.path.exists(man_path):
        fail(f"{MANIFEST_FILE} missing in {ext_dir}: the unit refuses to run without it (A6 rule)")
        return v
    try:
        with open(man_path) as f:
            man = json.load(f)
    except (OSError, ValueError) as e:
        fail(f"{MANIFEST_FILE} unreadable: {e}")
        return v
    _check_manifest(man, fail)
    shards = man.get("shards") if isinstance(man, dict) and isinstance(man.get("shards"), dict) else {}
    on_disk = sorted(n for n in os.listdir(ext_dir) if re.fullmatch(re.escape(SHARD_PREFIX) + r".*\.csv\.gz", n))
    for n in on_disk:
        if n not in shards:
            fail(f"{n}: a shard on disk that the manifest does not list")
    try:
        minute = {s.date: s for s in load_sessions(ext_dir, "1900-01-01", "2999-12-31")}
    except FileNotFoundError as e:
        fail(str(e))
        minute = {}
    man = man if isinstance(man, dict) else {}
    band_pct = man["band_pct"] if isinstance(man.get("band_pct"), (int, float)) else BAND_PCT
    acc = {"rows": 0, "crossed": 0, "locked": 0, "no_quote": 0}
    held = set()
    for name in sorted(shards):
        entry = shards[name] if isinstance(shards[name], dict) else {}
        held |= _check_shard(ext_dir, name, entry, band_pct, minute, fail, acc)
    # every session of the window is in the shards, excluded (vendor) or declared no-data; counts agree
    w = man.get("window")
    excluded, no_data = (_date_set(man.get(k)) for k in ("excluded_sessions", "no_data_sessions"))
    if isinstance(man.get("n_sessions"), int) and man["n_sessions"] != len(held):
        fail(f"manifest n_sessions {man['n_sessions']} != {len(held)} sessions found in the shards")
    if held & (excluded | no_data):
        fail("sessions both in the shards and in excluded_sessions or no_data_sessions: "
             f"{sorted(held & (excluded | no_data))[:5]}")
    if excluded & no_data:
        fail(f"sessions both in excluded_sessions and no_data_sessions: {sorted(excluded & no_data)[:5]}")
    if minute and isinstance(w, dict) and _is_iso_date(w.get("start")) and _is_iso_date(w.get("end")):
        expected = {d for d in minute if w["start"] <= d <= w["end"]}
        absent = sorted(expected - held - excluded - no_data)
        stray = sorted((held | excluded | no_data) - expected)
        if absent:
            fail(f"{len(absent)} sessions of the manifest window have neither quotes nor an exclusion nor a "
                 f"no-data declaration, e.g. {absent[:5]}")
        if stray:
            fail(f"{len(stray)} sessions outside the manifest window or the minute file, e.g. {stray[:5]}")
    v.report = dict(acc, shards=len(shards), sessions=len(held), excluded=len(excluded), no_data=len(no_data))
    return v


def print_validation(v):
    r = v.report
    if r:
        n = max(r["rows"], 1)
        print(f"VALIDATE: {r['shards']} shards, {r['rows']:,} rows, {r['sessions']} sessions "
              f"({r['excluded']} excluded by the vendor's condition, {r['no_data']} with no data)")
        print(f"  reported, not failed: crossed (bid > ask) {r['crossed']:,} rows ({100 * r['crossed'] / n:.4f}%); "
              f"locked (bid == ask) {r['locked']:,} rows ({100 * r['locked'] / n:.4f}%); "
              f"no quote (empty bid or ask) {r['no_quote']:,} rows ({100 * r['no_quote'] / n:.4f}%)")
    for f in v.failures:
        print(f"  FAIL: {f}")
    print("VALID" if v.ok else f"INVALID ({len(v.failures)} hard failures)")


# ----------------------------------------------------------------------------------------------------------------
# The vendor: retry, a keyword-only wrapper, the estimate, the download
# ----------------------------------------------------------------------------------------------------------------
def _transient_transport_error(exc):
    try:
        import requests
    except ImportError:
        return False
    transient = (requests.exceptions.Timeout, requests.exceptions.ConnectionError,
                 requests.exceptions.ChunkedEncodingError)
    permanent = (requests.exceptions.SSLError, requests.exceptions.ProxyError)
    return isinstance(exc, transient) and not isinstance(exc, permanent)


def is_retryable(exc):
    """429, 408 and 5xx responses, timeouts, dropped connections and a stream cut mid-transfer. Everything else
    (401 bad key, 402, 403, 404, 422 and any other 4xx, and every bug) is raised at once."""
    status = getattr(exc, "http_status", None)
    if status is not None:
        return status in (408, 429) or 500 <= status < 600
    if isinstance(exc, (TimeoutError, ConnectionError)):
        return True
    if type(exc).__name__ == "BentoError" and "Error streaming response" in str(exc):
        return True
    return _transient_transport_error(exc)


def retry_after_seconds(exc):
    """The Retry-After header of an HTTP error (seconds or an HTTP date), or None."""
    headers = getattr(exc, "headers", None)
    raw = None
    try:
        for k, val in dict(headers or {}).items():
            if str(k).lower() == "retry-after":
                raw = val
    except (TypeError, ValueError):
        return None
    if raw is None:
        return None
    try:
        return max(0.0, float(raw))
    except (TypeError, ValueError):
        pass
    try:
        when = email.utils.parsedate_to_datetime(str(raw))
        return max(0.0, (when - dt.datetime.now(dt.timezone.utc)).total_seconds())
    except (TypeError, ValueError):
        return None


def call_with_retry(fn, what, *, max_attempts=6, base_delay=2.0, max_delay=120.0, max_retry_after=900.0,
                    sleep=time.sleep):
    """fn() with exponential backoff (base_delay * 2^k, capped at max_delay) on retryable failures; a Retry-After
    header is honoured (never retry sooner than told, capped at max_retry_after). The last failure is raised."""
    for attempt in range(1, max_attempts + 1):
        try:
            return fn()
        except Exception as exc:  # noqa: BLE001 - classified below; non-retryable errors are re-raised unchanged
            if attempt == max_attempts or not is_retryable(exc):
                raise
            delay = min(max_delay, base_delay * 2 ** (attempt - 1))
            told = retry_after_seconds(exc)
            if told is not None:
                delay = max(delay, min(told, max_retry_after))
            print(f"  retry {attempt}/{max_attempts - 1} after {type(exc).__name__} in {what}: "
                  f"{str(exc)[:160]} (sleeping {delay:.0f}s)", file=sys.stderr, flush=True)
            sleep(delay)


def _squash(s):
    return "".join(str(s).split())


class Api:
    """The only place the vendor client is called: every call is KEYWORD-ONLY (get_cost's 4th positional parameter
    is a deprecated `mode`, so a positional call silently mis-sends) and goes through call_with_retry."""

    def __init__(self, client, sleep=time.sleep, max_attempts=6):
        self.client, self.sleep, self.max_attempts = client, sleep, max_attempts

    def _call(self, what, fn, **kwargs):
        return call_with_retry(lambda: fn(**kwargs), what, sleep=self.sleep, max_attempts=self.max_attempts)

    @staticmethod
    def _check(symbols):
        if not 0 < len(symbols) <= MAX_SYMBOLS:
            raise ValueError(f"a request takes 1..{MAX_SYMBOLS} symbols, got {len(symbols)}")
        return list(symbols)

    def conditions(self, start, end):
        """{YYYY-MM-DD: condition} from the vendor's per-date dataset condition (end is inclusive)."""
        rows = self._call("metadata.get_dataset_condition", self.client.metadata.get_dataset_condition,
                          dataset=DATASET, start_date=start, end_date=end)
        return {str(r["date"])[:10]: str(r["condition"]).lower() for r in rows or []}

    def resolve(self, symbols, day):
        """The subset of `symbols` the vendor lists on `day` (free symbology call), candidate order kept."""
        nxt = (dt.date.fromisoformat(day) + dt.timedelta(days=1)).isoformat()
        listed = set()
        for part in chunks(symbols):
            resp = self._call("symbology.resolve", self.client.symbology.resolve, dataset=DATASET, symbols=part,
                              stype_in="raw_symbol", stype_out="instrument_id", start_date=day, end_date=nxt)
            listed |= {_squash(k) for k, mapped in ((resp or {}).get("result") or {}).items() if mapped}
        return [s for s in symbols if _squash(s) in listed]

    def cost(self, symbols, start, end):
        return float(self._call("metadata.get_cost", self.client.metadata.get_cost, dataset=DATASET, start=start,
                                end=end, symbols=self._check(symbols), schema=SCHEMA, stype_in="raw_symbol"))

    def billable_size(self, symbols, start, end):
        return int(self._call("metadata.get_billable_size", self.client.metadata.get_billable_size, dataset=DATASET,
                              start=start, end=end, symbols=self._check(symbols), schema=SCHEMA,
                              stype_in="raw_symbol"))

    def get_range(self, symbols, start, end):
        """A paid call. Never passes path= (not retry-safe): the DBNStore is kept in memory."""
        return self._call("timeseries.get_range", self.client.timeseries.get_range, dataset=DATASET, schema=SCHEMA,
                          symbols=self._check(symbols), stype_in="raw_symbol", start=start, end=end)


@dataclass
class SessionPlan:
    date: str
    price: float
    open_minute: int
    symbols: list = field(default_factory=list)   # candidates the vendor lists
    unresolved: int = 0                            # candidates it does not
    cost_usd: float = 0.0
    billable_bytes: int = 0
    excluded: str = ""                             # the vendor's condition (degraded, missing): A51a exclusion
    no_data: str = ""                              # why there is nothing to fetch (pending, nothing listed): a gap


@dataclass
class Estimate:
    start: str
    end: str
    plans: list
    unreported: list = field(default_factory=list)   # session dates the vendor's condition answer did not mention

    def fetch_plans(self):
        return [p for p in self.plans if not p.excluded and not p.no_data]

    def excluded_plans(self):
        return [p for p in self.plans if p.excluded]

    def no_data_plans(self):
        return [p for p in self.plans if p.no_data]

    @property
    def total_usd(self):
        return round(math.fsum(p.cost_usd for p in self.plans), 6)

    @property
    def total_bytes(self):
        return sum(p.billable_bytes for p in self.plans)

    @property
    def n_symbols(self):
        return sum(len(p.symbols) for p in self.fetch_plans())

    @property
    def unresolved(self):
        return sum(p.unresolved for p in self.fetch_plans())

    def per_month(self):
        out = {}
        for p in self.plans:
            out[p.date[:7]] = out.get(p.date[:7], 0.0) + p.cost_usd
        return {m: round(out[m], 6) for m in sorted(out)}


def estimate(api, sessions, start, end):
    """Metadata calls only (free): resolve the candidates, apply the vendor's per-date condition, and sum get_cost and
    get_billable_size per session over 09:30:00 -> 16:00:01 ET. Nothing is downloaded."""
    cond = api.conditions(start, end)
    plans, unreported = [], []
    for s in sessions:
        p = SessionPlan(s.date, s.price, s.open_minute)
        plans.append(p)
        c = cond.get(s.date)
        if c is None:
            unreported.append(s.date)
        if c in EXCLUDE_CONDITIONS:
            p.excluded = c
            print(f"{s.date}  excluded: the vendor reports this session {c}", flush=True)
            continue
        if c in NO_DATA_CONDITIONS:
            p.no_data = c
            print(f"{s.date}  NO DATA: the vendor reports this session {c}", flush=True)
            continue
        candidates = candidate_symbols(s.date, s.price)
        p.symbols = api.resolve(candidates, s.date)
        p.unresolved = len(candidates) - len(p.symbols)
        if not p.symbols:
            p.no_data = "no symbols resolved"
            print(f"{s.date}  NO DATA: none of {len(candidates)} candidate symbols resolves", flush=True)
            continue
        t0, t1 = session_window(s.date)
        p.cost_usd = math.fsum(api.cost(part, t0, t1) for part in chunks(p.symbols))
        p.billable_bytes = sum(api.billable_size(part, t0, t1) for part in chunks(p.symbols))
        print(f"{s.date}  P={s.price:<8.2f} {len(p.symbols):>4} symbols ({p.unresolved} unresolved)  "
              f"${p.cost_usd:>9,.4f}  {p.billable_bytes / 1e6:>8.1f} MB", flush=True)
    return Estimate(start, end, plans, unreported)


def print_estimate(est):
    fetch = est.fetch_plans()
    late = [p for p in est.plans if p.open_minute != RTH_START]
    print(f"\nA51 QUOTE ESTIMATE  {DATASET} {SCHEMA}  sessions {est.start} -> {est.end}  "
          f"(09:30:00 -> 16:00:01 ET, band +/-{BAND_PCT:g}%)")
    print(f"  sessions in the window (minute file): {len(est.plans)}   to fetch: {len(fetch)}   "
          f"excluded (vendor degraded/missing, A51a): {len(est.excluded_plans())}   "
          f"no data: {len(est.no_data_plans())}")
    for p in est.excluded_plans():
        print(f"    excluded {p.date}: {p.excluded}")
    for p in est.no_data_plans():
        print(f"    NO DATA {p.date}: {p.no_data} (not excluded: the unit counts its legs as missing)")
    for p in late:
        print(f"    FLAG {p.date}: no 09:30 bar; P is the open of the first bar at or after 09:30 "
              f"(minute {p.open_minute // 60:02d}:{p.open_minute % 60:02d})")
    if est.unreported:
        print(f"    WARNING: the vendor's condition answer does not mention {len(est.unreported)} sessions, "
              f"e.g. {est.unreported[:3]}; they are treated as available")
    print(f"  symbols: {est.n_symbols:,} resolved, {est.unresolved:,} candidates unresolved")
    print(f"  billable size: {est.total_bytes:,} bytes ({est.total_bytes / 2 ** 30:.2f} GiB)")
    print("  USD per month:")
    for m, usd in est.per_month().items():
        print(f"    {m}  ${usd:>10,.2f}")
    print(f"  TOTAL USD: ${est.total_usd:,.2f}")
    print("  (metadata calls only: nothing was downloaded)")


class BudgetExceeded(RuntimeError):
    pass


def enforce_budget(total_usd, max_usd):
    """The cost guard: refuse when the estimate EXCEEDS the budget (equal to it proceeds)."""
    if total_usd > max_usd:
        raise BudgetExceeded(f"estimated cost ${total_usd:,.2f} exceeds --max-usd ${max_usd:,.2f}; "
                             "no get_range call was made and nothing was written")


def cache_path(ext_dir, day):
    return os.path.join(ext_dir, CACHE_SUBDIR, f"{day}.csv.gz")


def fetch_session(api, plan):
    """One session's rows: get_range per block of at most MAX_SYMBOLS symbols, converted by the one conversion path."""
    t0, t1 = session_window(plan.date)
    parts = [dbn_store_rows(api.get_range(block, t0, t1)) for block in chunks(plan.symbols)]
    parts = [part for part in parts if len(part)]
    rows = pd.concat(parts, ignore_index=True) if parts else empty_rows()
    rows = rows.sort_values(["ts", "strike", "right"], kind="mergesort").reset_index(drop=True)
    check_session_rows(rows, plan.date)
    return rows


def client_version():
    try:
        return importlib_metadata.version("databento")
    except importlib_metadata.PackageNotFoundError:
        return "unavailable"


def run_download(api, sessions, start, end, max_usd, ext_dir=EXT_DIR, version=None, now=None):
    """Estimate, enforce the cost guard, download what is not cached, write shards and manifest, validate.
    Returns the Validation. Raises BudgetExceeded BEFORE any get_range call."""
    est = estimate(api, sessions, start, end)
    print_estimate(est)
    enforce_budget(est.total_usd, max_usd)
    todo = est.fetch_plans()
    if not todo:
        raise RuntimeError("no session to fetch (all excluded by the vendor, pending or nothing listed); "
                           "no manifest written")
    os.makedirs(os.path.join(ext_dir, CACHE_SUBDIR), exist_ok=True)
    for p in todo:
        path = cache_path(ext_dir, p.date)
        if os.path.exists(path):
            print(f"{p.date}  cached, skipped", flush=True)
            continue
        rows = fetch_session(api, p)
        write_csv(rows, path)
        print(f"{p.date}  downloaded {len(rows):,} rows from {len(p.symbols)} symbols", flush=True)
    by_month = {}
    for p in todo:
        by_month.setdefault(p.date[:7], []).append(p.date)
    shards, kept, empty = {}, [], []
    for month in sorted(by_month):                      # one month of rows in memory at a time
        frames = []
        for day in by_month[month]:
            rows = read_rows(cache_path(ext_dir, day))
            check_session_rows(rows, day)
            if len(rows):
                frames.append(rows)
                kept.append(day)
            else:
                empty.append(day)
        if frames:
            shards.update(write_shards(pd.concat(frames, ignore_index=True), ext_dir))
    for day in empty:
        print(f"WARNING {day}: the vendor returned no rows; the session is listed in no_data_sessions, not excluded "
              f"(delete {cache_path(ext_dir, day)} to ask again)", file=sys.stderr, flush=True)
    if not shards:
        raise RuntimeError("every fetched session was empty; no manifest written")
    fetched_at = (now or dt.datetime.now(dt.timezone.utc)).strftime("%Y-%m-%dT%H:%M:%SZ")
    manifest = build_manifest((start, end), len(kept), [p.date for p in est.excluded_plans()],
                              [p.date for p in est.no_data_plans()] + empty, est.unresolved, shards, fetched_at,
                              version or client_version(), est.total_usd)
    print(f"wrote {write_manifest(manifest, ext_dir)}", flush=True)
    v = validate(ext_dir)
    print_validation(v)
    return v


def make_client():
    """The one place the vendor SDK is imported (lazily, so --validate-only and the pure functions need no SDK).
    The key comes from DATABENTO_API_KEY only; it is never read from the command line and never printed."""
    if not os.environ.get("DATABENTO_API_KEY", "").strip():
        raise SystemExit("DATABENTO_API_KEY is not set in the environment (the key is read from the environment only)")
    try:
        import databento
    except ImportError:
        raise SystemExit("the databento package is not installed: python -m venv .venv-quotes && "
                         ".venv-quotes/bin/pip install databento==0.87.0, then run this tool with "
                         ".venv-quotes/bin/python") from None
    return databento.Historical(key=None)


def convert_dbn_file(path, out):
    """--from-dbn: a local DBN file -> the vendor-neutral rows, through the exact path --download uses."""
    import databento
    with open(path, "rb") as f:                         # from_bytes: no file handle is left open by the store
        rows = dbn_store_rows(databento.DBNStore.from_bytes(f))
    write_csv(rows, out)
    return len(rows)


# ----------------------------------------------------------------------------------------------------------------
# CLI
# ----------------------------------------------------------------------------------------------------------------
def build_parser():
    ap = argparse.ArgumentParser(prog="fetch_spy_0dte_quotes.py", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--estimate", action="store_true",
                      help="price the request with metadata calls only; downloads nothing")
    mode.add_argument("--download", action="store_true",
                      help="estimate, enforce --max-usd, download, write shards + manifest, validate")
    mode.add_argument("--from-dbn", metavar="FILE",
                      help="offline: convert a local DBN file to vendor-neutral rows (needs --out)")
    mode.add_argument("--validate-only", action="store_true",
                      help="offline: validate the manifest and shards under --ext-dir")
    ap.add_argument("--start", default=None,
                    help=f"first session, YYYY-MM-DD (default {WINDOW_START}; estimate/download)")
    ap.add_argument("--end", default=None, help=f"last session, YYYY-MM-DD (default {WINDOW_END}; estimate/download)")
    ap.add_argument("--max-usd", type=float, default=None,
                    help="the cost guard: abort if the estimated total exceeds this (--download, required)")
    ap.add_argument("--out", metavar="FILE", default=None, help="output CSV (.csv.gz is gzipped) for --from-dbn")
    ap.add_argument("--ext-dir", default=EXT_DIR, help="the data/ext directory (default: this repository's)")
    return ap


def main(argv=None):
    ap = build_parser()
    a = ap.parse_args(argv)
    if a.download:
        if a.max_usd is None or not math.isfinite(a.max_usd) or a.max_usd < 0:
            ap.error("--download requires --max-usd X (a finite, non-negative budget in USD)")
    elif a.max_usd is not None:
        ap.error("--max-usd applies to --download only")
    if a.from_dbn:
        if not a.out:
            ap.error("--from-dbn requires --out FILE")
    elif a.out:
        ap.error("--out applies to --from-dbn only")
    if (a.validate_only or a.from_dbn) and (a.start or a.end):
        ap.error("--start/--end apply to --estimate and --download only")
    start, end = a.start or WINDOW_START, a.end or WINDOW_END
    try:
        dt.date.fromisoformat(start), dt.date.fromisoformat(end)
    except ValueError:
        ap.error("--start/--end must be YYYY-MM-DD")
    if start > end:
        ap.error("--start is after --end")

    if a.validate_only:
        v = validate(a.ext_dir)
        print_validation(v)
        return 0 if v.ok else 1
    if a.from_dbn:
        n = convert_dbn_file(a.from_dbn, a.out)
        print(f"wrote {a.out}: {n:,} rows")
        return 0
    try:
        sessions = load_sessions(a.ext_dir, start, end)
    except FileNotFoundError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1
    if not sessions:
        print(f"no sessions between {start} and {end} in {os.path.join(a.ext_dir, MINUTE_FILE)}", file=sys.stderr)
        return 1
    api = Api(make_client())
    if a.estimate:
        print_estimate(estimate(api, sessions, start, end))
        return 0
    try:
        v = run_download(api, sessions, start, end, a.max_usd, a.ext_dir)
    except BudgetExceeded as e:
        print(f"ABORT: {e}", file=sys.stderr)
        return 3
    return 0 if v.ok else 1


if __name__ == "__main__":
    sys.exit(main())
