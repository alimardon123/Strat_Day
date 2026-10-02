"""Tests for tools/fetch_spy_0dte_quotes.py (the A51 quote acquisition tool). Plain asserts, pytest-collectable, NO
network: every vendor call goes to a recording double, and the tests that drive the real databento client patch
`requests` so that no socket is ever opened (an autouse fixture also blocks sockets and clears the API key).

    <venv with databento>/bin/python -m pytest tools/test_fetch_spy_0dte_quotes.py -q -p no:cacheprovider
    python3 -m pytest tools/test_fetch_spy_0dte_quotes.py -q -p no:cacheprovider    # databento tests skip

Index (spec letters from the task, then added checks):
  (a) test_osi_builder_*            (b) test_osi_parser_*            (c) test_real_fixture_*
  (d) test_band_*                   (e) test_cost_guard_*            (f) test_client_calls_*, test_wire_*
  (g) test_shards_*, test_manifest_* (h) test_validator_*            (i) test_resumable_cache_*
  (j) test_retry_*  (k) test_estimate_*  (l) test_session_*  (m) test_convert_*  (n) test_download_*  (o) misc
"""
import datetime as dt
import gzip
import hashlib
import inspect
import json
import os
import shutil
import socket
import subprocess
import sys
import types

import numpy as np
import pandas as pd
import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import fetch_spy_0dte_quotes as fsq  # noqa: E402

REPO = os.path.dirname(HERE)
FIXTURE = os.path.join(HERE, "fixtures", "opra_cbbo1m_sample.dbn.zst")
NY = "America/New_York"
# three sessions across the 2026-03-08 DST change; bands from band_bounds: (651, 706), (652, 708), (662, 719)
DAYS3 = {"2026-03-02": 678.73, "2026-03-03": 680.0, "2026-03-09": 690.5}


@pytest.fixture(autouse=True)
def _offline(monkeypatch):
    monkeypatch.delenv("DATABENTO_API_KEY", raising=False)

    def blocked(*a, **k):
        raise AssertionError("a test tried to use the network")

    monkeypatch.setattr(socket.socket, "connect", blocked)
    monkeypatch.setattr(socket, "create_connection", blocked)
    monkeypatch.setattr(socket, "getaddrinfo", blocked)


def test_the_network_is_blocked_in_this_suite():
    with pytest.raises(AssertionError, match="network"):
        socket.create_connection(("hist.databento.com", 443), timeout=1)
    s = socket.socket()
    try:
        with pytest.raises(AssertionError, match="network"):
            s.connect(("127.0.0.1", 9))
    finally:
        s.close()
    with pytest.raises(AssertionError, match="network"):
        socket.getaddrinfo("hist.databento.com", 443)


def nosleep(_seconds):
    pass


class Sleeps(list):
    def __call__(self, seconds):
        self.append(seconds)


class HttpErr(Exception):
    """Duck-typed stand-in for databento's BentoHttpError: an http_status and the response headers."""

    def __init__(self, status, headers=None):
        super().__init__(f"HTTP {status}")
        self.http_status, self.headers = status, headers or {}


# ----------------------------------------------------------------------------------------------------------------
# builders: a tiny canonical minute file, vendor-shaped frames, a recording vendor double, valid quote rows
# ----------------------------------------------------------------------------------------------------------------
def utc(day, hhmm):
    return pd.Timestamp(f"{day} {hhmm}", tz=NY).tz_convert("UTC").strftime("%Y-%m-%d %H:%M:%S")


def minute_bars(day, price, first="09:30", nbars=5):
    """A pre-market bar and an after-hours bar (traps: neither is the 09:30 price) around `nbars` regular bars."""
    rows = []

    def add(hhmm, op):
        rows.append((utc(day, hhmm), op, op + 0.1, op - 0.1, op + 0.05, 100))

    add("08:00", price + 50)
    h, m = (int(x) for x in first.split(":"))
    for i in range(nbars):
        mm = h * 60 + m + i
        add(f"{mm // 60:02d}:{mm % 60:02d}", price + 0.01 * i)
    add("17:00", price - 50)
    return rows


def make_ext(root, days):
    """<root>/ext with a canonical-format minute file. days = {date: price or (price, first regular bar 'HH:MM')}."""
    ext = os.path.join(str(root), "ext")
    os.makedirs(ext, exist_ok=True)
    rows = []
    for day, spec in days.items():
        price, first = spec if isinstance(spec, tuple) else (spec, "09:30")
        rows += minute_bars(day, price, first)
    df = pd.DataFrame(rows, columns=["ts", "open", "high", "low", "close", "volume"]).sort_values("ts")
    df.to_csv(os.path.join(ext, fsq.MINUTE_FILE), index=False, compression="gzip")
    return ext


def vendor_frame(records):
    """records: [(ts_recv 'YYYY-MM-DD HH:MM:SS' UTC, OSI symbol, bid, ask, bid_sz, ask_sz)] -> a frame shaped like
    DBNStore.to_df() for cbbo-1m: index ts_recv (tz-aware UTC, ns), float prices, uint32 sizes, a `symbol` column."""
    n = len(records)
    ts = pd.DatetimeIndex(pd.to_datetime([r[0] for r in records], utc=True), name="ts_recv")
    ts = ts.astype("datetime64[ns, UTC]")
    df = pd.DataFrame({
        "ts_event": (ts - pd.Timedelta(seconds=37)),   # deliberately different from ts_recv
        "rtype": np.full(n, 193, dtype="uint8"),
        "publisher_id": np.full(n, 30, dtype="uint16"),
        "instrument_id": np.arange(n, dtype="uint32"),
        "side": ["N"] * n,
        "price": np.array([r[3] for r in records], dtype=float),
        "size": np.ones(n, dtype="uint32"),
        "flags": np.full(n, 194, dtype="uint8"),
        "bid_px_00": np.array([r[2] for r in records], dtype=float),
        "ask_px_00": np.array([r[3] for r in records], dtype=float),
        "bid_sz_00": np.array([r[4] for r in records], dtype="uint32"),
        "ask_sz_00": np.array([r[5] for r in records], dtype="uint32"),
        "symbol": [r[1] for r in records]})
    df.index = ts
    return df


class FakeStore:
    def __init__(self, df):
        self.df, self.to_df_kwargs = df, None

    def to_df(self, **kwargs):
        self.to_df_kwargs = kwargs
        return self.df.copy()


def _day_of(kwargs):
    return kwargs["start"].tz_convert(NY).strftime("%Y-%m-%d")


class FakeClient:
    """Test double for databento.Historical: records every call as (name, args, kwargs), serves canned metadata and
    deterministic quotes (3 minutes per symbol from 09:31 ET), can raise queued errors. Never touches a socket."""

    def __init__(self, cost=10.0, size=1_000_000, conditions=None, omit_dates=(), unlisted=lambda sym: False,
                 rows_per_symbol=3, quote=lambda sym, i: (1.00, 1.05), errors=None, empty_days=(), shift_expiry=False,
                 resolve_style="empty", dup_rows=False, only=lambda sym: True):
        self.cost, self.size = cost, size
        self.conditions, self.omit_dates, self.unlisted = conditions or {}, set(omit_dates), unlisted
        self.rows_per_symbol, self.quote, self.errors = rows_per_symbol, quote, errors or {}
        self.empty_days, self.shift_expiry, self.resolve_style = set(empty_days), shift_expiry, resolve_style
        self.dup_rows, self.only = dup_rows, only
        self.calls, self.stores = [], []
        self.metadata = types.SimpleNamespace(get_cost=self.get_cost, get_billable_size=self.get_billable_size,
                                              get_dataset_condition=self.get_dataset_condition)
        self.symbology = types.SimpleNamespace(resolve=self.resolve)
        self.timeseries = types.SimpleNamespace(get_range=self.get_range)

    def of(self, name):
        return [(a, k) for n, a, k in self.calls if n == name]

    def _record(self, name, args, kwargs):
        self.calls.append((name, args, kwargs))
        queued = self.errors.get(name)
        if queued:
            raise queued.pop(0)

    def get_cost(self, *args, **kwargs):
        self._record("get_cost", args, kwargs)
        return self.cost(kwargs) if callable(self.cost) else self.cost

    def get_billable_size(self, *args, **kwargs):
        self._record("get_billable_size", args, kwargs)
        return self.size(kwargs) if callable(self.size) else self.size

    def get_dataset_condition(self, *args, **kwargs):
        self._record("get_dataset_condition", args, kwargs)
        days = pd.date_range(kwargs["start_date"], kwargs["end_date"]).strftime("%Y-%m-%d")   # end inclusive
        return [{"date": d, "condition": self.conditions.get(d, "available"), "last_modified_date": d}
                for d in days if d not in self.omit_dates]

    def resolve(self, *args, **kwargs):
        self._record("resolve", args, kwargs)
        mapping = [{"d0": kwargs["start_date"], "d1": kwargs["end_date"], "s": "1"}]
        gone = [s for s in kwargs["symbols"] if self.unlisted(s)]
        result = {s: mapping for s in kwargs["symbols"] if s not in gone}
        if self.resolve_style == "empty":                    # an unresolved symbol may also come back as an empty list
            result.update({s: [] for s in gone})
        return {"result": result, "symbols": list(kwargs["symbols"]), "partial": [], "not_found": gone,
                "message": "OK", "status": 0}

    def get_range(self, *args, **kwargs):
        self._record("get_range", args, kwargs)
        day = _day_of(kwargs)
        recs = []
        if day not in self.empty_days:
            t0 = pd.Timestamp(f"{day} 09:31:00", tz=NY).tz_convert("UTC")
            for sym in kwargs["symbols"]:
                if not self.only(sym):                       # a block of symbols the vendor has no records for
                    continue
                shown = sym
                if self.shift_expiry:    # a vendor bug: the contract's expiry is not the session's date
                    shown = sym[:6] + (pd.Timestamp(day) + pd.Timedelta(days=1)).strftime("%y%m%d") + sym[12:]
                for i in range(self.rows_per_symbol):
                    bid, ask = self.quote(sym, i)
                    recs.append(((t0 + pd.Timedelta(minutes=i)).strftime("%Y-%m-%d %H:%M:%S"), shown, bid, ask, 10, 12))
        if self.dup_rows and recs:                           # a vendor bug: one record delivered twice
            recs = recs + recs[:1]
        store = FakeStore(vendor_frame(recs))
        self.stores.append(store)
        return store


def quote_rows(days, strikes=(678, 679, 680), minutes=3, bid=1.0, ask=1.05):
    """Valid vendor-neutral rows for each session: every strike, both rights, `minutes` minutes from 09:31 ET."""
    recs = []
    for day in days:
        for i in range(minutes):
            ts = (pd.Timestamp(f"{day} 09:31:00", tz=NY).tz_convert("UTC") + pd.Timedelta(minutes=i)
                  ).strftime("%Y-%m-%d %H:%M:%S")
            for k in strikes:
                for right in "CP":
                    recs.append((ts, day, float(k), right, bid, ask, 10, 12))
    return pd.DataFrame(recs, columns=fsq.COLS)


def install(ext, rows, window=("2026-03-02", "2026-03-09"), excluded=(), no_data=(), n_sessions=None, **overrides):
    """Write `rows` as shards plus a manifest that matches them, so a test corrupts exactly one thing."""
    shards = fsq.write_shards(rows, ext)
    n = rows["expiry"].nunique() if n_sessions is None else n_sessions
    man = fsq.build_manifest(window, n, list(excluded), list(no_data), 0, shards, "2026-10-05T12:00:00Z", "0.87.0",
                             10.0)
    man.update(overrides)
    fsq.write_manifest(man, ext)
    return man


def clean_ext(root):
    ext = make_ext(root, DAYS3)
    man = install(ext, quote_rows(DAYS3))
    return ext, man


def failures(ext):
    return fsq.validate(ext).failures


def assert_fails_with(ext, *needles):
    got = failures(ext)
    assert got, "the validator accepted a corrupted dataset"
    for needle in needles:
        assert any(needle in f for f in got), f"no failure mentions {needle!r}: {got}"


def run_dl(ext, client, days=DAYS3, max_usd=1e9, **kw):
    start, end = min(days), max(days)
    sessions = fsq.load_sessions(ext, start, end)
    api = fsq.Api(client, sleep=kw.pop("sleep", nosleep))
    return fsq.run_download(api, sessions, start, end, max_usd, ext_dir=ext, version="test", **kw)


# ----------------------------------------------------------------------------------------------------------------
# (a) OSI builder
# ----------------------------------------------------------------------------------------------------------------
def test_osi_builder_gives_exact_21_char_strings():
    s = fsq.osi_symbol("2024-02-01", "C", 480)
    assert s == "SPY   240201C00480000" and len(s) == 21
    assert fsq.osi_symbol("2024-02-01", "P", 481.0) == "SPY   240201P00481000"
    assert fsq.osi_symbol(dt.date(2026, 3, 2), "c", 678) == "SPY   260302C00678000"   # date object, lower-case right
    assert fsq.osi_symbol("2024-02-01", "C", 1234.5, root="QQQ") == "QQQ   240201C01234500"
    assert fsq.osi_symbol("2024-02-01", "C", 99999.999) == "SPY   240201C99999999"


def test_osi_builder_fractional_strikes():
    assert fsq.osi_symbol("2024-02-01", "C", 480.5) == "SPY   240201C00480500"
    assert fsq.osi_symbol("2024-02-01", "C", 0.5) == "SPY   240201C00000500"
    # 128.01 * 1000 == 128009.99999999999 in binary floating point: truncating instead of rounding gives ...128009
    assert 128.01 * 1000 < 128010
    assert fsq.osi_symbol("2024-02-01", "P", 128.01) == "SPY   240201P00128010"
    assert fsq.osi_symbol("2024-02-01", "P", 2.01) == "SPY   240201P00002010"


@pytest.mark.parametrize("args", [
    ("2024-02-01", "X", 480), ("2024-02-01", "C", 480.0004), ("2024-02-01", "C", 0), ("2024-02-01", "C", -1),
    ("2024-02-01", "C", 100000), ("2124-02-01", "C", 480), ("2024-02-30", "C", 480)])
def test_osi_builder_rejects_unrepresentable_input(args):
    with pytest.raises(ValueError):
        fsq.osi_symbol(*args)


def test_osi_builder_rejects_a_bad_root():
    for root in ("", "SPYXYZW", "SPY "):
        with pytest.raises(ValueError):
            fsq.osi_symbol("2024-02-01", "C", 480, root=root)


# ----------------------------------------------------------------------------------------------------------------
# (b) OSI parser
# ----------------------------------------------------------------------------------------------------------------
def test_osi_parser_round_trips():
    for root in ("SPY", "A", "AAPL", "BRKB"):
        for day in ("2000-01-01", "2024-02-01", "2026-12-31"):
            for right in "CP":
                for strike in (0.5, 1.0, 2.01, 128.01, 480.0, 480.5, 678.0, 1234.567, 99999.999):
                    sym = fsq.osi_symbol(day, right, strike, root=root)
                    assert len(sym) == 21
                    assert fsq.parse_osi(sym) == fsq.Osi(root, day, right, strike), sym


def test_osi_parser_reads_the_vendor_symbol():
    assert fsq.parse_osi("AAPL  250221C00250000") == ("AAPL", "2025-02-21", "C", 250.0)
    assert fsq.parse_osi("SPY   260302P00678500") == ("SPY", "2026-03-02", "P", 678.5)


@pytest.mark.parametrize("bad", [
    "SPY   240201C0048000", "SPY   240201C004800000", "SPY240201C00480000", "SPY   240201c00480000",
    "SPY   241301C00480000", "SPY   240230C00480000", "SPY   240201X00480000", "SPY   240201C0048000A", "", None, 480])
def test_osi_parser_rejects_malformed_symbols(bad):
    with pytest.raises(ValueError):
        fsq.parse_osi(bad)


# ----------------------------------------------------------------------------------------------------------------
# (c) the REAL vendor sample (needs databento: skipped under a Python without it)
# ----------------------------------------------------------------------------------------------------------------
EXPECTED_FIXTURE_CSV = (
    "ts,expiry,strike,right,bid,ask,bid_size,ask_size\n"
    "2025-02-20 13:01:00,2025-02-21,250.0,C,,,0,0\n"
    "2025-02-20 14:31:00,2025-02-21,250.0,C,0.32,0.34,104,132\n"
    "2025-02-20 14:32:00,2025-02-21,250.0,C,0.43,0.45,1,135\n"
    "2025-02-20 14:33:00,2025-02-21,250.0,C,0.34,0.36,62,79\n")


def test_fixture_is_the_untouched_vendor_sample():
    with open(FIXTURE, "rb") as f:
        digest = hashlib.sha256(f.read()).hexdigest()
    assert digest == "37a2b051710227e0cd9e5a2798b6b177ed525d4ac9e48028c01c898030547d8a"
    with open(os.path.join(HERE, "fixtures", "README.md")) as f:
        readme = f.read()
    assert "databento-python" in readme and "37a2b051710227e0cd9e5a2798b6b177ed525d4ac9e48028c01c898030547d8a" in readme


def test_real_fixture_converts_to_the_expected_rows():
    db = pytest.importorskip("databento")
    with open(FIXTURE, "rb") as f:
        rows = fsq.dbn_store_rows(db.DBNStore.from_bytes(f.read()))
    assert list(rows.columns) == fsq.COLS
    # the sample has 4 records: the empty book at 13:01 and three priced minutes
    assert rows["ts"].tolist() == ["2025-02-20 13:01:00", "2025-02-20 14:31:00", "2025-02-20 14:32:00",
                                   "2025-02-20 14:33:00"]
    assert set(rows["expiry"]) == {"2025-02-21"} and set(rows["right"]) == {"C"} and set(rows["strike"]) == {250.0}
    assert np.isnan(rows.loc[0, "bid"]) and np.isnan(rows.loc[0, "ask"])               # empty book is KEPT, NaN
    assert rows.loc[1:, "bid"].tolist() == [0.32, 0.43, 0.34] and rows.loc[1:, "ask"].tolist() == [0.34, 0.45, 0.36]
    assert rows["bid_size"].tolist() == [0, 104, 1, 62] and rows["ask_size"].tolist() == [0, 132, 135, 79]
    assert rows["bid_size"].dtype == np.int64 and rows["strike"].dtype == np.float64
    # ts_recv, not ts_event: ts_event is 14:30:59.895648 for the first priced record and undefined for the empty book
    assert (pd.to_datetime(rows["ts"]).dt.second == 0).all()


def test_real_fixture_cli_writes_exact_csv_text(tmp_path):
    pytest.importorskip("databento")
    out = str(tmp_path / "rows.csv")
    assert fsq.main(["--from-dbn", FIXTURE, "--out", out]) == 0
    with open(out) as f:
        assert f.read() == EXPECTED_FIXTURE_CSV
    gz = str(tmp_path / "rows.csv.gz")
    assert fsq.main(["--from-dbn", FIXTURE, "--out", gz]) == 0
    with gzip.open(gz, "rt") as f:
        assert f.read() == EXPECTED_FIXTURE_CSV


def test_real_empty_store_converts_to_no_rows():
    db = pytest.importorskip("databento")
    zstandard = pytest.importorskip("zstandard")
    import io
    with open(FIXTURE, "rb") as f:
        raw = zstandard.ZstdDecompressor().stream_reader(f).read()
    header_only = raw[:8 + int.from_bytes(raw[4:8], "little")]          # DBN metadata block, zero records
    rows = fsq.dbn_store_rows(db.DBNStore.from_bytes(io.BytesIO(header_only)))
    assert len(rows) == 0 and list(rows.columns) == fsq.COLS


# ----------------------------------------------------------------------------------------------------------------
# (d) band strikes
# ----------------------------------------------------------------------------------------------------------------
def test_band_strikes_are_exactly_the_integer_range():
    assert fsq.band_bounds(700.0) == (672, 728)                     # 0.96 * 700 and 1.04 * 700 are integers
    assert fsq.band_strikes(700.0) == list(range(672, 729)) and len(fsq.band_strikes(700.0)) == 57
    assert fsq.band_bounds(755.56) == (725, 786)                    # 725.3376 floors, 785.7824 ceils
    assert fsq.band_bounds(678.73) == (651, 706)                    # 651.5808 floors, 705.8792 ceils
    assert fsq.band_bounds(625.0) == (600, 650)                     # integer edges stay
    assert fsq.band_bounds(625.01) == (600, 651)                    # 650.0104 ceils up
    assert fsq.band_bounds(624.99) == (599, 650)                    # 599.9904 floors down
    assert fsq.band_bounds(700.0, 3.0) == (679, 721)


def test_candidate_symbols_are_both_rights_of_every_band_strike():
    c = fsq.candidate_symbols("2026-03-02", 700.0)
    assert len(c) == 114 and len(set(c)) == 114
    assert c[:2] == ["SPY   260302C00672000", "SPY   260302P00672000"]
    assert c[-2:] == ["SPY   260302C00728000", "SPY   260302P00728000"]
    parsed = [fsq.parse_osi(s) for s in c]
    assert {p.expiry for p in parsed} == {"2026-03-02"} and {p.right for p in parsed} == {"C", "P"}
    assert sorted({p.strike for p in parsed}) == [float(k) for k in range(672, 729)]


# ----------------------------------------------------------------------------------------------------------------
# (e) the cost guard
# ----------------------------------------------------------------------------------------------------------------
def test_cost_guard_aborts_before_any_get_range_and_writes_nothing(tmp_path):
    ext = make_ext(tmp_path, DAYS3)
    client = FakeClient(cost=60.0)                                   # 3 sessions x 60 = 180
    with pytest.raises(fsq.BudgetExceeded):
        run_dl(ext, client, max_usd=179.99)
    assert client.of("get_range") == []
    assert len(client.of("get_cost")) == 3                           # it did price the sessions first
    assert not os.path.exists(os.path.join(ext, fsq.CACHE_SUBDIR))
    assert not os.path.exists(os.path.join(ext, fsq.MANIFEST_FILE))
    assert [n for n in os.listdir(ext) if n.startswith(fsq.SHARD_PREFIX)] == []


def test_cost_guard_allows_a_total_equal_to_the_budget(tmp_path):
    ext = make_ext(tmp_path, DAYS3)
    client = FakeClient(cost=60.0)
    assert run_dl(ext, client, max_usd=180.0).ok                     # equal is not "exceeds"
    assert len(client.of("get_range")) == 3


def test_enforce_budget_boundary():
    fsq.enforce_budget(12.5, 12.5)
    fsq.enforce_budget(0.0, 0.0)
    with pytest.raises(fsq.BudgetExceeded):
        fsq.enforce_budget(12.500001, 12.5)


def test_cost_guard_through_the_cli_exits_3_without_get_range(tmp_path, monkeypatch, capsys):
    ext = make_ext(tmp_path, DAYS3)
    client = FakeClient(cost=60.0)
    monkeypatch.setattr(fsq, "make_client", lambda: client)
    argv = ["--download", "--start", "2026-03-02", "--end", "2026-03-09", "--ext-dir", ext]
    assert fsq.main(argv + ["--max-usd", "100"]) == 3
    assert client.of("get_range") == []
    assert "ABORT" in capsys.readouterr().err
    assert fsq.main(argv + ["--max-usd", "180"]) == 0
    assert len(client.of("get_range")) == 3


# ----------------------------------------------------------------------------------------------------------------
# (f) every vendor call: keyword-only, tz-aware, end = 16:00:01 ET
# ----------------------------------------------------------------------------------------------------------------
def test_client_calls_are_keyword_only_and_end_at_160001_et(tmp_path):
    ext = make_ext(tmp_path, DAYS3)
    client = FakeClient()
    assert run_dl(ext, client).ok
    names = {n for n, _, _ in client.calls}
    assert names == {"get_dataset_condition", "resolve", "get_cost", "get_billable_size", "get_range"}
    for name, args, kwargs in client.calls:
        assert args == (), f"{name} was called with positional arguments {args}"
    expected_end = {"2026-03-02": "2026-03-02T16:00:01-05:00", "2026-03-03": "2026-03-03T16:00:01-05:00",
                    "2026-03-09": "2026-03-09T16:00:01-04:00"}          # EST, EST, then EDT after 2026-03-08
    expected_start = {d: e.replace("T16:00:01", "T09:30:00") for d, e in expected_end.items()}
    for name in ("get_cost", "get_billable_size", "get_range"):
        calls = client.of(name)
        assert len(calls) == 3
        for _, kw in calls:
            day = _day_of(kw)
            assert kw["end"].tzinfo is not None and kw["start"].tzinfo is not None      # never naive
            assert kw["end"] == pd.Timestamp(f"{day} 16:00:01", tz=NY)
            assert kw["end"].isoformat() == expected_end[day]
            assert kw["start"].isoformat() == expected_start[day]
            assert kw["dataset"] == "OPRA.PILLAR" and kw["schema"] == "cbbo-1m" and kw["stype_in"] == "raw_symbol"
            assert 0 < len(kw["symbols"]) <= 2000 and set(kw) >= {"dataset", "start", "end", "symbols", "schema"}
    for _, kw in client.of("get_range"):
        assert "path" not in kw                                           # get_range's path= is not retry-safe
    for _, kw in client.of("resolve"):
        assert kw["stype_in"] == "raw_symbol" and kw["stype_out"] == "instrument_id"
        d = dt.date.fromisoformat(kw["start_date"])
        assert kw["end_date"] == (d + dt.timedelta(days=1)).isoformat()
    (_, cond), = client.of("get_dataset_condition")
    assert cond == {"dataset": "OPRA.PILLAR", "start_date": "2026-03-02", "end_date": "2026-03-09"}
    assert all(s.to_df_kwargs == {"price_type": "float", "pretty_ts": True, "map_symbols": True}
               for s in client.stores)


def test_client_calls_bind_to_the_real_sdk_signatures(tmp_path):
    """The double accepts anything, so bind every recorded call to the INSTALLED databento signatures: an unknown or
    misspelt keyword raises TypeError; get_cost's 4th positional parameter is the deprecated `mode` (the trap)."""
    pytest.importorskip("databento")
    from databento.historical.api.metadata import MetadataHttpAPI
    from databento.historical.api.symbology import SymbologyHttpAPI
    from databento.historical.api.timeseries import TimeseriesHttpAPI
    params = list(inspect.signature(MetadataHttpAPI.get_cost).parameters)
    assert params[:5] == ["self", "dataset", "start", "end", "mode"]
    real = {"get_cost": MetadataHttpAPI.get_cost, "get_billable_size": MetadataHttpAPI.get_billable_size,
            "get_dataset_condition": MetadataHttpAPI.get_dataset_condition, "resolve": SymbologyHttpAPI.resolve,
            "get_range": TimeseriesHttpAPI.get_range}
    ext = make_ext(tmp_path, DAYS3)
    client = FakeClient()
    run_dl(ext, client)
    for name, args, kwargs in client.calls:
        inspect.signature(real[name]).bind(None, **kwargs)
        assert "mode" not in kwargs


class _Resp:
    """Just enough of requests.Response for databento's HTTP layer."""

    def __init__(self, payload=None, content=b"", status=200, headers=None):
        self.payload, self.content, self.status_code, self.headers = payload, content, status, headers or {}

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def json(self):
        return self.payload

    def iter_content(self, chunk_size=None):
        yield self.content


def _wire(monkeypatch, handler):
    """Patch requests.post/get under the REAL databento client; `handler(method, name, data_or_params)` answers."""
    import requests
    sent = []

    def post(url, data=None, params=None, headers=None, auth=None, timeout=None, stream=None):
        sent.append(("POST", url.rsplit("/", 1)[-1], dict(data or {})))
        return handler("POST", sent[-1][1], sent[-1][2])

    def get(url, params=None, headers=None, auth=None, timeout=None):
        sent.append(("GET", url.rsplit("/", 1)[-1], list(params or [])))
        return handler("GET", sent[-1][1], sent[-1][2])

    monkeypatch.setattr(requests, "post", post)
    monkeypatch.setattr(requests, "get", get)
    return sent


def test_wire_payloads_of_the_real_client_are_what_a51_needs(monkeypatch):
    """Drive the REAL databento client (requests patched, so no socket) and assert the exact request bodies: a
    positional get_cost would send schema 'trades' and symbols 'CBBO-1M'; a wrong end would not be 16:00:01."""
    db = pytest.importorskip("databento")
    with open(FIXTURE, "rb") as f:
        dbn_bytes = f.read()
    sym = fsq.osi_symbol("2026-03-02", "C", 680)

    def handler(method, name, payload):
        if name == "timeseries.get_range":
            return _Resp(content=dbn_bytes)
        if name == "metadata.get_cost":
            return _Resp(payload=1.25)
        if name == "metadata.get_billable_size":
            return _Resp(payload=4096)
        if name == "symbology.resolve":
            return _Resp(payload={"result": {sym: [{"d0": "2026-03-02", "d1": "2026-03-03", "s": "7"}]}, "partial": [],
                                  "not_found": [fsq.osi_symbol("2026-03-02", "P", 680)]})
        if name == "metadata.get_dataset_condition":
            return _Resp(payload=[{"date": "2026-03-02", "condition": "degraded", "last_modified_date": "2026-03-03"}])
        raise AssertionError(f"unexpected endpoint {name}")

    sent = _wire(monkeypatch, handler)
    api = fsq.Api(db.Historical(key="db-" + "x" * 29), sleep=nosleep)        # a dummy string; nothing is sent anywhere
    t0, t1 = fsq.session_window("2026-03-02")
    assert api.conditions("2026-03-02", "2026-03-02") == {"2026-03-02": "degraded"}
    assert api.resolve([sym, fsq.osi_symbol("2026-03-02", "P", 680)], "2026-03-02") == [sym]
    assert api.cost([sym], t0, t1) == 1.25
    assert api.billable_size([sym], t0, t1) == 4096
    rows = fsq.dbn_store_rows(api.get_range([sym], t0, t1))
    assert len(rows) == 4 and list(rows.columns) == fsq.COLS               # the real DBN bytes decode and convert

    by_name = {name: payload for _, name, payload in sent}
    common = {"dataset": "OPRA.PILLAR", "symbols": sym, "schema": "cbbo-1m", "stype_in": "raw_symbol",
              "start": "2026-03-02T09:30:00-05:00", "end": "2026-03-02T16:00:01-05:00"}
    for name in ("metadata.get_cost", "metadata.get_billable_size", "timeseries.get_range"):
        got = by_name[name]
        assert {k: got[k] for k in common} == common, name
        assert got["stype_out"] == "instrument_id"
    assert by_name["timeseries.get_range"]["encoding"] == "dbn"
    res = by_name["symbology.resolve"]
    assert res["stype_in"] == "raw_symbol" and res["dataset"] == "OPRA.PILLAR"
    assert res["start_date"] == "2026-03-02" and res["end_date"] == "2026-03-03"
    assert ("dataset", "OPRA.PILLAR") in by_name["metadata.get_dataset_condition"]
    assert ("start_date", "2026-03-02") in by_name["metadata.get_dataset_condition"]
    assert ("end_date", "2026-03-02") in by_name["metadata.get_dataset_condition"]


def test_wire_retry_against_the_real_error_classes(monkeypatch):
    """429 with Retry-After and 503 are retried; 401 is not. Uses databento's own BentoClientError/BentoServerError."""
    db = pytest.importorskip("databento")
    answers = [_Resp(payload={"detail": "slow down"}, status=429, headers={"Retry-After": "7"}),
               _Resp(payload={"detail": "upstream"}, status=503),
               _Resp(payload=2.5)]
    _wire(monkeypatch, lambda m, n, p: answers.pop(0))
    sleeps = Sleeps()
    api = fsq.Api(db.Historical(key="db-" + "x" * 29), sleep=sleeps)
    t0, t1 = fsq.session_window("2026-03-02")
    assert api.cost([fsq.osi_symbol("2026-03-02", "C", 680)], t0, t1) == 2.5
    assert sleeps == [7.0, 4.0]                                              # Retry-After 7 > backoff 2; then backoff 4
    answers[:] = [_Resp(payload={"detail": "bad key"}, status=401)]
    sleeps.clear()
    with pytest.raises(db.BentoClientError):
        api.cost([fsq.osi_symbol("2026-03-02", "C", 680)], t0, t1)
    assert sleeps == [] and answers == []                                    # one call, no retry


def test_make_client_needs_the_key_in_the_environment_and_there_is_no_key_option(monkeypatch):
    with pytest.raises(SystemExit) as e:
        fsq.make_client()
    assert "DATABENTO_API_KEY" in str(e.value)
    monkeypatch.setenv("DATABENTO_API_KEY", "   ")
    with pytest.raises(SystemExit):
        fsq.make_client()
    assert not [a for a in fsq.build_parser()._actions if any("key" in o for o in a.option_strings)]


def test_make_client_returns_a_historical_client_from_the_environment(monkeypatch):
    pytest.importorskip("databento")
    monkeypatch.setenv("DATABENTO_API_KEY", "db-" + "s" * 29)
    client = fsq.make_client()
    assert type(client).__name__ == "Historical" and client.key == "db-" + "s" * 29


# ----------------------------------------------------------------------------------------------------------------
# (g) shards and the manifest
# ----------------------------------------------------------------------------------------------------------------
def month_rows():
    days = ["2026-03-31", "2026-03-30", "2026-05-04", "2026-04-01"]           # shuffled: not in time order
    return quote_rows(days, strikes=(680, 679)).sample(frac=1.0, random_state=3).reset_index(drop=True)


def test_shards_split_by_calendar_month_and_manifest_matches_files(tmp_path):
    rows = month_rows()
    shards = fsq.write_shards(rows, str(tmp_path))
    assert sorted(shards) == ["spy_0dte_quotes_1min_2026-03.csv.gz", "spy_0dte_quotes_1min_2026-04.csv.gz",
                              "spy_0dte_quotes_1min_2026-05.csv.gz"]
    assert sorted(os.listdir(tmp_path)) == sorted(shards)                    # nothing else is left behind
    for name, entry in shards.items():
        path = tmp_path / name
        assert entry["sha256"] == hashlib.sha256(path.read_bytes()).hexdigest()
        df = pd.read_csv(path)
        assert list(df.columns) == fsq.COLS and len(df) == entry["rows"]
        assert (df["ts"].str[:7] == name[len(fsq.SHARD_PREFIX):len(fsq.SHARD_PREFIX) + 7]).all()
        assert df.equals(df.sort_values(["ts", "strike", "right"], kind="mergesort").reset_index(drop=True))
    assert shards["spy_0dte_quotes_1min_2026-03.csv.gz"]["rows"] == 2 * 3 * 2 * 2     # two March sessions
    assert shards["spy_0dte_quotes_1min_2026-04.csv.gz"]["rows"] == 3 * 2 * 2
    assert sum(e["rows"] for e in shards.values()) == len(rows)
    man = fsq.build_manifest(("2026-03-02", "2026-09-11"), 4, ["2026-04-02"], [], 7, shards,
                             "2026-10-05T12:00:00Z", "0.87.0", 123.45)
    path = fsq.write_manifest(man, str(tmp_path))
    with open(path) as f:
        back = json.load(f)
    assert back == man
    for name, entry in back["shards"].items():                               # the manifest verifies against the files
        assert fsq.sha256_file(str(tmp_path / name)) == entry["sha256"]
        assert len(pd.read_csv(tmp_path / name)) == entry["rows"]


def test_manifest_declares_what_a51_and_a51a_require():
    man = fsq.build_manifest(("2026-03-02", "2026-09-11"), 131, ["2026-04-03", "2026-03-05"],
                             ["2026-06-09", "2026-06-08"], 12,
                             {"spy_0dte_quotes_1min_2026-03.csv.gz": {"sha256": "ab" * 32, "rows": 10}},
                             "2026-10-05T12:00:00Z", "0.87.0", 99.5)
    assert [k for k in man if k in fsq.MANIFEST_KEYS] == fsq.MANIFEST_KEYS          # every required key, in order
    assert set(man) - set(fsq.MANIFEST_KEYS) == {"no_data_sessions"}               # the one key this tool adds
    assert list(man).index("no_data_sessions") == list(man).index("excluded_sessions") + 1
    assert man["vendor"] == "Databento" and man["dataset"] == "OPRA.PILLAR" and man["schema"] == "cbbo-1m"
    assert man["rows_on_change"] is True and man["band_pct"] == 4.0
    for phrase in ("ts = ts_recv", "end of the vendor's one-minute interval", "instant the consolidated BBO applies",
                   "A51/A51a"):
        assert phrase in man["ts_semantics"]
    assert man["window"] == {"start": "2026-03-02", "end": "2026-09-11"}
    assert man["n_sessions"] == 131 and man["unresolved_symbols"] == 12 and man["cost_estimate_usd"] == 99.5
    assert man["excluded_sessions"] == ["2026-03-05", "2026-04-03"]                   # sorted
    assert man["no_data_sessions"] == ["2026-06-08", "2026-06-09"]
    assert man["fetched_at"] == "2026-10-05T12:00:00Z" and man["client_version"] == "0.87.0"
    assert man["shards"] == {"spy_0dte_quotes_1min_2026-03.csv.gz": {"sha256": "ab" * 32, "rows": 10}}


def test_shard_writer_refuses_a_shard_of_100_mb_or_more(tmp_path, monkeypatch):
    assert fsq.MAX_SHARD_BYTES == 100_000_000
    monkeypatch.setattr(fsq, "MAX_SHARD_BYTES", 50)                          # every gzip shard here is larger
    with pytest.raises(AssertionError, match="under 50"):
        fsq.write_shards(month_rows(), str(tmp_path))
    assert os.listdir(tmp_path) == []                                        # not even a temp file survives
    one = month_rows().iloc[:1]
    monkeypatch.setattr(fsq, "MAX_SHARD_BYTES", 10 ** 6)
    (name, _), = fsq.write_shards(one, str(tmp_path)).items()
    exact = os.path.getsize(tmp_path / name)
    os.remove(tmp_path / name)
    monkeypatch.setattr(fsq, "MAX_SHARD_BYTES", exact)                       # "< limit": exactly the limit fails
    with pytest.raises(AssertionError):
        fsq.write_shards(one, str(tmp_path))
    monkeypatch.setattr(fsq, "MAX_SHARD_BYTES", exact + 1)
    assert fsq.write_shards(one, str(tmp_path))
    monkeypatch.setattr(fsq, "MAX_SHARD_BYTES", 10 ** 7)
    assert fsq.write_shards(month_rows(), str(tmp_path))


def test_gzip_output_is_deterministic(tmp_path):
    rows = month_rows()
    a, b = str(tmp_path / "a.csv.gz"), str(tmp_path / "b.csv.gz")
    fsq.write_csv(rows, a)
    fsq.write_csv(rows, b)
    with open(a, "rb") as fa, open(b, "rb") as fb:
        da, db_ = fa.read(), fb.read()
    assert da == db_
    assert da[4:8] == b"\x00\x00\x00\x00" and not da[3] & 0x08              # mtime 0, no embedded file name
    assert fsq.write_shards(rows, str(tmp_path)) == fsq.write_shards(rows, str(tmp_path))


# ----------------------------------------------------------------------------------------------------------------
# (h) the validator
# ----------------------------------------------------------------------------------------------------------------
def test_validator_accepts_a_clean_dataset(tmp_path, capsys):
    ext, _ = clean_ext(tmp_path)
    v = fsq.validate(ext)
    assert v.ok, v.failures
    assert v.report["rows"] == 3 * 3 * 3 * 2 and v.report["sessions"] == 3 and v.report["shards"] == 1
    assert v.report["crossed"] == v.report["locked"] == v.report["no_quote"] == 0
    fsq.print_validation(v)
    assert "VALID" in capsys.readouterr().out


def test_validator_catches_a_duplicate_row(tmp_path):
    ext = make_ext(tmp_path, DAYS3)
    rows = quote_rows(DAYS3)
    install(ext, pd.concat([rows, rows.iloc[[5]]], ignore_index=True))
    assert_fails_with(ext, "duplicate")
    assert len(failures(ext)) == 1                                           # and nothing else is wrong


def test_validator_catches_a_wrong_expiry(tmp_path):
    ext = make_ext(tmp_path, DAYS3)
    rows = quote_rows(DAYS3)
    rows.loc[4, "expiry"] = "2026-03-04"                                     # a next-day contract
    install(ext, rows)
    assert_fails_with(ext, "expiry != the New York date of ts")


def test_validator_expiry_is_the_new_york_date_not_the_utc_date(tmp_path):
    ext = make_ext(tmp_path, DAYS3)
    late = quote_rows(["2026-03-02"], strikes=(680,), minutes=1)
    late["ts"] = "2026-03-03 00:30:00"                                       # 19:30 ET on 2026-03-02, UTC date 03-03
    install(ext, pd.concat([quote_rows(DAYS3), late], ignore_index=True))
    assert fsq.validate(ext).ok, failures(ext)
    wrong = late.copy()
    wrong["expiry"] = "2026-03-03"                                           # the UTC date: NOT the New York date
    install(ext, pd.concat([quote_rows(DAYS3), wrong], ignore_index=True))
    assert_fails_with(ext, "expiry != the New York date of ts")


def test_validator_catches_a_non_minute_ts(tmp_path):
    ext = make_ext(tmp_path, DAYS3)
    for bad in ("2026-03-02 14:31:30", "2026-03-02T14:31:00", "2026-03-02 14:31", "2026-03-02 14:3x:00"):
        rows = quote_rows(DAYS3)
        rows.loc[0, "ts"] = bad
        install(ext, rows)
        assert_fails_with(ext, "whole minute")


def test_validator_reports_but_does_not_fail_crossed_locked_and_empty_quotes(tmp_path, capsys):
    ext = make_ext(tmp_path, DAYS3)
    rows = quote_rows(DAYS3)
    rows.loc[1, ["bid", "ask"]] = [2.0, 1.0]                                 # crossed: bid > ask
    rows.loc[2, ["bid", "ask"]] = [1.0, 1.0]                                 # locked: bid == ask
    rows.loc[3, ["bid", "ask"]] = [np.nan, np.nan]                           # the vendor's empty book
    rows.loc[4, "bid"] = np.nan                                              # a one-sided book
    install(ext, rows)
    v = fsq.validate(ext)
    assert v.ok, v.failures
    assert (v.report["crossed"], v.report["locked"], v.report["no_quote"]) == (1, 1, 2)
    fsq.print_validation(v)
    out = capsys.readouterr().out
    assert "crossed (bid > ask) 1 rows" in out and "locked (bid == ask) 1 rows" in out and "VALID" in out
    assert "no quote (empty bid or ask) 2 rows" in out


def test_validator_band_edges(tmp_path):
    """Session 2026-03-02 has P = 678.73, so the band is [651, 706]: both edges are in, one dollar further is out."""
    ext = make_ext(tmp_path, DAYS3)
    inside = quote_rows(DAYS3)
    edge = quote_rows(["2026-03-02"], strikes=(651, 706), minutes=1)
    install(ext, pd.concat([inside, edge], ignore_index=True))
    assert fsq.validate(ext).ok
    for strike in (650, 707):
        out = quote_rows(["2026-03-02"], strikes=(strike,), minutes=1)
        install(ext, pd.concat([inside, out], ignore_index=True))
        assert_fails_with(ext, "band")


def test_validator_catches_sha_and_row_count_mismatches(tmp_path):
    ext, man = clean_ext(tmp_path)
    name = next(iter(man["shards"]))
    bad = json.loads(json.dumps(man))
    bad["shards"][name]["sha256"] = "0" * 64
    fsq.write_manifest(bad, ext)
    assert_fails_with(ext, "sha256 mismatch")
    bad = json.loads(json.dumps(man))
    bad["shards"][name]["rows"] += 1
    fsq.write_manifest(bad, ext)
    assert_fails_with(ext, "manifest says")
    with open(os.path.join(ext, name), "ab") as f:                           # a file edited after the manifest
        f.write(b"x")
    fsq.write_manifest(man, ext)
    assert_fails_with(ext, "sha256 mismatch")


def test_validator_needs_the_manifest_and_every_listed_shard(tmp_path):
    ext, man = clean_ext(tmp_path)
    name = next(iter(man["shards"]))
    other = os.path.join(ext, "spy_0dte_quotes_1min_2026-04.csv.gz")
    with open(os.path.join(ext, name), "rb") as f, open(other, "wb") as g:
        g.write(f.read())
    assert_fails_with(ext, "a shard on disk that the manifest does not list")
    os.remove(other)
    os.remove(os.path.join(ext, name))
    assert_fails_with(ext, "missing on disk")
    os.remove(os.path.join(ext, fsq.MANIFEST_FILE))
    assert_fails_with(ext, "quotes_manifest.json missing")


def test_validator_demands_the_exact_columns(tmp_path):
    ext = make_ext(tmp_path, DAYS3)
    rows = quote_rows(DAYS3)
    name = "spy_0dte_quotes_1min_2026-03.csv.gz"
    for cols in (fsq.COLS[::-1], fsq.COLS + ["extra"], fsq.COLS[:-1]):
        with gzip.open(os.path.join(ext, name), "wt", newline="") as f:
            rows.reindex(columns=cols).to_csv(f, index=False)
        man = fsq.build_manifest(("2026-03-02", "2026-03-09"), 3, [], [], 0,
                                 {name: {"sha256": fsq.sha256_file(os.path.join(ext, name)), "rows": len(rows)}},
                                 "2026-10-05T12:00:00Z", "0.87.0", 1.0)
        fsq.write_manifest(man, ext)
        assert any(f.startswith(f"{name}: columns") for f in failures(ext)), failures(ext)


def test_validator_demands_right_c_or_p(tmp_path):
    ext = make_ext(tmp_path, DAYS3)
    rows = quote_rows(DAYS3)
    rows.loc[0, "right"] = "X"
    install(ext, rows)
    assert_fails_with(ext, "right not in")


def test_validator_demands_every_row_be_in_its_shards_month(tmp_path):
    ext = make_ext(tmp_path, DAYS3)
    rows = quote_rows(DAYS3)
    name = "spy_0dte_quotes_1min_2026-04.csv.gz"                             # March rows filed under April
    fsq.write_csv(rows, os.path.join(ext, name))
    man = fsq.build_manifest(("2026-03-02", "2026-03-09"), 3, [], [], 0,
                             {name: {"sha256": fsq.sha256_file(os.path.join(ext, name)), "rows": len(rows)}},
                             "2026-10-05T12:00:00Z", "0.87.0", 1.0)
    fsq.write_manifest(man, ext)
    assert_fails_with(ext, "whose ts is not in 2026-04")


def test_validator_demands_every_window_session_be_present_excluded_or_declared_no_data(tmp_path, capsys):
    ext = make_ext(tmp_path, DAYS3)
    rows = quote_rows(DAYS3)
    short = rows[rows["expiry"] != "2026-03-03"]
    install(ext, short)                                                      # a silent hole
    assert_fails_with(ext, "neither quotes nor an exclusion nor a no-data declaration")
    install(ext, short, excluded=["2026-03-03"])                             # the same hole, declared: vendor-flagged
    assert fsq.validate(ext).ok
    install(ext, short, no_data=["2026-03-03"])                              # ... or declared a no-data gap
    v = fsq.validate(ext)
    assert v.ok and v.report["no_data"] == 1 and v.report["excluded"] == 0
    fsq.print_validation(v)
    assert "1 with no data" in capsys.readouterr().out
    install(ext, rows, n_sessions=2)
    assert_fails_with(ext, "n_sessions")
    install(ext, rows, excluded=["2026-03-02"])
    assert_fails_with(ext, "both in the shards and in excluded_sessions or no_data_sessions")
    install(ext, rows, no_data=["2026-03-02"])
    assert_fails_with(ext, "both in the shards and in excluded_sessions or no_data_sessions")
    install(ext, short, excluded=["2026-03-03"], no_data=["2026-03-03"])
    assert_fails_with(ext, "both in excluded_sessions and no_data_sessions")
    install(ext, short, excluded=["2026-03-03"], no_data=["2026-03-04"])     # 03-04 is not a session of this window
    assert_fails_with(ext, "outside the manifest window")
    install(ext, rows, window=("2026-03-02", "2026-03-03"))                  # quotes outside the declared window
    assert_fails_with(ext, "outside the manifest window")


def test_a_manifest_without_no_data_sessions_is_still_valid_and_a_malformed_one_is_not(tmp_path):
    ext, man = clean_ext(tmp_path)
    bare = {k: v for k, v in man.items() if k != "no_data_sessions"}         # a manifest from another producer
    fsq.write_manifest(bare, ext)
    assert fsq.validate(ext).ok
    fsq.write_manifest(dict(man, no_data_sessions=["03/04/2026"]), ext)
    assert_fails_with(ext, "no_data_sessions")
    fsq.write_manifest(dict(man, no_data_sessions="2026-03-03"), ext)
    assert_fails_with(ext, "no_data_sessions")


def test_validator_checks_the_manifest_fields(tmp_path):
    ext, man = clean_ext(tmp_path)
    for key in fsq.MANIFEST_KEYS:
        broken = {k: v for k, v in man.items() if k != key}
        fsq.write_manifest(broken, ext)
        assert_fails_with(ext, "lacks keys")
    for key, value, needle in (("rows_on_change", "yes", "rows_on_change"), ("band_pct", 3.0, "band_pct"),
                               ("window", {"start": "2026-03-09", "end": "2026-03-02"}, "window"),
                               ("excluded_sessions", ["03/04/2026"], "excluded_sessions"),
                               ("shards", {}, "shards"), ("vendor", "", "vendor"), ("n_sessions", -1, "n_sessions")):
        fsq.write_manifest(dict(man, **{key: value}), ext)
        assert_fails_with(ext, needle)
    with open(os.path.join(ext, fsq.MANIFEST_FILE), "w") as f:
        f.write("{not json")
    assert_fails_with(ext, "unreadable")


def test_validator_needs_the_minute_file(tmp_path):
    ext, _ = clean_ext(tmp_path)
    os.remove(os.path.join(ext, fsq.MINUTE_FILE))
    assert_fails_with(ext, "minute file")


def test_validator_runs_without_databento_and_cli_exit_codes(tmp_path):
    ext, man = clean_ext(tmp_path)
    code = (f"import sys; sys.path.insert(0, {HERE!r}); import fetch_spy_0dte_quotes as f; "
            f"v = f.validate({ext!r}); assert v.ok, v.failures; "
            "assert 'databento' not in sys.modules, 'databento was imported'; print('LAZY_OK')")
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, env=env)
    assert out.returncode == 0 and "LAZY_OK" in out.stdout, out.stderr
    tool = os.path.join(HERE, "fetch_spy_0dte_quotes.py")
    ok = subprocess.run([sys.executable, tool, "--validate-only", "--ext-dir", ext], capture_output=True, text=True,
                        env=env)
    assert ok.returncode == 0 and "VALID" in ok.stdout and "crossed (bid > ask)" in ok.stdout, ok.stdout + ok.stderr
    os.remove(os.path.join(ext, next(iter(man["shards"]))))
    bad = subprocess.run([sys.executable, tool, "--validate-only", "--ext-dir", ext], capture_output=True, text=True,
                         env=env)
    assert bad.returncode == 1 and "INVALID" in bad.stdout


# ----------------------------------------------------------------------------------------------------------------
# (i) the resumable cache
# ----------------------------------------------------------------------------------------------------------------
def test_resumable_cache_skips_sessions_already_cached(tmp_path):
    ext = make_ext(tmp_path, DAYS3)
    first = FakeClient()
    assert run_dl(ext, first).ok
    assert len(first.of("get_range")) == 3
    for day in DAYS3:
        cached = fsq.read_rows(fsq.cache_path(ext, day))
        assert len(cached) > 0 and set(cached["expiry"]) == {day}
    before = {n: fsq.sha256_file(os.path.join(ext, n)) for n in os.listdir(ext) if n.startswith(fsq.SHARD_PREFIX)}
    second = FakeClient()
    assert run_dl(ext, second).ok
    assert second.of("get_range") == []                                      # nothing is requested again
    assert {n: fsq.sha256_file(os.path.join(ext, n)) for n in before} == before   # and the shards are byte-identical
    os.remove(fsq.cache_path(ext, "2026-03-03"))                             # one session lost: only it is re-fetched
    third = FakeClient()
    assert run_dl(ext, third).ok
    assert [_day_of(k) for _, k in third.of("get_range")] == ["2026-03-03"]


def test_a_cache_file_holding_another_sessions_rows_is_refused(tmp_path):
    ext = make_ext(tmp_path, DAYS3)
    os.makedirs(os.path.join(ext, fsq.CACHE_SUBDIR))
    fsq.write_csv(quote_rows(["2026-03-02"]), fsq.cache_path(ext, "2026-03-03"))      # filed under the wrong date
    with pytest.raises(ValueError, match="same-day"):
        run_dl(ext, FakeClient())
    assert not os.path.exists(os.path.join(ext, fsq.MANIFEST_FILE))


def test_a_failed_run_resumes_where_it_stopped(tmp_path):
    ext = make_ext(tmp_path, DAYS3)
    with pytest.raises(HttpErr):
        run_dl(ext, FakeClient(errors={"get_range": [HttpErr(401)]}))        # the very first request is refused
    assert os.listdir(os.path.join(ext, fsq.CACHE_SUBDIR)) == []             # a failed session leaves no cache file

    class FailOnThird(FakeClient):
        def get_range(self, *a, **k):
            if len(self.of("get_range")) == 2:
                self.calls.append(("get_range", a, k))
                raise HttpErr(402)
            return super().get_range(*a, **k)

    with pytest.raises(HttpErr):
        run_dl(ext, FailOnThird())
    assert sorted(os.listdir(os.path.join(ext, fsq.CACHE_SUBDIR))) == ["2026-03-02.csv.gz", "2026-03-03.csv.gz"]
    resumed = FakeClient()
    assert run_dl(ext, resumed).ok
    assert [_day_of(k) for _, k in resumed.of("get_range")] == ["2026-03-09"]
    assert not [n for n in os.listdir(os.path.join(ext, fsq.CACHE_SUBDIR)) if ".tmp." in n]


# ----------------------------------------------------------------------------------------------------------------
# (j) retry with exponential backoff
# ----------------------------------------------------------------------------------------------------------------
def flaky(*failures_then_value):
    queue = list(failures_then_value)
    calls = []

    def fn():
        calls.append(1)
        item = queue.pop(0)
        if isinstance(item, Exception):
            raise item
        return item

    return fn, calls


def test_retry_backs_off_exponentially_then_succeeds():
    fn, calls = flaky(HttpErr(503), HttpErr(502), HttpErr(504), "ok")
    sleeps = Sleeps()
    assert fsq.call_with_retry(fn, "x", sleep=sleeps) == "ok"
    assert sleeps == [2.0, 4.0, 8.0] and len(calls) == 4


def test_retry_backoff_is_capped_and_the_last_error_is_raised():
    fn, calls = flaky(*[HttpErr(503)] * 10)
    sleeps = Sleeps()
    with pytest.raises(HttpErr) as e:
        fsq.call_with_retry(fn, "x", max_attempts=8, sleep=sleeps)
    assert e.value.http_status == 503 and len(calls) == 8
    assert sleeps == [2.0, 4.0, 8.0, 16.0, 32.0, 64.0, 120.0]


def test_retry_honours_retry_after_but_never_sleeps_less_than_the_backoff():
    fn, _ = flaky(HttpErr(429, {"Retry-After": "30"}), HttpErr(429, {"retry-after": "1"}), "ok")
    sleeps = Sleeps()
    assert fsq.call_with_retry(fn, "x", sleep=sleeps) == "ok"
    assert sleeps == [30.0, 4.0]                                             # 30 > 2; then 1 < backoff 4
    when = (dt.datetime.now(dt.timezone.utc) + dt.timedelta(seconds=60)).strftime("%a, %d %b %Y %H:%M:%S GMT")
    fn, _ = flaky(HttpErr(503, {"Retry-After": when}), "ok")
    sleeps = Sleeps()
    fsq.call_with_retry(fn, "x", sleep=sleeps)
    assert 55 <= sleeps[0] <= 61                                             # an HTTP-date is honoured too
    fn, _ = flaky(HttpErr(429, {"Retry-After": "100000"}), "ok")
    sleeps = Sleeps()
    fsq.call_with_retry(fn, "x", sleep=sleeps)
    assert sleeps == [900.0]                                                 # capped, not a day-long hang


@pytest.mark.parametrize("status", [408, 429, 500, 502, 503, 504])
def test_retry_retries_these_http_statuses(status):
    fn, calls = flaky(HttpErr(status), "ok")
    assert fsq.call_with_retry(fn, "x", sleep=nosleep) == "ok" and len(calls) == 2


@pytest.mark.parametrize("exc", [HttpErr(400), HttpErr(401), HttpErr(402), HttpErr(403), HttpErr(404), HttpErr(422),
                                 ValueError("bug"), KeyError("k"), AssertionError("no")])
def test_retry_raises_these_at_once(exc):
    fn, calls = flaky(exc, "never")
    sleeps = Sleeps()
    with pytest.raises(type(exc)):
        fsq.call_with_retry(fn, "x", sleep=sleeps)
    assert len(calls) == 1 and sleeps == []


def test_retry_retries_timeouts_and_dropped_connections():
    requests = pytest.importorskip("requests")
    for exc in (TimeoutError("t"), ConnectionError("c"), requests.exceptions.ReadTimeout("r"),
                requests.exceptions.ConnectTimeout("c"), requests.exceptions.ConnectionError("c"),
                requests.exceptions.ChunkedEncodingError("c")):
        fn, calls = flaky(exc, "ok")
        assert fsq.call_with_retry(fn, "x", sleep=nosleep) == "ok" and len(calls) == 2, type(exc)
    for exc in (requests.exceptions.SSLError("tls"), requests.exceptions.ProxyError("403 from the proxy"),
                requests.exceptions.InvalidURL("u")):
        fn, calls = flaky(exc, "never")
        with pytest.raises(type(exc)):
            fsq.call_with_retry(fn, "x", sleep=nosleep)
        assert len(calls) == 1, type(exc)


def test_retry_retries_a_stream_cut_mid_transfer():
    class BentoError(Exception):
        pass

    fn, calls = flaky(BentoError("Error streaming response: connection reset"), "ok")
    assert fsq.call_with_retry(fn, "x", sleep=nosleep) == "ok" and len(calls) == 2
    fn, calls = flaky(BentoError("some other vendor error"), "never")
    with pytest.raises(BentoError):
        fsq.call_with_retry(fn, "x", sleep=nosleep)


def test_api_retries_every_vendor_call_and_get_range_is_not_double_written(tmp_path):
    ext = make_ext(tmp_path, DAYS3)
    client = FakeClient(errors={"get_cost": [HttpErr(503), HttpErr(429, {"Retry-After": "5"})],
                                "get_range": [HttpErr(504)], "resolve": [HttpErr(500)],
                                "get_dataset_condition": [HttpErr(408)], "get_billable_size": [TimeoutError("t")]})
    sleeps = Sleeps()
    assert run_dl(ext, client, sleep=sleeps).ok
    assert len(client.of("get_range")) == 3 + 1 and len(client.of("get_cost")) == 3 + 2
    assert len(client.of("resolve")) == 3 + 1 and len(client.of("get_dataset_condition")) == 1 + 1
    assert 5.0 in sleeps and sleeps.count(2.0) >= 4
    assert sorted(os.listdir(os.path.join(ext, fsq.CACHE_SUBDIR))) == [f"{d}.csv.gz" for d in sorted(DAYS3)]
    assert fsq.validate(ext).ok


# ----------------------------------------------------------------------------------------------------------------
# (k) the estimate
# ----------------------------------------------------------------------------------------------------------------
def four_sessions(tmp_path):
    return make_ext(tmp_path, {"2026-03-02": 678.73, "2026-03-03": 680.0, "2026-04-01": 690.5, "2026-04-02": 691.0})


def test_estimate_sums_cost_bytes_months_symbols_and_applies_the_condition(tmp_path, capsys):
    ext = four_sessions(tmp_path)
    cost = {"2026-03-02": 1.5, "2026-03-03": 2.5, "2026-04-01": 4.0, "2026-04-02": 8.0}
    size = {"2026-03-02": 1000, "2026-03-03": 2000, "2026-04-01": 3000, "2026-04-02": 4000}
    client = FakeClient(cost=lambda kw: cost[_day_of(kw)], size=lambda kw: size[_day_of(kw)],
                        conditions={"2026-03-03": "degraded", "2026-04-02": "missing"},
                        unlisted=lambda s: fsq.parse_osi(s).strike > 700)
    sessions = fsq.load_sessions(ext, "2026-03-02", "2026-04-02")
    est = fsq.estimate(fsq.Api(client, sleep=nosleep), sessions, "2026-03-02", "2026-04-02")
    assert [p.date for p in est.fetch_plans()] == ["2026-03-02", "2026-04-01"]
    assert {p.date: p.excluded for p in est.excluded_plans()} == {"2026-03-03": "degraded", "2026-04-02": "missing"}
    assert est.total_usd == 5.5 and est.total_bytes == 4000                  # excluded sessions cost nothing
    assert est.per_month() == {"2026-03": 1.5, "2026-04": 4.0}
    assert est.n_symbols == (50 + 39) * 2                                    # strikes 651..700, 662..700; both rights
    assert est.unresolved == 6 * 2 + 19 * 2                                  # strikes 701..706 and 701..719
    asked = {_day_of(k) for _, k in client.of("get_cost")} | {_day_of(k) for _, k in client.of("get_billable_size")}
    assert asked == {"2026-03-02", "2026-04-01"}                             # the excluded days were never priced
    assert {k["start_date"] for _, k in client.of("resolve")} == {"2026-03-02", "2026-04-01"}
    fsq.print_estimate(est)
    out = capsys.readouterr().out
    assert "TOTAL USD: $5.50" in out and "2026-03  " in out and "2026-04  " in out
    assert "excluded 2026-03-03: degraded" in out and "excluded 2026-04-02: missing" in out
    assert "4,000 bytes" in out and "nothing was downloaded" in out
    assert client.of("get_range") == []                                      # an estimate never downloads


@pytest.mark.parametrize("style", ["empty", "omit"])
def test_estimate_reads_both_shapes_of_the_symbology_answer(tmp_path, style):
    ext = four_sessions(tmp_path)
    client = FakeClient(unlisted=lambda s: fsq.parse_osi(s).strike > 700, resolve_style=style)
    est = fsq.estimate(fsq.Api(client, sleep=nosleep), fsq.load_sessions(ext, "2026-03-02", "2026-03-02"),
                       "2026-03-02", "2026-03-02")
    (plan,) = est.plans
    assert plan.unresolved == 12 and len(plan.symbols) == 100
    assert all(fsq.parse_osi(s).strike <= 700 for s in plan.symbols)


def test_estimate_does_not_hide_pending_or_unlisted_sessions_as_excluded(tmp_path, capsys):
    """A51a excludes only what the vendor reports degraded or missing. A pending session, or one with nothing listed,
    is a GAP: it must reach the unit as missing legs (the coverage gate), never vanish into excluded_sessions."""
    ext = four_sessions(tmp_path)
    client = FakeClient(conditions={"2026-03-03": "pending", "2026-04-02": "degraded"},
                        unlisted=lambda s: "260401" in s)
    est = fsq.estimate(fsq.Api(client, sleep=nosleep), fsq.load_sessions(ext, "2026-03-02", "2026-04-02"),
                       "2026-03-02", "2026-04-02")
    assert {p.date: p.no_data for p in est.no_data_plans()} == {"2026-03-03": "pending",
                                                                "2026-04-01": "no symbols resolved"}
    assert {p.date: p.excluded for p in est.excluded_plans()} == {"2026-04-02": "degraded"}
    assert [p.date for p in est.fetch_plans()] == ["2026-03-02"]
    asked = {_day_of(k) for _, k in client.of("get_cost")}
    assert asked == {"2026-03-02"}                                           # neither gap was priced
    fsq.print_estimate(est)
    out = capsys.readouterr().out
    assert "NO DATA 2026-03-03: pending" in out and "NO DATA 2026-04-01: no symbols resolved" in out
    assert "excluded 2026-04-02: degraded" in out and "excluded 2026-03-03" not in out


def test_estimate_warns_about_sessions_the_vendor_does_not_mention(tmp_path, capsys):
    ext = four_sessions(tmp_path)
    client = FakeClient(omit_dates=["2026-03-03"])
    est = fsq.estimate(fsq.Api(client, sleep=nosleep), fsq.load_sessions(ext, "2026-03-02", "2026-04-02"),
                       "2026-03-02", "2026-04-02")
    assert est.unreported == ["2026-03-03"] and len(est.fetch_plans()) == 4
    fsq.print_estimate(est)
    assert "does not mention 1 sessions" in capsys.readouterr().out


def test_estimate_flags_a_session_without_a_0930_bar(tmp_path, capsys):
    ext = make_ext(tmp_path, {"2026-03-02": (678.73, "09:35"), "2026-03-03": 680.0})
    est = fsq.estimate(fsq.Api(FakeClient(), sleep=nosleep), fsq.load_sessions(ext, "2026-03-02", "2026-03-03"),
                       "2026-03-02", "2026-03-03")
    assert [p.open_minute for p in est.plans] == [575, 570]
    fsq.print_estimate(est)
    out = capsys.readouterr().out
    assert "FLAG 2026-03-02: no 09:30 bar" in out and "09:35" in out and "FLAG 2026-03-03" not in out


def test_estimate_and_resolve_split_requests_at_2000_symbols(tmp_path, monkeypatch):
    ext = make_ext(tmp_path, {"2026-03-02": 678.73})
    many = [fsq.osi_symbol("2026-03-02", right, k) for k in range(1, 2251) for right in "CP"]      # 4,500 symbols
    monkeypatch.setattr(fsq, "candidate_symbols", lambda day, price: many)
    client = FakeClient(cost=1.0, size=100)
    est = fsq.estimate(fsq.Api(client, sleep=nosleep), fsq.load_sessions(ext, "2026-03-02", "2026-03-02"),
                       "2026-03-02", "2026-03-02")
    for name in ("resolve", "get_cost", "get_billable_size"):
        assert [len(k["symbols"]) for _, k in client.of(name)] == [2000, 2000, 500], name
    assert est.total_usd == 3.0 and est.total_bytes == 300 and est.n_symbols == 4500
    api = fsq.Api(client, sleep=nosleep)
    t0, t1 = fsq.session_window("2026-03-02")
    for call in (api.cost, api.billable_size, api.get_range):
        with pytest.raises(ValueError):
            call(many[:2001], t0, t1)
        with pytest.raises(ValueError):
            call([], t0, t1)
    plan = fsq.SessionPlan("2026-03-02", 678.73, 570, symbols=many)
    rows = fsq.fetch_session(api, plan)
    assert [len(k["symbols"]) for _, k in client.of("get_range")] == [2000, 2000, 500]
    assert len(rows) == 4500 * 3 and rows.equals(
        rows.sort_values(["ts", "strike", "right"], kind="mergesort").reset_index(drop=True))


def test_estimate_through_the_cli_prints_the_totals_and_downloads_nothing(tmp_path, monkeypatch, capsys):
    ext = make_ext(tmp_path, DAYS3)
    client = FakeClient(cost=60.0, size=5_000_000)
    monkeypatch.setattr(fsq, "make_client", lambda: client)
    assert fsq.main(["--estimate", "--start", "2026-03-02", "--end", "2026-03-09", "--ext-dir", ext]) == 0
    out = capsys.readouterr().out
    assert "TOTAL USD: $180.00" in out and "15,000,000 bytes" in out and "2026-03  " in out
    assert client.of("get_range") == [] and not os.path.exists(os.path.join(ext, fsq.CACHE_SUBDIR))


# ----------------------------------------------------------------------------------------------------------------
# (l) sessions and the 09:30 reference price
# ----------------------------------------------------------------------------------------------------------------
def test_session_price_is_the_open_of_the_0930_bar_across_the_dst_change(tmp_path):
    ext = make_ext(tmp_path, DAYS3)                       # 2026-03-09 is after the 2026-03-08 DST change
    got = fsq.load_sessions(ext, "2026-03-01", "2026-03-31")
    assert got == [fsq.Session("2026-03-02", 678.73, 570), fsq.Session("2026-03-03", 680.0, 570),
                   fsq.Session("2026-03-09", 690.5, 570)]
    assert [s.date for s in fsq.load_sessions(ext, "2026-03-03", "2026-03-09")] == ["2026-03-03", "2026-03-09"]
    assert fsq.load_sessions(ext, "2026-03-04", "2026-03-08") == []


def test_session_without_a_0930_bar_uses_the_first_bar_after_it_and_is_flagged(tmp_path):
    ext = make_ext(tmp_path, {"2026-03-02": (678.73, "09:35"), "2026-03-03": (680.0, "10:15")})
    got = fsq.load_sessions(ext, "2026-03-02", "2026-03-03")
    assert got == [fsq.Session("2026-03-02", 678.73, 575), fsq.Session("2026-03-03", 680.0, 615)]


def test_sessions_ignore_extended_hours_weekends_and_non_sessions(tmp_path):
    ext = make_ext(tmp_path, {"2026-03-06": 678.0, "2026-03-07": 679.0, "2026-03-09": 690.5})   # 03-07 is a Saturday
    assert [s.date for s in fsq.load_sessions(ext, "2026-03-01", "2026-03-31")] == ["2026-03-06", "2026-03-09"]
    # a day that has only pre-market and after-hours bars is not a session
    path = os.path.join(ext, fsq.MINUTE_FILE)
    df = pd.read_csv(path)
    extra = pd.DataFrame([(utc("2026-03-10", "08:00"), 700.0, 700.1, 699.9, 700.0, 10),
                          (utc("2026-03-10", "16:00"), 701.0, 701.1, 700.9, 701.0, 10)], columns=df.columns)
    pd.concat([df, extra]).sort_values("ts").to_csv(path, index=False, compression="gzip")
    assert "2026-03-10" not in [s.date for s in fsq.load_sessions(ext, "2026-03-01", "2026-03-31")]


def test_default_window_has_the_135_sessions_a51_names_in_the_canonical_minute_file():
    path = os.path.join(REPO, "data", "ext", fsq.MINUTE_FILE)
    if not os.path.exists(path):
        pytest.skip("canonical minute file not present")
    got = fsq.load_sessions(os.path.join(REPO, "data", "ext"), fsq.WINDOW_START, fsq.WINDOW_END)
    assert len(got) == 135 and got[0].date == "2026-03-02" and got[-1].date == "2026-09-11"
    assert {s.open_minute for s in got} == {570}
    dates = {s.date for s in got}
    assert not dates & {"2026-04-03", "2026-05-25", "2026-06-19", "2026-07-03", "2026-09-07"}    # NYSE holidays
    assert all(500 < s.price < 900 for s in got)                                                  # SPY dollars
    assert fsq.WINDOW_START == "2026-03-02" and fsq.WINDOW_END == "2026-09-11"


# ----------------------------------------------------------------------------------------------------------------
# (m) the conversion, on synthetic vendor frames
# ----------------------------------------------------------------------------------------------------------------
A, B = "SPY   260302C00680000", "SPY   260302P00679000"


def test_convert_formats_sorts_and_keeps_empty_books():
    df = vendor_frame([("2026-03-02 14:33:00", B, 1.10, 1.20, 5, 6),
                       ("2026-03-02 14:31:00", B, np.nan, np.nan, 0, 0),         # the empty book: kept
                       ("2026-03-02 14:31:00", A, 3.50, 3.60, 7, 8),
                       ("2026-03-02 14:32:00", A, 3.55, 3.65, 9, 10)])
    rows = fsq.convert_df(df)
    assert list(rows.columns) == fsq.COLS
    assert rows["ts"].tolist() == ["2026-03-02 14:31:00"] * 2 + ["2026-03-02 14:32:00", "2026-03-02 14:33:00"]
    assert rows["strike"].tolist() == [679.0, 680.0, 680.0, 679.0]               # sorted by ts, then strike, then right
    assert rows["right"].tolist() == ["P", "C", "C", "P"]
    assert rows["expiry"].tolist() == ["2026-03-02"] * 4
    assert np.isnan(rows.loc[0, "bid"]) and np.isnan(rows.loc[0, "ask"])
    assert rows["bid"].tolist()[1:] == [3.5, 3.55, 1.1] and rows["ask"].tolist()[1:] == [3.6, 3.65, 1.2]
    assert rows["bid_size"].tolist() == [0, 7, 9, 5] and rows["ask_size"].tolist() == [0, 8, 10, 6]
    assert rows["bid_size"].dtype == np.int64 and rows["ask_size"].dtype == np.int64


def test_convert_uses_ts_recv_not_ts_event_and_converts_to_utc():
    df = vendor_frame([("2026-03-02 14:31:00", A, 1.0, 1.1, 1, 1)])
    assert df["ts_event"].iloc[0] == pd.Timestamp("2026-03-02 14:30:23", tz="UTC")
    assert fsq.convert_df(df)["ts"].tolist() == ["2026-03-02 14:31:00"]
    ny = df.copy()
    ny.index = ny.index.tz_convert(NY)                                           # the same instant, another zone
    assert fsq.convert_df(ny)["ts"].tolist() == ["2026-03-02 14:31:00"]


def test_convert_rounds_float_noise_away_but_keeps_the_vendor_grid():
    df = vendor_frame([("2026-03-02 14:31:00", A, 0.32000000000000006, 0.34, 1, 1)])
    assert fsq.convert_df(df)["bid"].tolist() == [0.32]
    df = vendor_frame([("2026-03-02 14:31:00", A, 0.123456789, 0.5, 1, 1)])
    assert fsq.convert_df(df)["bid"].tolist() == [0.123456789]


def test_convert_refuses_what_breaks_the_vendor_contract():
    good = vendor_frame([("2026-03-02 14:31:00", A, 1.0, 1.1, 1, 1)])
    off = good.copy()
    off.index = off.index + pd.Timedelta(seconds=5)
    with pytest.raises(ValueError, match="whole minute"):
        fsq.convert_df(off)
    sub = good.copy()
    sub.index = sub.index + pd.Timedelta(milliseconds=1)
    with pytest.raises(ValueError, match="whole minute"):
        fsq.convert_df(sub)
    with pytest.raises(ValueError, match="no mapped raw symbol"):
        fsq.convert_df(good.assign(symbol=[None]))
    with pytest.raises(ValueError):
        fsq.convert_df(good.assign(symbol=["SPY240302C680"]))
    with pytest.raises(ValueError, match="float dollars"):
        fsq.convert_df(good.assign(bid_px_00=np.array([1_000_000_000], dtype="int64")))
    with pytest.raises(ValueError, match="ts_recv"):
        fsq.convert_df(good.rename_axis("ts_event"))
    with pytest.raises(ValueError, match="ts_recv"):
        fsq.convert_df(good.set_axis(good.index.tz_localize(None)))                 # a naive index
    with pytest.raises(ValueError, match="missing columns"):
        fsq.convert_df(good.drop(columns=["ask_sz_00"]))
    empty = fsq.convert_df(vendor_frame([]))
    assert len(empty) == 0 and list(empty.columns) == fsq.COLS


def test_session_rows_guard_rejects_next_day_contracts_and_other_dates(tmp_path):
    rows = quote_rows(["2026-03-02"], strikes=(680,), minutes=1)
    fsq.check_session_rows(rows, "2026-03-02")
    fsq.check_session_rows(rows.iloc[0:0], "2026-03-02")
    with pytest.raises(ValueError, match="same-day"):
        fsq.check_session_rows(rows.assign(expiry="2026-03-03"), "2026-03-02")
    with pytest.raises(ValueError, match="same-day"):
        fsq.check_session_rows(rows, "2026-03-03")
    with pytest.raises(ValueError, match="same-day"):                        # the right expiry, stamped on another date
        fsq.check_session_rows(rows.assign(ts="2026-03-03 14:31:00"), "2026-03-02")
    ext = make_ext(tmp_path, {"2026-03-02": 678.73})
    with pytest.raises(ValueError, match="same-day"):
        run_dl(ext, FakeClient(shift_expiry=True), days={"2026-03-02": 678.73})


# ----------------------------------------------------------------------------------------------------------------
# (n) the whole download, end to end on the double
# ----------------------------------------------------------------------------------------------------------------
def test_download_end_to_end_writes_shards_and_manifest_and_validates(tmp_path):
    days = {"2026-03-02": 678.73, "2026-03-03": 680.0, "2026-03-31": 681.0, "2026-04-01": 690.5, "2026-04-02": 691.0}
    ext = make_ext(tmp_path, days)
    client = FakeClient(cost=lambda kw: 2.0, conditions={"2026-04-02": "degraded"},
                        unlisted=lambda s: fsq.parse_osi(s).strike >= 700)
    now = dt.datetime(2026, 10, 5, 12, 0, 0, tzinfo=dt.timezone.utc)
    v = run_dl(ext, client, days=days, now=now)
    assert v.ok, v.failures
    with open(os.path.join(ext, fsq.MANIFEST_FILE)) as f:
        man = json.load(f)
    assert v.report["sessions"] == 4 and v.report["excluded"] == 1 and v.report["shards"] == 2   # validate() ran
    assert v.report["no_data"] == 0
    assert v.report["rows"] == sum(e["rows"] for e in man["shards"].values()) > 0
    assert [k for k in man if k in fsq.MANIFEST_KEYS] == fsq.MANIFEST_KEYS
    assert man["window"] == {"start": "2026-03-02", "end": "2026-04-02"}
    assert man["n_sessions"] == 4 and man["excluded_sessions"] == ["2026-04-02"] and man["no_data_sessions"] == []
    assert man["fetched_at"] == "2026-10-05T12:00:00Z" and man["client_version"] == "test"
    assert man["cost_estimate_usd"] == 8.0 and man["rows_on_change"] is True and man["band_pct"] == 4.0
    # unresolved: per session, the band strikes at or above 700, both rights
    expect = sum(2 * sum(1 for k in fsq.band_strikes(p) if k >= 700) for d, p in days.items() if d != "2026-04-02")
    assert man["unresolved_symbols"] == expect and expect > 0
    assert sorted(man["shards"]) == ["spy_0dte_quotes_1min_2026-03.csv.gz", "spy_0dte_quotes_1min_2026-04.csv.gz"]
    for name, entry in man["shards"].items():
        df = pd.read_csv(os.path.join(ext, name))
        assert list(df.columns) == fsq.COLS and len(df) == entry["rows"]
        assert fsq.sha256_file(os.path.join(ext, name)) == entry["sha256"]
        assert len(df.drop_duplicates(["ts", "strike", "right"])) == len(df)
        assert (df["strike"] < 700).all()
    assert [n for n in os.listdir(ext) if ".tmp." in n] == []


def test_download_keeps_gaps_visible_only_degraded_and_missing_sessions_are_excluded(tmp_path):
    days = {"2026-03-02": 678.73, "2026-03-03": 680.0, "2026-03-09": 690.5, "2026-03-10": 691.0}
    ext = make_ext(tmp_path, days)
    client = FakeClient(conditions={"2026-03-03": "pending", "2026-03-09": "missing"},
                        unlisted=lambda s: fsq.parse_osi(s).expiry == "2026-03-10")
    v = run_dl(ext, client, days=days)
    assert v.ok, v.failures
    with open(os.path.join(ext, fsq.MANIFEST_FILE)) as f:
        man = json.load(f)
    assert man["excluded_sessions"] == ["2026-03-09"]                        # the vendor's own missing flag (A51a)
    assert man["no_data_sessions"] == ["2026-03-03", "2026-03-10"]           # pending; nothing listed: gaps, not hidden
    assert man["n_sessions"] == 1
    assert [_day_of(k) for _, k in client.of("get_range")] == ["2026-03-02"]
    assert (v.report["sessions"], v.report["excluded"], v.report["no_data"]) == (1, 1, 2)


def test_download_declares_a_session_the_vendor_returned_nothing_for_as_no_data_not_excluded(tmp_path, capsys):
    ext = make_ext(tmp_path, DAYS3)
    assert run_dl(ext, FakeClient(empty_days=["2026-03-03"])).ok
    with open(os.path.join(ext, fsq.MANIFEST_FILE)) as f:
        man = json.load(f)
    assert man["no_data_sessions"] == ["2026-03-03"] and man["excluded_sessions"] == [] and man["n_sessions"] == 2
    assert "returned no rows" in capsys.readouterr().err
    assert len(fsq.read_rows(fsq.cache_path(ext, "2026-03-03"))) == 0       # cached as empty: a re-run does not re-ask


def test_a_dataset_the_validator_rejects_makes_the_download_exit_1(tmp_path, monkeypatch, capsys):
    ext = make_ext(tmp_path, DAYS3)
    client = FakeClient(dup_rows=True)                                       # every session carries a duplicate row
    v = run_dl(ext, client)
    assert not v.ok and any("duplicate" in f for f in v.failures)
    shutil.rmtree(os.path.join(ext, fsq.CACHE_SUBDIR))                       # ask the vendor again
    monkeypatch.setattr(fsq, "make_client", lambda: FakeClient(dup_rows=True))
    argv = ["--download", "--max-usd", "1000", "--start", "2026-03-02", "--end", "2026-03-09", "--ext-dir", ext]
    capsys.readouterr()
    assert fsq.main(argv) == 1
    out = capsys.readouterr().out
    assert "INVALID" in out and "duplicate" in out


def test_fetch_session_ignores_blocks_the_vendor_has_no_records_for():
    many = [fsq.osi_symbol("2026-03-02", right, k) for k in range(1, 2251) for right in "CP"]
    client = FakeClient(only=lambda sym: fsq.parse_osi(sym).strike <= 1000)   # only the first block has records
    plan = fsq.SessionPlan("2026-03-02", 678.73, 570, symbols=many)
    rows = fsq.fetch_session(fsq.Api(client, sleep=nosleep), plan)
    assert len(client.of("get_range")) == 3 and len(rows) == 2000 * 3
    empty = fsq.fetch_session(fsq.Api(FakeClient(only=lambda sym: False), sleep=nosleep), plan)
    assert len(empty) == 0 and list(empty.columns) == fsq.COLS


def test_download_refuses_to_write_a_manifest_for_nothing(tmp_path):
    ext = make_ext(tmp_path, DAYS3)
    client = FakeClient(unlisted=lambda s: True)                             # nothing resolves: every session a gap
    with pytest.raises(RuntimeError, match="no session to fetch"):
        run_dl(ext, client)
    assert client.of("get_range") == [] and not os.path.exists(os.path.join(ext, fsq.MANIFEST_FILE))
    ext2 = make_ext(tmp_path / "b", DAYS3)
    with pytest.raises(RuntimeError, match="every fetched session was empty"):
        run_dl(ext2, FakeClient(empty_days=list(DAYS3)))
    assert not os.path.exists(os.path.join(ext2, fsq.MANIFEST_FILE))


# ----------------------------------------------------------------------------------------------------------------
# (o) the CLI and the repo plumbing
# ----------------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("argv", [
    [], ["--download"], ["--download", "--max-usd", "-1"], ["--download", "--max-usd", "nan"],
    ["--estimate", "--max-usd", "5"], ["--from-dbn", "x.dbn"], ["--estimate", "--out", "x.csv"],
    ["--estimate", "--start", "2026-09-12", "--end", "2026-09-11"], ["--estimate", "--start", "09/01/2026"],
    ["--validate-only", "--start", "2026-03-02"], ["--estimate", "--key", "secret"], ["--estimate", "--validate-only"]])
def test_cli_rejects_bad_argument_combinations(argv):
    with pytest.raises(SystemExit) as e:
        fsq.main(argv)
    assert e.value.code == 2


def test_cli_reports_a_missing_minute_file_without_a_traceback(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(fsq, "make_client", lambda: pytest.fail("the vendor client must not be built first"))
    assert fsq.main(["--estimate", "--ext-dir", str(tmp_path)]) == 1
    assert "minute file" in capsys.readouterr().err
    ext = make_ext(tmp_path / "x", {"2026-03-02": 678.73})
    assert fsq.main(["--estimate", "--ext-dir", ext, "--start", "2026-05-01", "--end", "2026-05-31"]) == 1
    assert "no sessions between 2026-05-01 and 2026-05-31" in capsys.readouterr().err


def test_cli_defaults_are_a51s_decision_window_and_help_renders(capsys, monkeypatch):
    seen = []
    monkeypatch.setattr(fsq, "load_sessions", lambda ext_dir, start, end: seen.append((start, end)) or [])
    assert fsq.main(["--estimate"]) == 1 and seen == [("2026-03-02", "2026-09-11")]
    assert fsq.main(["--download", "--max-usd", "1"]) == 1 and seen[-1] == ("2026-03-02", "2026-09-11")
    capsys.readouterr()
    with pytest.raises(SystemExit) as e:
        fsq.main(["--help"])
    assert e.value.code == 0
    out = capsys.readouterr().out
    for needle in ("--estimate", "--download", "--max-usd", "--from-dbn", "--validate-only", "DATABENTO_API_KEY",
                   "pip install databento==0.87.0", ".venv-quotes", "THE COST GUARD", "A51"):
        assert needle in out, needle


def test_repo_plumbing_gitignore_and_docstring():
    with open(os.path.join(REPO, ".gitignore")) as f:
        lines = [x.strip() for x in f]
    assert "data/ext/_quotes_cache/" in lines and ".venv-quotes/" in lines
    doc = fsq.__doc__
    assert "python -m venv .venv-quotes && .venv-quotes/bin/pip install databento==0.87.0" in doc
    assert "DATABENTO_API_KEY" in doc and "never" in doc and "--key" in doc
