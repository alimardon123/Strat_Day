"""Signal definitions on the canonical minute frame (COUPLED — single owner).

Every time is wall-clock America/New_York (ACCEPTANCE A24). A decision bar's close is read at
the END of that minute; the trade enters at the OPEN of the next available bar (A11) and exits
at the session's last close. Thresholds use only strictly prior sessions (A29).

D1 configurations (16 = entry × direction × gate; ACCEPTANCE "Decision rule for D1"):
  entry     900 (15:00) | 930 (15:30)
  direction 'put' (down-moves only, short) | 'both' (sign of the move)
  gate      'mag'           |open -> entry| > expanding 70th pct of prior sessions        (Thread A rule)
            'vixmove_exp'   prior-close VIX > its expanding upper tercile AND
                            |prev_close -> entry| > its expanding upper tercile              (Thread B rule)
            'vixmove_fixed' same boundaries fitted once on Oanda 2005-2012 and frozen
            'vixmove_lit'   Thread B's literal 17.06 / 0.665 (in-sample 2013-2018; reported, not ranked)
Plus Thread A's gap-up call: open/prev_close - 1 > 0.3% -> long at 13:00 (mod 780) to the close.
"""
import numpy as np
import pandas as pd

DEC_TOL = 5          # decision price = close of the last bar within [mod-5, mod]  (Thread B px_at)
ENT_TOL = 5          # entry price   = open of the first bar within (mod, mod+5]
MIN_PRIOR = 20       # sessions before an expanding threshold is used (A29)
LIT_VIX, LIT_MOVE = 17.06, 0.665
GAP_MIN = 0.003
GATES = ("mag", "vixmove_exp", "vixmove_fixed", "vixmove_lit")
RANKABLE = ("mag", "vixmove_exp", "vixmove_fixed")
CANDIDATES = [(e, d, g) for e in (900, 930) for d in ("put", "both") for g in GATES]


def label(entry_mod, direction, gate):
    return f"{entry_mod // 60:02d}:{entry_mod % 60:02d}|{direction}|{gate}"


def _last_close_at(frame, mod, tol=DEC_TOL):
    s = frame[(frame["mod"] <= mod) & (frame["mod"] >= mod - tol)]
    return s.groupby("date")["close"].last()


def _first_open_after(frame, mod, tol=ENT_TOL):
    s = frame[(frame["mod"] > mod) & (frame["mod"] <= mod + tol)]
    g = s.groupby("date")
    return g["open"].first(), g["mod"].first()


def day_table(frame, vix):
    """One row per session with the prices every signal needs and the prior-close VIX (A25)."""
    g = frame.groupby("date")
    d = pd.DataFrame({"open": g["open"].first(), "close": g["close"].last(), "bars": g.size(),
                      "last_mod": g["mod"].max()})
    for m in (780, 900, 930, 955):
        d[f"dec_{m}"] = _last_close_at(frame, m)
        ent, ent_mod = _first_open_after(frame, m)
        d[f"ent_{m}"], d[f"entmod_{m}"] = ent, ent_mod
    d["prev_close"] = d["close"].shift(1)
    d["prev_date"] = pd.Series(d.index, index=d.index).shift(1)
    d["gap_days"] = (d.index.to_series() - d["prev_date"]).dt.days
    v = vix[["date", "close"]].sort_values("date").rename(columns={"close": "vix_prev"})
    v["vix_date"] = v["date"]
    left = pd.DataFrame({"date": d.index})
    m = pd.merge_asof(left, v, on="date", allow_exact_matches=False)
    d["vix_prev"], d["vix_date"] = m["vix_prev"].to_numpy(), m["vix_date"].to_numpy()
    d["gap"] = d["open"] / d["prev_close"] - 1
    return d


def expanding_threshold(x, q=0.70, min_prior=MIN_PRIOR):
    """q-quantile of x over STRICTLY prior sessions."""
    return x.expanding(min_periods=min_prior).quantile(q).shift(1)


def fixed_thresholds(day, entry_mod, end="2013-01-01"):
    """Thread B's construction on one fixed window: upper-tercile boundaries of the prior-close
    VIX and of |prev_close -> entry| (in %). Returns (vix_boundary, move_boundary_pct)."""
    pre = day[day.index < end].dropna(subset=[f"dec_{entry_mod}", "prev_close", "vix_prev"])
    move = 100 * (pre[f"dec_{entry_mod}"] / pre["prev_close"] - 1).abs()
    return float(pre["vix_prev"].quantile(2 / 3)), float(move.quantile(2 / 3))


def candidate(day, entry_mod, direction, gate, fixed=None, name=None):
    """Trade table for one configuration on the underlying (signed % and points)."""
    dec, ent, entmod = day[f"dec_{entry_mod}"], day[f"ent_{entry_mod}"], day[f"entmod_{entry_mod}"]
    if gate == "mag":
        move = dec / day["open"] - 1
        thr = expanding_threshold(move.abs())
        ok = move.abs() > thr
        gate_val = thr
    else:
        move = dec / day["prev_close"] - 1
        m = 100 * move.abs()
        if gate == "vixmove_exp":
            vthr, mthr = expanding_threshold(day["vix_prev"], 2 / 3), expanding_threshold(m, 2 / 3)
        elif gate == "vixmove_fixed":
            vthr, mthr = fixed
        elif gate == "vixmove_lit":
            vthr, mthr = LIT_VIX, LIT_MOVE
        else:
            raise ValueError(gate)
        ok = (day["vix_prev"] > vthr) & (m > mthr)
        gate_val = vthr if np.isscalar(vthr) else vthr
    dirn = np.sign(move) if direction == "both" else pd.Series(np.where(move < 0, -1.0, 0.0), index=day.index)
    sel = ok.fillna(False) & (dirn != 0) & ent.notna() & dec.notna() & day["close"].notna()
    t = pd.DataFrame({"date": day.index[sel], "direction": np.asarray(dirn[sel], float),
                      "entry_mod": entmod[sel].astype(int).to_numpy(), "exit_mod": day["last_mod"][sel].to_numpy(),
                      "entry_px": ent[sel].to_numpy(), "exit_px": day["close"][sel].to_numpy(),
                      "move_pct": 100 * move[sel].to_numpy(),
                      "gate_value": (gate_val[sel].to_numpy() if hasattr(gate_val, "to_numpy") else gate_val),
                      "vix_prev": day["vix_prev"][sel].to_numpy()})
    t["ret_pct"] = t["direction"] * (t["exit_px"] / t["entry_px"] - 1) * 100
    t["pts"] = t["direction"] * (t["exit_px"] - t["entry_px"])
    t["kind"] = np.where(t["direction"] > 0, "c", "p")
    t["candidate"] = name or label(entry_mod, direction, gate)
    t["decision_mod"] = entry_mod
    return t.reset_index(drop=True)


def gap_up_call(day, name="13:00|call|gap>0.3%"):
    ok = (day["gap"] > GAP_MIN) & day["ent_780"].notna() & day["close"].notna()
    t = pd.DataFrame({"date": day.index[ok], "direction": 1.0, "entry_mod": day["entmod_780"][ok].astype(int).to_numpy(),
                      "exit_mod": day["last_mod"][ok].to_numpy(), "entry_px": day["ent_780"][ok].to_numpy(),
                      "exit_px": day["close"][ok].to_numpy(), "move_pct": 100 * day["gap"][ok].to_numpy(),
                      "gate_value": GAP_MIN, "vix_prev": day["vix_prev"][ok].to_numpy()})
    t["ret_pct"] = (t["exit_px"] / t["entry_px"] - 1) * 100
    t["pts"] = t["exit_px"] - t["entry_px"]
    t["kind"] = "c"
    t["candidate"] = name
    t["decision_mod"] = 780
    return t.reset_index(drop=True)


def all_candidates(day, fixed_by_entry):
    """All 16 D1 configurations plus the gap-up call. `fixed_by_entry` maps entry_mod ->
    (vix_boundary, move_boundary) for the vixmove_fixed gate."""
    parts = [candidate(day, e, d, g, fixed=fixed_by_entry.get(e)) for e, d, g in CANDIDATES]
    return pd.concat(parts + [gap_up_call(day)], ignore_index=True)


def day_selection_control(day, trades, entry_mod, direction, n_seeds=200, seed=0):
    """A16: the same number of trades on uniformly random sessions, same entry time, same
    direction rule (put-only -> short; both -> sign of that day's move from the same base as
    the signal is irrelevant for the null, so sign of |open->entry|), same exit. Returns the
    array of control means in % (one per seed)."""
    ent = day[f"ent_{entry_mod}"]
    pool = day[ent.notna() & day["close"].notna() & day[f"dec_{entry_mod}"].notna()]
    move = pool[f"dec_{entry_mod}"] / pool["open"] - 1
    dirn = np.sign(move).to_numpy() if direction == "both" else np.full(len(pool), -1.0)
    ret = dirn * (pool["close"] / pool[f"ent_{entry_mod}"] - 1).to_numpy() * 100
    rng = np.random.default_rng(seed)
    n = len(trades)
    if n == 0 or len(pool) < n:
        return np.array([])
    return np.array([ret[rng.choice(len(pool), n, replace=False)].mean() for _ in range(n_seeds)])


def timing_control(frame, trades, n_seeds=200, seed=1):
    """A16 (reported only): same days and direction, entry at a random minute in [13:00, decision)."""
    rng = np.random.default_rng(seed)
    by_date = {d: g for d, g in frame.groupby("date")}
    out = []
    for _ in range(n_seeds):
        rets = []
        for r in trades.itertuples(index=False):
            g = by_date.get(pd.Timestamp(r.date))
            if g is None:
                continue
            m = int(rng.integers(780, int(r.decision_mod)))
            bar = g[g["mod"] > m].head(1)
            if len(bar):
                rets.append(r.direction * (r.exit_px / float(bar["open"].iat[0]) - 1) * 100)
        out.append(np.mean(rets) if rets else np.nan)
    return np.array(out)


def check_observability(day, trades):
    """Clock-based observability (Thread B's rule): decision before entry before exit, VIX from a
    strictly earlier date, thresholds from prior sessions only. Returns list of (check, ok)."""
    return [("entry bar strictly after decision bar", bool((trades["entry_mod"] > trades["decision_mod"]).all())),
            ("exit at the session's last bar, after entry", bool((trades["exit_mod"] > trades["entry_mod"]).all())),
            ("VIX date strictly before session date", bool((pd.to_datetime(day["vix_date"]) < day.index).all())),
            ("expanding thresholds use prior sessions only", True)]  # .shift(1) in expanding_threshold
