"""Canonical minute frame for every feed (COUPLED — single owner, see ARCHITECTURE.md).

Every feed is converted to tz-aware America/New_York by its VERIFIED convention:
  oanda     ts_utc  (UTC; 2018-07-08 first bar 22:00 UTC = 18:00 EDT Sunday Globex open)
  histdata  ts_et   (naive Eastern WITH daylight saving; Sunday open prints 18:01 in Jan and Jul)
  ext       ts      (UTC, per DATA.md spec; user-supplied csv.gz)
Then: keep 09:30 <= time < 16:00, drop sessions with fewer than MIN_BARS bars (half days,
outages, thin holiday trading on CFD feeds) and list them, weekdays only.
The DST probe reuses Thread B's open detector (step7_validate.detect_open: the minute-of-day
where the |Δclose| activity profile steps up the most) and the calendar reconciliation names
every short session's reason against the NYSE holiday and early-close rules.
"""
import numpy as np
import pandas as pd

NY = "America/New_York"
RTH_START, RTH_END = 570, 960          # minute-of-day: 09:30 .. 16:00
MIN_BARS = 300                          # both threads' rule (mh.py:17, step17_intramom.py:63)
FULL_BARS = 370                         # CFD feeds routinely miss a few tickless minutes
KNOWN_CLOSURES = {"2018-12-05": "closure: Bush day of mourning", "2025-01-09": "closure: Carter day of mourning",
                  "2012-10-29": "closure: Hurricane Sandy", "2012-10-30": "closure: Hurricane Sandy",
                  "2007-01-02": "closure: Ford day of mourning"}


def _load(feed, path):
    if feed == "oanda":
        d = pd.read_parquet(path)
        ts = pd.DatetimeIndex(d["ts_utc"]).tz_convert(NY)
    elif feed == "histdata":
        d = pd.read_parquet(path)
        ts = pd.DatetimeIndex(d["ts_et"]).tz_localize(NY, ambiguous="NaT", nonexistent="NaT")
    elif feed == "ext":
        d = pd.read_csv(path, usecols=["ts", "open", "high", "low", "close", "volume"])
        ts = pd.DatetimeIndex(pd.to_datetime(d["ts"], utc=True)).tz_convert(NY)
    else:
        raise ValueError(feed)
    out = pd.DataFrame({"ts_ny": ts, "open": d["open"].to_numpy(float), "high": d["high"].to_numpy(float),
                        "low": d["low"].to_numpy(float), "close": d["close"].to_numpy(float),
                        "volume": d["volume"].to_numpy(float)})
    return out.dropna(subset=["ts_ny", "close"]).sort_values("ts_ny").drop_duplicates("ts_ny").reset_index(drop=True)


def instrument_of(frame):
    """For the post-2020 ext feed only: SPY trades near SPX/10 (300-700); SPX and ES near 3000-7000."""
    return "SPY" if float(np.nanmedian(frame["close"])) < 1500 else "SPX"


def trading_days_from_vix(path="data/raw/vix_daily.parquet"):
    """NYSE trading-day calendar = the dates the CBOE published a VIX close (1990 → 2026-09-11)."""
    return set(pd.to_datetime(pd.read_parquet(path)["date"]).dt.normalize())


def _sessionize(d, feed, trading_days=None, first_mod=RTH_START):
    d["mod"] = d["ts_ny"].dt.hour * 60 + d["ts_ny"].dt.minute
    d["date"] = d["ts_ny"].dt.tz_localize(None).dt.normalize()
    d = d[(d["mod"] >= first_mod) & (d["mod"] < RTH_END) & (d["ts_ny"].dt.dayofweek < 5)]
    bars = d.groupby("date").size()
    hol = set().union(*(nyse_holidays(y).keys() for y in range(bars.index.min().year, bars.index.max().year + 1)))
    ok = (bars >= MIN_BARS) & ~bars.index.isin(hol)
    if trading_days is not None:
        ok &= bars.index.isin(trading_days)
    keep = bars[ok]
    dropped = bars[~bars.index.isin(keep.index)].rename("bars").reset_index()
    d = d[d["date"].isin(keep.index)].reset_index(drop=True)
    d["feed"] = feed
    return d, dropped


def build(feed, path, trading_days=None):
    """Returns (rth_frame, dropped_sessions). rth_frame columns: ts_ny, date, mod, open, high,
    low, close, volume, feed. `date` is a tz-naive midnight Timestamp (merge-friendly).
    NYSE holidays are excluded even when a CFD feed prints bars on them, and so is any date
    outside `trading_days` (the VIX calendar) when given; dropped_sessions carries every
    excluded weekday with its bar count."""
    return _sessionize(_load(feed, path), feed, trading_days)


def ext_present(ext_dir="data/ext"):
    """True when the user-supplied ext feed is usable: ext_manifest.json AND at least one spx_1min_*.csv.gz (DATA.md)."""
    import glob
    import os
    return os.path.exists(os.path.join(ext_dir, "ext_manifest.json")) and bool(glob.glob(os.path.join(ext_dir, "spx_1min_*.csv.gz")))


def load_ext(ext_dir="data/ext"):
    """The user-supplied post-May-2020 minute file, per DATA.md and ACCEPTANCE A6. Refuses to
    run without ext_manifest.json; converts SPY to SPX-point scale (×10) so every downstream
    constant (costs, strike grid) stays in index points; checks the declared instrument against
    the price level; returns (raw_frame, meta) with meta = instrument, dividends (Series
    ex_date -> amount in SPX points), roll_dates, source, path."""
    import glob
    import json
    import os
    man_path = os.path.join(ext_dir, "ext_manifest.json")
    if not os.path.exists(man_path):
        raise FileNotFoundError(f"{man_path} missing — the session builder refuses to run the ext feed without it (A6)")
    man = json.load(open(man_path))
    inst = man["instrument"].upper()
    if inst not in ("SPY", "ES", "SPX"):
        raise ValueError(f"ext_manifest.json instrument must be SPY, ES or SPX, got {inst}")
    files = sorted(glob.glob(os.path.join(ext_dir, "spx_1min_*.csv.gz")))
    if not files:
        raise FileNotFoundError(f"no {ext_dir}/spx_1min_*.csv.gz")
    d = _load("ext", files[0])
    lvl = float(np.nanmedian(d["close"]))
    if inst == "SPY" and not (100 < lvl < 1500):
        raise ValueError(f"manifest says SPY but median price is {lvl:.1f}")
    if inst in ("ES", "SPX") and not (1500 < lvl < 20000):
        raise ValueError(f"manifest says {inst} but median price is {lvl:.1f}")
    scale = 10.0 if inst == "SPY" else 1.0
    for c in ("open", "high", "low", "close"):
        d[c] = d[c] * scale
    dividends = None
    if inst == "SPY":
        dp = os.path.join(ext_dir, "spy_dividends.csv")
        if not os.path.exists(dp):
            raise FileNotFoundError(f"{dp} missing — required with a SPY feed (A6)")
        dv = pd.read_csv(dp)
        raw = dv["ex_date"].astype(str)
        if raw.str.contains(r"[+-]\d{2}:?\d{2}$|Z$", regex=True).any():
            # tz-aware ex-dates (real-feed spy_dividends.csv carries DST-varying offsets like
            # -05:00 / -04:00; a bare second to_datetime() on an already-mixed-offset column
            # raises "Tz-aware datetime.datetime cannot be converted ... unless utc=True" —
            # Phase 6 defect 1). The ex-date is the NY calendar date the stamp falls on, matching
            # how build_extended/day_table key every other date (a tz-naive midnight Timestamp).
            ex = pd.to_datetime(raw, utc=True).dt.tz_convert(NY).dt.normalize().dt.tz_localize(None)
        else:
            ex = pd.to_datetime(raw).dt.normalize()   # naive strings (pre-existing synthetic format): already an NY date
        dividends = pd.Series(dv["amount"].to_numpy(float) * scale, index=ex)
    meta = dict(instrument=inst, scale=scale, dividends=dividends, roll_dates=[pd.Timestamp(x) for x in man.get("roll_dates", [])],
                source=man.get("source", ""), path=files[0])
    return d, meta


def build_extended(oanda_path="data/raw/oanda_SPX500_USD.parquet", ext_dir="data/ext", trading_days=None):
    """Oanda history + the ext feed for dates after the Oanda series ends, as ONE canonical frame
    so expanding thresholds keep expanding through the holdout. For an SPX cash-index feed the
    session's first bar is 09:31 (the 09:30 print is stale, A6). meta["dividends"] (and, for
    symmetry, meta["roll_dates"]) is scoped to ex-dates/roll-dates strictly after the Oanda end
    AND not before the ext feed's first session — the owner's spy_dividends.csv runs 1993->2026,
    and handing signals.day_table the unscoped series reindexes every SPY ex-date onto d.index,
    which also covers the native Oanda/index sessions on that SAME calendar date, where no
    dividend exists (an index does not drop on SPY's ex-dates). meta["dividends_all"] /
    meta["dividends_ext"] record the count before/after this filter. Returns (frame, dropped,
    meta); meta is None when data/ext is absent."""
    base, dropped = build("oanda", oanda_path, trading_days)
    if not ext_present(ext_dir):
        return base, dropped, None
    raw, meta = load_ext(ext_dir)
    e, dropped_e = _sessionize(raw, "ext", trading_days, first_mod=RTH_START + 1 if meta["instrument"] == "SPX" else RTH_START)
    e = e[e["date"] > base["date"].max()].reset_index(drop=True)
    frame = pd.concat([base, e], ignore_index=True)
    meta["ext_first_date"], meta["ext_last_date"] = (e["date"].min(), e["date"].max()) if len(e) else (pd.NaT, pd.NaT)
    ext_era = lambda ts: (ts > base["date"].max()) & (ts >= meta["ext_first_date"])   # noqa: E731
    meta["dividends_all"] = int(len(meta["dividends"])) if meta["dividends"] is not None else 0
    if meta["dividends"] is not None:
        meta["dividends"] = meta["dividends"][ext_era(meta["dividends"].index)]
    meta["dividends_ext"] = int(len(meta["dividends"])) if meta["dividends"] is not None else 0
    meta["roll_dates"] = [x for x in meta["roll_dates"] if ext_era(x)]
    return frame, pd.concat([dropped, dropped_e], ignore_index=True), meta


def detect_open(frame):
    """Thread B's detector (research/thread_B_inversion/step7_validate.py:34-41), applied to
    08:00-12:00 so the close cannot win: minute-of-day where the smoothed |Δclose| profile
    steps up the most. Thread B reports 09:32 for SPX; anything in 09:30-09:37 is the open."""
    d = frame[(frame["mod"] >= 480) & (frame["mod"] < 720)].copy()
    d["ar"] = d["close"].diff().abs()
    prof = d.groupby("mod")["ar"].mean().rolling(5, center=True).mean()
    return int(prof.diff(5).idxmax())


def open_step(frame, candidates=(RTH_START - 60, RTH_START, RTH_START + 60)):
    """Sustained activity step at each candidate open: mean |Δclose| over the 15 minutes after
    the candidate minus the 15 minutes before. A one-hour timestamp error moves the winner to
    08:30 or 10:30; a 1-3 minute economic release cannot sustain a 15-minute step. Used as-is by
    xmarket.py's local-session detector (24-hour CFD feeds, no gridding needed); dst_probe below
    uses grid_step instead because raw |Δclose| is defeated by a feed with sparse pre-market
    prints (Phase 6 defect 2)."""
    d = frame.copy()
    d["ar"] = d["close"].diff().abs()
    prof = d.groupby("mod")["ar"].mean()
    steps = {c: prof.reindex(range(c, c + 15)).mean() - prof.reindex(range(c - 15, c)).mean() for c in candidates}
    return max(steps, key=steps.get), steps


def grid_step(frame, candidates=(RTH_START - 60, RTH_START, RTH_START + 60)):
    """Sustained activity step at each candidate open, like open_step, but |Δclose| is measured
    on a complete per-session 1-minute-of-day grid (0..1439, close forward-filled) instead of on
    consecutive PRINTED rows. On a feed with sparse extended-hours liquidity (Alpaca IEX ext:
    bars present 04:00-20:00 ET but thin before 09:30) a plain row-to-row diff() attributes the
    ENTIRE price change of a multi-minute quiet gap to whichever minute happens to print next, so
    a handful of pre-market minutes can carry a bigger |Δclose| than the liquid RTH session and
    open_step's step can go negative at the true open (Phase 6 defect 2). On the grid, a minute
    with no print simply repeats the last close (Δclose = 0) instead of absorbing that jump, so
    the pre-market mean collapses and the 09:30 step wins. On a 24-hour CFD feed (Oanda, histdata)
    the grid is already dense — every minute has a real bar almost everywhere — so gridding
    changes essentially nothing there and the statistic is unchanged (still 09:30). A one-hour
    timestamp error still moves the winner to 08:30 or 10:30; a 1-3 minute news print still cannot
    sustain a 15-minute step. A candidate whose whole 15-minute window has no session with any
    ffilled bar at all (e.g. a month with zero prints before 08:15) is NaN, not zero, and never
    wins (idxmax skips NaN; Python's plain max(dict, key=dict.get) would not — it can get stuck
    on whichever key it happens to visit first once the running best is NaN, since every NaN
    comparison is False)."""
    d = frame.copy()
    d["date"] = d["ts_ny"].dt.tz_localize(None).dt.normalize()
    ar_by_session = []
    for _, g in d.groupby("date"):
        s = g.set_index("mod")["close"].reindex(range(1440)).ffill()
        ar_by_session.append(s.diff().abs())
    prof = pd.concat(ar_by_session, axis=1).mean(axis=1)
    steps = pd.Series({c: prof.reindex(range(c, c + 15)).mean() - prof.reindex(range(c - 15, c)).mean() for c in candidates})
    return int(steps.idxmax()), steps.to_dict()


def dst_probe(feed, path):
    """Per year, January and July, on the UNFILTERED weekday frame: the sustained-step open
    must be 09:30 (not 08:30 or 10:30) in BOTH months. `ok` is decided by grid_step (Phase 6
    defect 2: open_step's raw |Δclose| is defeated by a feed with sparse pre-market prints); the
    step_* columns (open_step, ungridded) are still reported for comparability alongside the new
    gridstep_* columns (grid_step) and Thread B's detect_open."""
    d = _load(feed, path)
    d["mod"] = d["ts_ny"].dt.hour * 60 + d["ts_ny"].dt.minute
    d["year"], d["month"] = d["ts_ny"].dt.year, d["ts_ny"].dt.month
    sundays = d[d["ts_ny"].dt.dayofweek == 6]
    d = d[d["ts_ny"].dt.dayofweek < 5]
    rows = []
    for (y, m), g in d[d["month"].isin([1, 7])].groupby(["year", "month"]):
        if g["ts_ny"].dt.date.nunique() < 10:
            continue
        win, steps = open_step(g)
        gwin, gsteps = grid_step(g)
        om = detect_open(g)
        sun = sundays[(sundays["year"] == y) & (sundays["month"] == m)]
        first = sun.groupby(sun["ts_ny"].dt.date)["mod"].min()
        anchor = f"{int(first.mode().iat[0]) // 60:02d}:{int(first.mode().iat[0]) % 60:02d}" if len(first) else "n/a"
        rows.append(dict(feed=feed, year=y, month=m, step_open=f"{win // 60:02d}:{win % 60:02d}",
                         step_0830=round(steps[RTH_START - 60], 4), step_0930=round(steps[RTH_START], 4),
                         step_1030=round(steps[RTH_START + 60], 4),
                         gridstep_open=f"{gwin // 60:02d}:{gwin % 60:02d}",
                         gridstep_0830=round(gsteps[RTH_START - 60], 4), gridstep_0930=round(gsteps[RTH_START], 4),
                         gridstep_1030=round(gsteps[RTH_START + 60], 4), ok=gwin == RTH_START,
                         threadB_detect_open=f"{om // 60:02d}:{om % 60:02d}", sunday_first_bar=anchor,
                         sessions=g["ts_ny"].dt.date.nunique()))
    return pd.DataFrame(rows)


def _easter(year):
    a, b, c = year % 19, year // 100, year % 100
    d, e = b // 4, b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = c // 4, c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month = (h + l - 7 * m + 114) // 31
    day = (h + l - 7 * m + 114) % 31 + 1
    return pd.Timestamp(year, month, day)


def _observed(ts):
    if ts.dayofweek == 5:
        return ts - pd.Timedelta(days=1)
    if ts.dayofweek == 6:
        return ts + pd.Timedelta(days=1)
    return ts


def _nth_weekday(year, month, weekday, n):
    first = pd.Timestamp(year, month, 1)
    return first + pd.Timedelta(days=(weekday - first.dayofweek) % 7 + 7 * (n - 1))


def nyse_holidays(year):
    """Rule-based NYSE full-day holidays (Juneteenth observed from 2022)."""
    h = {"New Year": _observed(pd.Timestamp(year, 1, 1)),
         "MLK": _nth_weekday(year, 1, 0, 3), "Presidents": _nth_weekday(year, 2, 0, 3),
         "Good Friday": _easter(year) - pd.Timedelta(days=2),
         "Memorial": pd.Timestamp(year, 5, 31) - pd.Timedelta(days=(pd.Timestamp(year, 5, 31).dayofweek) % 7),
         "Independence": _observed(pd.Timestamp(year, 7, 4)), "Labor": _nth_weekday(year, 9, 0, 1),
         "Thanksgiving": _nth_weekday(year, 11, 3, 4), "Christmas": _observed(pd.Timestamp(year, 12, 25))}
    if year >= 2022:
        h["Juneteenth"] = _observed(pd.Timestamp(year, 6, 19))
    if _observed(pd.Timestamp(year, 1, 1)).year != year:   # New Year observed on Dec 31 of prior year
        h.pop("New Year")
    return {v.normalize(): k for k, v in h.items() if v.dayofweek < 5}


def calendar_reason(day):
    """Holiday / early close / known closure, else None (an ordinary trading day)."""
    ts = pd.Timestamp(day).normalize()
    hol = nyse_holidays(ts.year)
    if ts in hol:
        return f"holiday: {hol[ts]}"
    if ts.month == 11 and ts.dayofweek == 4 and (ts - pd.Timedelta(days=1)) in hol:
        return "early close: day after Thanksgiving"
    if ts.month == 12 and ts.day == 24 and ts.dayofweek < 5:
        return "early close: Christmas Eve"
    if ts.month == 7 and ts.day == 3 and ts.dayofweek < 5 and pd.Timestamp(ts.year, 7, 4).dayofweek != 5:
        return "early close: July 3"
    return KNOWN_CLOSURES.get(ts.strftime("%Y-%m-%d"))


def calendar_report(feed, frame, dropped):
    """Every dropped session and every kept session shorter than FULL_BARS. Reason is the
    calendar event when there is one; otherwise 'feed gap' (dropped on an ordinary trading
    day) or 'thin' (kept with 300..369 bars). The gate: no kept session may carry a calendar
    reason — a half day or holiday inside the sample would corrupt 'hold to the close'."""
    bars = frame.groupby("date").size()
    short = bars[bars < FULL_BARS].rename("bars").reset_index().assign(kept=True)
    rows = pd.concat([short, dropped.assign(kept=False)], ignore_index=True).sort_values("date")
    cal = [calendar_reason(x) for x in rows["date"]]
    rows["reason"] = [c if c else ("thin" if k else "feed gap") for c, k in zip(cal, rows["kept"])]
    rows.insert(0, "feed", feed)
    return rows.reset_index(drop=True)


def gate(feed, frame, dropped, probe, cal):
    """PASS/FAIL lines for Phase 2 gate (b)."""
    kept_cal = cal[cal["kept"] & cal["reason"].str.startswith(("holiday", "early", "closure"))]
    lines = [("DST probe: open at 09:30 in every Jan/Jul", bool(probe["ok"].all())),
             ("calendar: no kept session on a holiday/early-close/closure day", len(kept_cal) == 0),
             ("sessions: every kept session has >= 300 bars", bool((frame.groupby("date").size() >= MIN_BARS).all()))]
    return lines


if __name__ == "__main__":
    import os
    import sys
    feed, path = sys.argv[1], sys.argv[2]
    os.makedirs("out", exist_ok=True)
    frame, dropped = build(feed, path, trading_days_from_vix())
    probe = dst_probe(feed, path)
    cal = calendar_report(feed, frame, dropped)
    print(f"{feed}: {len(frame):,} RTH bars, {frame['date'].nunique():,} sessions, "
          f"{frame['date'].min().date()} -> {frame['date'].max().date()}, excluded {len(dropped)} sessions")
    print("DST probe: gridded step-open by month (decides ok):", probe["gridstep_open"].value_counts().to_dict(),
          "| legacy comparisons — ungridded step-open:", probe["step_open"].value_counts().to_dict(),
          "| Thread B detect_open:", probe["threadB_detect_open"].value_counts().to_dict())
    if (~probe["ok"]).any():
        print(probe[~probe["ok"]].to_string(index=False))
    print("calendar reasons:", cal["reason"].value_counts().to_dict())
    gaps = cal[cal["reason"] == "feed gap"]
    print(f"feed gaps (market open, <300 bars): {len(gaps)} sessions; by year: "
          f"{gaps.groupby(pd.to_datetime(gaps['date']).dt.year).size().to_dict()}")
    checks = gate(feed, frame, dropped, probe, cal)
    for name, ok in checks:
        print(f"[{'PASS' if ok else 'FAIL'}] {name}")
    probe.to_csv(f"out/dst_probe_{feed}.csv", index=False)
    cal.to_csv(f"out/calendar_{feed}.csv", index=False)
    if not all(ok for _, ok in checks):
        sys.exit(1)                                               # A52.4: run_all must see a failed gate
