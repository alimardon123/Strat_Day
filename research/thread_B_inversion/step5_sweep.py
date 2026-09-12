"""Broad hypothesis sweep over structural / behavioural market effects.

Every hypothesis is a conditional forward-return bet. All are tested together so the
multiple-comparison correction is honest about how many questions were asked.
"""
import numpy as np
import pandas as pd
from loader import load
from engine2 import to_5m, atr
from stats_engine import evaluate, block_bootstrap_p, bh_fdr, TRAIN_END

COST_OPTIMISTIC = 0.25   # ES futures, spread only — deliberately generous
HORIZONS = {"5m": 1, "15m": 3, "30m": 6, "60m": 12}


def build_features(b):
    s = b["session"]
    b["ret5"] = b["close"].diff()
    b["atr_ratio"] = b["atr"] / b["atr"].rolling(100).mean()

    # --- session context ---
    g = b.groupby(s)
    b["sess_open"] = g["open"].transform("first")
    b["sess_hi"] = g["high"].cummax()
    b["sess_lo"] = g["low"].cummin()
    b["bar_in_sess"] = g.cumcount()
    b["day_pos"] = (b["close"] - b["sess_open"]) / b["atr"]
    rng = (b["sess_hi"] - b["sess_lo"]).replace(0, np.nan)
    b["pos_in_range"] = (b["close"] - b["sess_lo"]) / rng
    b["running_mean"] = g["close"].transform(lambda x: x.expanding().mean())
    b["vwap_dev"] = (b["close"] - b["running_mean"]) / b["atr"]

    # --- overnight gap ---
    daily = b.groupby(s).agg(o=("open", "first"), c=("close", "last"))
    daily["gap"] = daily["o"] - daily["c"].shift(1)
    daily["prev_ret"] = daily["c"].diff().shift(0)
    daily["gap_z"] = daily["gap"] / daily["gap"].rolling(60).std()
    daily["prev_ret_z"] = daily["prev_ret"].shift(1) / daily["prev_ret"].rolling(60).std().shift(1)
    b = b.join(daily[["gap_z", "prev_ret_z"]], on="session")

    # --- opening range (first 30 min) ---
    first6 = b[b["bar_in_sess"] < 6].groupby(s).agg(or_hi=("high", "max"), or_lo=("low", "min"))
    b = b.join(first6, on="session")
    b["or_state"] = np.where(b["close"] > b["or_hi"], 1, np.where(b["close"] < b["or_lo"], -1, 0))
    b.loc[b["bar_in_sess"] < 6, "or_state"] = 0

    # --- round-number magnetism (human psychology, literally) ---
    for step in (25, 50, 100):
        near = (b["close"] % step)
        b[f"dist{step}"] = np.minimum(near, step - near) / b["atr"]
        b[f"above{step}"] = (near < step / 2).astype(int)

    # --- momentum / reversal at several scales ---
    for k, lbl in [(1, "1"), (3, "3"), (12, "12"), (36, "36")]:
        b[f"mom{lbl}"] = (b["close"] - b["close"].shift(k)) / b["atr"]
        b.loc[b["bar_in_sess"] < k, f"mom{lbl}"] = np.nan

    # --- run length of same-sign bars ---
    sign = np.sign(b["ret5"].fillna(0))
    grp = (sign != sign.shift()).cumsum()
    b["run_len"] = sign.groupby(grp).cumcount() + 1
    b["run_dir"] = sign

    # --- range expansion ---
    b["bar_range_z"] = (b["high"] - b["low"]) / b["atr"]

    # --- calendar ---
    ts = b["ts"]
    b["dow"] = ts.dt.dayofweek
    b["dom"] = ts.dt.day
    b["turn_of_month"] = ((b["dom"] >= 28) | (b["dom"] <= 3)).astype(int)

    # --- forward returns (points), truncated at session end ---
    for lbl, k in HORIZONS.items():
        f = b["close"].shift(-k) - b["close"]
        f[b["session"] != b["session"].shift(-k)] = np.nan
        b[f"fwd_{lbl}"] = f
    fclose = b.groupby(s)["close"].transform("last") - b["close"]
    b["fwd_close"] = fclose
    return b


def hypotheses(b):
    """Yield (name, boolean mask). Each is a structural/behavioural claim."""
    H = {}
    mod, br = b["minute_of_day"], b["bar_in_sess"]

    # time of day
    for lo, hi, nm in [(570, 600, "tod_open30"), (600, 660, "tod_0930_1030"),
                       (660, 780, "tod_late_morning"), (780, 870, "tod_midday"),
                       (870, 930, "tod_1430_1530"), (930, 961, "tod_last30")]:
        H[nm] = (mod >= lo) & (mod < hi)

    # calendar
    for d, nm in enumerate(["mon", "tue", "wed", "thu", "fri"]):
        H[f"dow_{nm}"] = b["dow"] == d
    H["turn_of_month"] = b["turn_of_month"] == 1
    H["mid_month"] = b["turn_of_month"] == 0

    # gap behaviour
    H["gap_up_big"] = b["gap_z"] > 1
    H["gap_dn_big"] = b["gap_z"] < -1
    H["gap_small"] = b["gap_z"].abs() < 0.3
    H["prev_day_up"] = b["prev_ret_z"] > 0.5
    H["prev_day_dn"] = b["prev_ret_z"] < -0.5

    # opening range
    H["or_broken_up"] = b["or_state"] == 1
    H["or_broken_dn"] = b["or_state"] == -1
    H["or_inside"] = (b["or_state"] == 0) & (br >= 6)

    # round numbers
    for step in (25, 50, 100):
        H[f"near_round{step}"] = b[f"dist{step}"] < 0.5
        H[f"far_round{step}"] = b[f"dist{step}"] > 2.0

    # momentum / reversal
    for lbl in ["1", "3", "12", "36"]:
        H[f"mom{lbl}_strong_up"] = b[f"mom{lbl}"] > 1.5
        H[f"mom{lbl}_strong_dn"] = b[f"mom{lbl}"] < -1.5
        H[f"mom{lbl}_flat"] = b[f"mom{lbl}"].abs() < 0.3

    # runs
    H["run_up_3plus"] = (b["run_len"] >= 3) & (b["run_dir"] > 0)
    H["run_dn_3plus"] = (b["run_len"] >= 3) & (b["run_dir"] < 0)
    H["run_up_5plus"] = (b["run_len"] >= 5) & (b["run_dir"] > 0)
    H["run_dn_5plus"] = (b["run_len"] >= 5) & (b["run_dir"] < 0)

    # volatility regime
    H["vol_quiet"] = b["atr_ratio"] < 0.8
    H["vol_high"] = b["atr_ratio"] > 1.3
    H["range_expansion"] = b["bar_range_z"] > 2.0

    # position in day
    H["at_day_high"] = b["pos_in_range"] > 0.95
    H["at_day_low"] = b["pos_in_range"] < 0.05
    H["mid_day_range"] = b["pos_in_range"].between(0.4, 0.6)
    H["far_above_vwap"] = b["vwap_dev"] > 1.5
    H["far_below_vwap"] = b["vwap_dev"] < -1.5

    # interactions worth asking about
    H["gap_up_and_or_up"] = (b["gap_z"] > 0.5) & (b["or_state"] == 1)
    H["gap_dn_and_or_dn"] = (b["gap_z"] < -0.5) & (b["or_state"] == -1)
    H["last30_above_vwap"] = (mod >= 930) & (b["vwap_dev"] > 0)
    H["last30_below_vwap"] = (mod >= 930) & (b["vwap_dev"] < 0)
    H["open30_gap_up"] = (mod < 600) & (b["gap_z"] > 0.5)
    H["open30_gap_dn"] = (mod < 600) & (b["gap_z"] < -0.5)
    return H


if __name__ == "__main__":
    m1 = load()
    b = to_5m(m1)
    b["atr"] = atr(b)
    b = build_features(b)
    b = b.dropna(subset=["atr", "fwd_30m"]).reset_index(drop=True)

    days = b["session"].to_numpy()
    ts = b["ts"].to_numpy()
    H = hypotheses(b)
    horizons = list(HORIZONS) + ["close"]
    print(f"conditions: {len(H)} | horizons: {len(horizons)} | TOTAL TESTS: {len(H)*len(horizons)}\n")

    results = []
    for hz in horizons:
        fwd = b[f"fwd_{hz}"].to_numpy(float)
        ok = ~np.isnan(fwd)
        for nm, mask in H.items():
            m = mask.to_numpy() & ok
            if m.sum() < 300:
                continue
            r = fwd[m]
            t_ = pd.Series(ts[m])
            tr = t_ < TRAIN_END
            if tr.sum() < 150 or (~tr).sum() < 100:
                continue
            d = 1 if r[tr.to_numpy()].mean() >= 0 else -1   # direction chosen on TRAIN only
            rr = r * d
            te = (~tr).to_numpy()
            results.append(dict(cond=nm, hz=hz, dir=d, n=int(m.sum()),
                                tr_mean=rr[tr.to_numpy()].mean(),
                                tr_t=rr[tr.to_numpy()].mean() / (rr[tr.to_numpy()].std() / np.sqrt(tr.sum())),
                                te_n=int(te.sum()), te_mean=rr[te].mean(),
                                te_t=rr[te].mean() / (rr[te].std() / np.sqrt(te.sum())),
                                _v=rr[te], _d=days[m][te]))

    res = pd.DataFrame(results)
    res.to_pickle("sweep_raw.pkl")
    print(f"tests actually run: {len(res)}")
    print(f"nominally significant on TEST at p<0.05 (|t|>1.96): {(res['te_t'].abs()>1.96).sum()}")
    print(f"  ...expected by pure chance: {0.05*len(res):.1f}")
    print(f"same sign train & test AND |test t|>1.96: {((np.sign(res['tr_mean'])==np.sign(res['te_mean'])) & (res['te_t'].abs()>1.96)).sum()}")
    print("\nNote: direction was fixed on TRAIN, so test t>0 is the only valid direction.")
    print(f"test t > +1.96 (correct direction held out-of-sample): {(res['te_t']>1.96).sum()}")
