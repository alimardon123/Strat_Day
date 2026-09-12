"""D4 — 0DTE pricing, risk and sizing tables for a trade table (COUPLED — single owner).

Every number is measured on the trades it is given (the caller labels the window: the D4
headline is the 2020-06→2026-09 holdout; anything else is IN-SAMPLE + HOLDOUT). Pricing per
ACCEPTANCE A7/A8/A28 via pipeline/options.py; sizing per the numeric budgets (worst-trade loss
with a 100% floor, intraday MAE, combined-book worst day) with the daily limit at 3/4/5%.
"""
import numpy as np
import pandas as pd

from pipeline import options

SPREADS = (1.0, 2.0, 3.0)
KS_1300 = (1.0, 1.3, 1.6)
LIMITS = (0.03, 0.04, 0.05)


def mae(frame, trades):
    """Worst intraday excursion of the UNDERLYING against each trade, in points and as a fraction
    of the option premium (delta ≈ 1 for 2% ITM): what a prop desk marks during the hold."""
    by_date = {d: g for d, g in frame.groupby("date")}
    out = []
    for r in trades.itertuples(index=False):
        g = by_date.get(pd.Timestamp(r.date))
        if g is None:
            out.append(np.nan)
            continue
        h = g[(g["mod"] >= r.entry_mod) & (g["mod"] <= r.exit_mod)]
        adverse = (h["low"].min() - r.entry_px) if r.direction > 0 else (r.entry_px - h["high"].max())
        out.append(min(float(adverse), 0.0))
    return np.array(out)


def price_table(trades, spread, settle, k, grid, exit_mod_spy=955, px_1555=None):
    """Option returns for one (spread, settlement, k). For settle="exit" (SPY) the trade is
    closed at 15:55: exit_px comes from `px_1555` (a Series indexed by date)."""
    t = trades.copy()
    if settle == "exit":
        t["exit_mod"] = exit_mod_spy
        t["exit_px"] = pd.Series(t["date"]).map(px_1555).to_numpy()
        t = t.dropna(subset=["exit_px"])
    return options.trade_table(t, k=k, itm=0.02, spread_pts=spread, grid=grid, settle=settle)


def summarise(o, years_span):
    """Return-on-premium statistics for one priced trade table."""
    if o.empty:
        return dict(n=0)
    r = o["opt_ret"]
    daily = o.groupby("date")["opt_ret"].sum()
    mae_frac = (o["mae_pts"] / o["premium"]).clip(lower=-1.0) if "mae_pts" in o else None   # an option cannot lose more than its premium
    return dict(n=len(o), trades_per_year=len(o) / years_span, win=100 * (r > 0).mean(), mean=100 * r.mean(),
                median=100 * r.median(), worst_trade=100 * r.min(), best_trade=100 * r.max(),
                worst_day=100 * daily.min(), premium_mean=o["premium"].mean(),
                mae_worst=100 * mae_frac.min() if mae_frac is not None else np.nan,
                full_loss_trades=int((r <= -0.999).sum()))


def sizing(o, limit, years_span):
    """Position size = limit ÷ worst-trade loss (floor 100% of premium) → expected annual return and
    worst year at that size, in % of account. Also the size at which the worst intraday MAE hits
    the limit."""
    worst = max(-o["opt_ret"].min(), 1.0)          # fraction of premium; hold-to-close has no stop → floor 100%
    size = limit / worst
    yr = o.assign(year=pd.to_datetime(o["date"]).dt.year).groupby("year")["opt_ret"].sum()
    daily = o.groupby("date")["opt_ret"].sum()
    worst_day = max(-daily.min(), 1.0)             # same signal firing once per day: equals worst trade
    return dict(limit=100 * limit, size_pct=100 * size, worst_trade_loss_pct=100 * worst,
                exp_annual_pct=100 * size * o["opt_ret"].sum() / years_span,
                worst_year_pct=100 * size * yr.min(), best_year_pct=100 * size * yr.max(),
                size_by_worst_day_pct=100 * limit / worst_day)


def build(frame, day, signals_by_name, window_label, grid="SPX", out_prefix="out/playbook"):
    """signals_by_name: {name: trade table}. Writes per-signal priced rows and a summary table."""
    px_1555 = day["dec_955"] if "dec_955" in day else None
    rows, sizes = [], []
    dates = pd.concat([t["date"] for t in signals_by_name.values()])
    years_span = max((pd.to_datetime(dates.max()) - pd.to_datetime(dates.min())).days / 365.25, 1e-9)
    book = []
    for name, t in signals_by_name.items():
        t = t.copy()
        t["mae_pts"] = mae(frame, t)
        ks = KS_1300 if int(t["decision_mod"].iloc[0]) == 780 else (1.0,)
        for spread in SPREADS:
            for settle in ("cash", "exit"):
                if settle == "exit" and px_1555 is None:
                    continue
                for k in ks:
                    o = price_table(t, spread, settle, k, options.GRID[grid] if settle == "cash" else options.GRID["SPY"], px_1555=px_1555)
                    if o.empty:
                        continue
                    o["mae_pts"] = t.set_index("date").loc[o["date"], "mae_pts"].to_numpy()
                    s = summarise(o, years_span)
                    s.update(signal=name, window=window_label, spread=spread, settle=settle, k=k)
                    rows.append(s)
                    if spread == 1.0 and settle == "cash" and k in (1.0, 1.3) and (k == 1.3 or ks == (1.0,)):
                        for lim in LIMITS:
                            z = sizing(o, lim, years_span)
                            z.update(signal=name, window=window_label, spread=spread, settle=settle, k=k)
                            sizes.append(z)
                        book.append(o[["date", "opt_ret", "premium"]].assign(signal=name))
                    o.to_csv(f"{out_prefix}_{name.replace('|', '_').replace('>', 'gt').replace('%', 'pct').replace(':', '')}_s{spread:.0f}_{settle}_k{k}.csv",
                             index=False, float_format="%.6f")
    summary = pd.DataFrame(rows)
    summary.to_csv(f"{out_prefix}_summary.csv", index=False, float_format="%.6f")
    sz = pd.DataFrame(sizes)
    if book:
        b = pd.concat(book)
        daily = b.groupby("date")["opt_ret"].sum()
        both = b.groupby("date")["signal"].nunique()
        worst_comb = max(-daily.min(), 1.0)
        combined = dict(signal="COMBINED BOOK", window=window_label, worst_trade_loss_pct=100 * worst_comb,
                        days_with_two_positions=int((both > 1).sum()),
                        worst_day_both_positions_pct=100 * daily[both > 1].min() if (both > 1).any() else np.nan)
        for lim in LIMITS:
            row = dict(combined, limit=100 * lim, size_pct=100 * lim / worst_comb,
                       exp_annual_pct=100 * (lim / worst_comb) * b["opt_ret"].sum() / years_span)
            sz = pd.concat([sz, pd.DataFrame([row])], ignore_index=True)
    sz.to_csv(f"{out_prefix}_sizing.csv", index=False, float_format="%.6f")
    return summary, sz
