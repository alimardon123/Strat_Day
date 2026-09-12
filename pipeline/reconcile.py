"""D1 — reconcile the last-hour momentum specification (COUPLED — single owner).

Implements ACCEPTANCE.md "Decision rule for D1" v2 exactly:
  * 16 configurations = {15:00, 15:30} × {put-only, both} × {mag, vixmove_exp, vixmove_fixed,
    vixmove_lit}; the 12 without the literal thresholds are rankable.
  * Selection window 2013-01-01 → 2020-05-13 on Oanda SPX500_USD, America/New_York sessions,
    wall-clock decision times, next-bar entry, exit at the last close.
  * Unit: underlying index points per trade net of 1.0 pt round trip (percent shown too).
  * Ranking metric: annualised Sharpe of the calendar-day net-% P&L series (zeros on non-trade
    days); ties within 0.10 → fewer parameters.
  * Inference on the window: one-sided month-block bootstrap p, BH-FDR across all 16, the
    day-selection control (200 seeds), the timing control (reported), DSR at N = 12 and at
    the historical N = 42.
  * The top-ranked configuration is PRE-REGISTERED in out/reconcile_decision.md before any
    holdout data is read. Thread A's gap-up call is pre-registered by Thread A itself.
Outputs: out/reconcile_candidates.csv, out/reconcile_decision.md, out/trials.csv
"""
import os

import numpy as np
import pandas as pd

from pipeline import sessions, signals, stats

SEL_START, SEL_END = "2013-01-01", "2020-05-13"
COST_PTS = 1.0
N_HIST = 42          # 16 this run + 4 it22 setups + 22 step17 tests (ACCEPTANCE survival rule 5)
PARAMS = {"mag": 1, "vixmove_exp": 2, "vixmove_fixed": 2, "vixmove_lit": 2}


def window_stats(name, t, day, frame, entry_mod, direction, gate, all_dates, sr_pool):
    w = t[(t["date"] >= SEL_START) & (t["date"] <= SEL_END)].copy()
    w["net_pts"] = w["pts"] - COST_PTS
    w["net_pct"] = w["ret_pct"] - 100 * COST_PTS / w["entry_px"]
    row = dict(candidate=name, entry=f"{entry_mod // 60:02d}:{entry_mod % 60:02d}", direction=direction, gate=gate,
               rankable=gate in signals.RANKABLE, params=PARAMS[gate] + (1 if direction == "put" else 0),
               n=len(w), trades_per_year=len(w) / 7.37, win=100 * (w["pts"] > 0).mean() if len(w) else np.nan,
               gross_pts=w["pts"].mean() if len(w) else np.nan, net_pts=w["net_pts"].mean() if len(w) else np.nan,
               net_pct=w["net_pct"].mean() if len(w) else np.nan, worst_pts=w["net_pts"].min() if len(w) else np.nan)
    if len(w) >= 20:
        row["p_boot_month"] = stats.one_sided_p(w["net_pct"].to_numpy(), stats.month_blocks(w["date"]))
        row["p_boot_day"] = stats.one_sided_p(w["net_pct"].to_numpy(), stats.day_blocks(w["date"]))
        row["sharpe_calday"] = stats.calendar_day_sharpe(w["net_pct"].to_numpy(), w["date"], all_dates)
        row["sr_trade"] = stats.per_trade_sharpe(w["net_pct"].to_numpy())
        row["sharpe_threadB_conv"] = stats.sharpe(w["net_pct"].to_numpy(), 252)   # per-trade x sqrt(252), as step17:77 — inflates by sqrt(252 / trades per year)
        ctrl = signals.day_selection_control(day.loc[SEL_START:SEL_END], w, entry_mod, direction)
        ctrl_net = ctrl - 100 * COST_PTS / w["entry_px"].mean()
        row["control_mean_pct"] = ctrl_net.mean() if len(ctrl) else np.nan
        row["excess_over_control_pct"] = row["net_pct"] - row["control_mean_pct"]
        row["frac_seeds_beaten"] = (w["net_pct"].mean() > ctrl_net).mean() if len(ctrl) else np.nan
        tim = signals.timing_control(frame[(frame["date"] >= SEL_START) & (frame["date"] <= SEL_END)], w, n_seeds=50)
        row["timing_control_pct"] = np.nanmean(tim) - 100 * COST_PTS / w["entry_px"].mean()
    else:
        for k in ("p_boot_month", "p_boot_day", "sharpe_calday", "sr_trade", "sharpe_threadB_conv", "control_mean_pct",
                  "excess_over_control_pct", "frac_seeds_beaten", "timing_control_pct"):
            row[k] = np.nan
    return row, w


def main():
    os.makedirs("out", exist_ok=True)
    vix = pd.read_parquet("data/raw/vix_daily.parquet")
    frame, _ = sessions.build("oanda", "data/raw/oanda_SPX500_USD.parquet", sessions.trading_days_from_vix())
    day = signals.day_table(frame, vix)
    fixed = {e: signals.fixed_thresholds(day, e) for e in (900, 930)}
    all_dates = day.loc[SEL_START:SEL_END].index
    rows, trades = [], {}
    for e, d, g in signals.CANDIDATES:
        t = signals.candidate(day, e, d, g, fixed=fixed.get(e))
        name = signals.label(e, d, g)
        row, w = window_stats(name, t, day, frame, e, d, g, all_dates, None)
        rows.append(row)
        trades[name] = w
    res = pd.DataFrame(rows)
    # multiple testing across all 16 trials; DSR uses the dispersion of the rankable trials' per-trade Sharpes
    pv = res["p_boot_month"].fillna(1.0).to_numpy()
    res["fdr_pass_10pct"] = stats.bh_fdr(pv, alpha=0.10)
    sr_pool = res.loc[res["rankable"], "sr_trade"].dropna().to_numpy()
    for i, r in res.iterrows():
        w = trades[r["candidate"]]
        if len(w) >= 20:
            res.loc[i, "dsr_N12"] = stats.deflated_sharpe(w["net_pct"].to_numpy(), sr_pool)[0]
            res.loc[i, "dsr_N42"] = stats.deflated_sharpe(w["net_pct"].to_numpy(), np.resize(sr_pool, N_HIST))[0]
    # ranking
    rk = res[res["rankable"]].sort_values(["sharpe_calday"], ascending=False).reset_index(drop=True)
    best = rk.iloc[0]
    tied = rk[(best["sharpe_calday"] - rk["sharpe_calday"]) <= 0.10]
    winner = tied.sort_values(["params", "sharpe_calday"], ascending=[True, False]).iloc[0]
    res["rank"] = res["candidate"].map({c: i + 1 for i, c in enumerate(rk["candidate"])})
    res["winner"] = res["candidate"] == winner["candidate"]
    res = res.sort_values(["rankable", "rank"], ascending=[False, True])
    res.to_csv("out/reconcile_candidates.csv", index=False, float_format="%.6f")
    pd.concat([w.assign(candidate=n) for n, w in trades.items()]).to_csv("out/reconcile_trades_selection.csv", index=False, float_format="%.6f")
    res[["candidate", "n", "p_boot_month", "fdr_pass_10pct", "sr_trade", "dsr_N12", "dsr_N42"]].to_csv("out/trials.csv", index=False, float_format="%.6f")

    lines = ["# out/reconcile_decision.md — D1 pre-registration", "",
             f"Selection window {SEL_START} → {SEL_END}, Oanda SPX500_USD, America/New_York sessions, cost {COST_PTS} pt.",
             f"vixmove_fixed thresholds (Oanda 2005-2012 upper terciles): 15:00 VIX>{fixed[900][0]:.2f} & |move|>{fixed[900][1]:.3f}%; "
             f"15:30 VIX>{fixed[930][0]:.2f} & |move|>{fixed[930][1]:.3f}%.", "",
             "## Ranking of the 12 rankable configurations (calendar-day Sharpe, net of cost)", "",
             rk[["candidate", "n", "win", "net_pts", "net_pct", "sharpe_calday", "sharpe_threadB_conv", "p_boot_month", "p_boot_day",
                 "fdr_pass_10pct", "excess_over_control_pct", "frac_seeds_beaten", "dsr_N12", "dsr_N42"]].to_string(index=False, float_format=lambda x: f"{x:.4f}"), "",
             "p_boot_month is NA when the trades span fewer than 20 calendar months (survival rule 2); p_boot_day is the",
             "one-observation-per-day bootstrap. sharpe_threadB_conv is per-trade Sharpe × √252 (step17_intramom.py:77), which",
             "overstates the annualised figure by √(252 / trades per year); sharpe_calday is the ranking metric.", "",
             "## Literal-threshold rows (Thread B's 17.06 / 0.665 — in-sample on 2013-2018; reported, not ranked)", "",
             res[~res["rankable"]][["candidate", "n", "win", "net_pts", "net_pct", "sharpe_calday", "sharpe_threadB_conv", "p_boot_month", "p_boot_day"]].to_string(index=False, float_format=lambda x: f"{x:.4f}"), "",
             "## PRE-REGISTERED holdout test", "",
             f"Winner: **{winner['candidate']}** (rank {int(res.loc[res['candidate'] == winner['candidate'], 'rank'].iat[0])}; "
             f"ties within 0.10 Sharpe resolved by parameter count: {len(tied)} tied).",
             "This ONE configuration is tested on the 2020-06-01 → 2026-09-11 holdout when data/ext arrives. Thread A's gap-up call "
             "(13:00, gap > 0.3%) is the second pre-registered holdout signal. All other configurations' holdout rows will be "
             "published labelled POST-SELECTION and never promoted.", "",
             f"Written before any holdout data was read. Trials counted this run: {len(res)}; historical N for DSR: {N_HIST}."]
    with open("out/reconcile_decision.md", "w") as f:
        f.write("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
