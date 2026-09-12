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


def build(feed, path, trading_days=None):
    """Returns (rth_frame, dropped_sessions). rth_frame columns: ts_ny, date, mod, open, high,
    low, close, volume, feed. `date` is a tz-naive midnight Timestamp (merge-friendly).
    NYSE holidays are excluded even when a CFD feed prints bars on them, and so is any date
    outside `trading_days` (the VIX calendar) when given; dropped_sessions carries every
    excluded weekday with its bar count."""
    d = _load(feed, path)
    d["mod"] = d["ts_ny"].dt.hour * 60 + d["ts_ny"].dt.minute
    d["date"] = d["ts_ny"].dt.tz_localize(None).dt.normalize()
    d = d[(d["mod"] >= RTH_START) & (d["mod"] < RTH_END) & (d["ts_ny"].dt.dayofweek < 5)]
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
    08:30 or 10:30; a 1-3 minute economic release cannot sustain a 15-minute step."""
    d = frame.copy()
    d["ar"] = d["close"].diff().abs()
    prof = d.groupby("mod")["ar"].mean()
    steps = {c: prof.reindex(range(c, c + 15)).mean() - prof.reindex(range(c - 15, c)).mean() for c in candidates}
    return max(steps, key=steps.get), steps


def dst_probe(feed, path):
    """Per year, January and July, on the UNFILTERED weekday frame: the sustained-step open
    must be 09:30 (not 08:30 or 10:30) in BOTH months. Thread B's detect_open is reported too."""
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
        om = detect_open(g)
        sun = sundays[(sundays["year"] == y) & (sundays["month"] == m)]
        first = sun.groupby(sun["ts_ny"].dt.date)["mod"].min()
        anchor = f"{int(first.mode().iat[0]) // 60:02d}:{int(first.mode().iat[0]) % 60:02d}" if len(first) else "n/a"
        rows.append(dict(feed=feed, year=y, month=m, step_open=f"{win // 60:02d}:{win % 60:02d}",
                         step_0830=round(steps[RTH_START - 60], 4), step_0930=round(steps[RTH_START], 4),
                         step_1030=round(steps[RTH_START + 60], 4), ok=win == RTH_START,
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
    print("DST probe: step-open by month:", probe["step_open"].value_counts().to_dict(),
          "| Thread B detect_open:", probe["threadB_detect_open"].value_counts().to_dict())
    if (~probe["ok"]).any():
        print(probe[~probe["ok"]].to_string(index=False))
    print("calendar reasons:", cal["reason"].value_counts().to_dict())
    gaps = cal[cal["reason"] == "feed gap"]
    print(f"feed gaps (market open, <300 bars): {len(gaps)} sessions; by year: "
          f"{gaps.groupby(pd.to_datetime(gaps['date']).dt.year).size().to_dict()}")
    for name, ok in gate(feed, frame, dropped, probe, cal):
        print(f"[{'PASS' if ok else 'FAIL'}] {name}")
    probe.to_csv(f"out/dst_probe_{feed}.csv", index=False)
    cal.to_csv(f"out/calendar_{feed}.csv", index=False)
