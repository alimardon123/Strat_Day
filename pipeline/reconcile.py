"""D1 — reconcile the last-hour momentum specification (COUPLED — single owner).

Implements ACCEPTANCE.md "Decision rule for D1" v2 exactly:
  * 16 configurations = {15:00, 15:30} × {put-only, both} × {mag, vixmove_exp, vixmove_fixed,
    vixmove_lit}; the 12 without the literal thresholds are rankable.
  * Selection window 2013-01-01 → 2020-05-13 on the extended frame (Oanda, plus the ext feed
    when present — the window filter excludes it), America/New_York sessions, wall-clock
    decision times, next-bar entry, exit at the last close.
  * Unit: underlying index points per trade net of 1.0 pt round trip; the ranking metric is the
    annualised Sharpe of the calendar-day net-% P&L series over NYSE trading days (zeros on
    non-trade days) — % so a price level that doubled over the window does not weight late
    trades (logged amendment, CHANGELOG); ties within 0.10 → fewer FITTED parameters (expanding
    rules are rules, not parameters: mag 0, vixmove_exp 0, vixmove_fixed 2 — Phase 4 defect 2).
  * Inference on the window: one-sided month- and day-block bootstrap p, BH-FDR within the
    16 (the family-wide FDR is in pipeline/trials.py), the day-selection control with the
    signal's own direction base (200 seeds), the timing control (reported), DSR at N = 12 and
    N = 42 with an explicit N (no resampling of the trial pool).
  * The top-ranked configuration is PRE-REGISTERED in out/reconcile_decision.md before any
    holdout data is read. Thread A's gap-up call is pre-registered by Thread A itself and gets
    the same table row (PSR at N = 1; DSR at N = 1,099 using the 12-config dispersion).
Outputs: out/reconcile_candidates.csv, out/reconcile_decision.md, out/reconcile_trials.csv,
         out/reconcile_trades_selection.csv, out/reconcile_ref_report.csv
"""
import os
import sys

import numpy as np
import pandas as pd

from pipeline import insample, sessions, signals, stats

SEL_START, SEL_END = "2013-01-01", "2020-05-13"
HOLD_START, HOLD_END = "2020-06-01", "2026-09-11"   # D1's post-selection publication window (ACCEPTANCE line ~92);
                                                     # D2's own pre-registered test is pipeline/insample.py
COST_PTS = 1.0
N_HIST = 42          # 16 this run + 4 it22 setups + 22 step17 tests (ACCEPTANCE survival rule 5)
N_GAP_HIST = 1099    # 1,092 scan cells + 6 conditions + 1
PARAMS = {"mag": 0, "vixmove_exp": 0, "vixmove_fixed": 2, "vixmove_lit": 2}   # FITTED numbers only


def window_stats(name, t, day, frame, entry_mod, direction, base, all_dates, years, win_start=SEL_START, win_end=SEL_END):
    w = t[(t["date"] >= win_start) & (t["date"] <= win_end)].copy()
    w["net_pts"] = w["pts"] - COST_PTS
    w["net_pct"] = w["ret_pct"] - 100 * COST_PTS / w["entry_px"]
    row = dict(candidate=name, n=len(w), trades_per_year=len(w) / years,
               win=100 * (w["pts"] > 0).mean() if len(w) else np.nan,
               gross_pts=w["pts"].mean() if len(w) else np.nan, net_pts=w["net_pts"].mean() if len(w) else np.nan,
               net_pct=w["net_pct"].mean() if len(w) else np.nan, worst_pts=w["net_pts"].min() if len(w) else np.nan)
    keys = ("p_boot_month", "p_boot_day", "sharpe_calday", "sr_trade", "sharpe_threadB_conv", "control_mean_pct",
            "excess_over_control_pct", "frac_seeds_beaten", "timing_control_pct")
    if len(w) >= 20:
        row["p_boot_month"] = stats.one_sided_p(w["net_pct"].to_numpy(), stats.month_blocks(w["date"]))
        row["p_boot_day"] = stats.one_sided_p(w["net_pct"].to_numpy(), stats.day_blocks(w["date"]))
        row["sharpe_calday"] = stats.calendar_day_sharpe(w["net_pct"].to_numpy(), w["date"], all_dates)
        row["sr_trade"] = stats.per_trade_sharpe(w["net_pct"].to_numpy())
        row["sharpe_threadB_conv"] = stats.sharpe(w["net_pct"].to_numpy(), 252)
        ctrl = signals.day_selection_control(day.loc[win_start:win_end], w, entry_mod, direction, base=base)
        ctrl_net = ctrl - 100 * COST_PTS / w["entry_px"].mean()
        row["control_mean_pct"] = ctrl_net.mean() if len(ctrl) else np.nan
        row["excess_over_control_pct"] = row["net_pct"] - row["control_mean_pct"]
        row["frac_seeds_beaten"] = (w["net_pct"].mean() > ctrl_net).mean() if len(ctrl) else np.nan
        tim = signals.timing_control(frame[(frame["date"] >= win_start) & (frame["date"] <= win_end)], w, n_seeds=50)
        row["timing_control_pct"] = np.nanmean(tim) - 100 * COST_PTS / w["entry_px"].mean()
    else:
        for k in keys:
            row[k] = np.nan
    return row, w


def holdout_main():
    """D1's post-selection publication (ACCEPTANCE line ~92, N2): the same window_stats row for
    all 16 momentum configurations (12 rankable + 4 literal) on the 2020-06-01..2026-09-11
    window, appended to out/reconcile_candidates.csv with `window`/`label` columns. Expanding
    gates (mag, vixmove_exp) keep expanding through the holdout using strictly prior sessions
    (a rule, not a fit); vixmove_fixed keeps the pre-2013 fit (fixed_thresholds' `end` default is
    2013-01-01, unaffected by the window); vixmove_lit keeps the literal 17.06/0.665. Never
    re-ranked — these rows carry no `rank` — and never added to the trial family in
    pipeline/trials.py (they are never promoted). Thread A's gap-up call is not re-published here:
    it is Thread A's own pre-registered signal and its holdout test is pipeline/insample.py's D2."""
    cand_path = "out/reconcile_candidates.csv"
    if not sessions.ext_present():
        print("data/ext absent — `pipeline.reconcile holdout` is a no-op (DATA.md)")
        return
    if not os.path.exists(cand_path):
        raise FileNotFoundError(f"{cand_path} missing — run `python -m pipeline.reconcile` (in-sample) first")
    existing = pd.read_csv(cand_path)
    vix = pd.read_parquet("data/raw/vix_daily.parquet")
    td = sessions.trading_days_from_vix()
    frame, _, meta = sessions.build_extended(trading_days=td)
    day = signals.day_table(frame, vix, dividends=meta["dividends"] if meta else None, trading_days=td,
                            roll_dates=meta["roll_dates"] if meta else ())
    fixed = {e: signals.fixed_thresholds(day, e) for e in (900, 930)}   # pre-2013 fit, exactly as constructed for the in-sample run
    all_dates = [d for d in td if pd.Timestamp(HOLD_START) <= d <= pd.Timestamp(HOLD_END)]
    years = (pd.Timestamp(HOLD_END) - pd.Timestamp(HOLD_START)).days / 365.25
    rows = []
    for e, d, g in signals.CANDIDATES:
        t = signals.candidate(day, e, d, g, fixed=fixed.get(e))
        name = signals.label(e, d, g)
        row, _ = window_stats(name, t, day, frame, e, d, signals.gate_base(g), all_dates, years, win_start=HOLD_START, win_end=HOLD_END)
        row.update(entry=f"{e // 60:02d}:{e % 60:02d}", direction=d, gate=g, rankable=g in signals.RANKABLE,
                   params=PARAMS[g], family="momentum")
        rows.append(row)
    hold = pd.DataFrame(rows)
    winner_name = insample.winner_from_decision()
    hold["window"] = f"{HOLD_START}..{HOLD_END}"
    hold["label"] = np.where(hold["candidate"] == winner_name, "PRE-REGISTERED", "POST-SELECTION")
    # POST-SELECTION rows are published for transparency only, per ACCEPTANCE's decision rule; they carry no `rank`
    # and are NOT added to pipeline/trials.py's trial family (D6/A31) — never promoted.
    out = pd.concat([existing, hold], ignore_index=True, sort=False)
    out.to_csv(cand_path, index=False, float_format="%.6f")
    print(f"holdout rows appended: {len(hold)} configurations on {HOLD_START}..{HOLD_END}; PRE-REGISTERED: {winner_name}")


def main(mode="insample"):
    os.makedirs("out", exist_ok=True)
    if mode == "holdout":
        holdout_main()
        return
    vix = pd.read_parquet("data/raw/vix_daily.parquet")
    td = sessions.trading_days_from_vix()
    frame, _, meta = sessions.build_extended(trading_days=td)
    day = signals.day_table(frame, vix, dividends=meta["dividends"] if meta else None, trading_days=td,
                            roll_dates=meta["roll_dates"] if meta else ())
    pd.DataFrame([signals.ref_report(day.loc[SEL_START:SEL_END])]).to_csv("out/reconcile_ref_report.csv", index=False)
    fixed = {e: signals.fixed_thresholds(day, e) for e in (900, 930)}
    all_dates = [d for d in td if pd.Timestamp(SEL_START) <= d <= pd.Timestamp(SEL_END)]
    years = (pd.Timestamp(SEL_END) - pd.Timestamp(SEL_START)).days / 365.25
    rows, trades = [], {}
    for e, d, g in signals.CANDIDATES:
        t = signals.candidate(day, e, d, g, fixed=fixed.get(e))
        name = signals.label(e, d, g)
        row, w = window_stats(name, t, day, frame, e, d, signals.gate_base(g), all_dates, years)
        row.update(entry=f"{e // 60:02d}:{e % 60:02d}", direction=d, gate=g, rankable=g in signals.RANKABLE,
                   params=PARAMS[g], family="momentum")
        rows.append(row)
        trades[name] = w
    gap = signals.gap_up_call(day)
    grow, gw = window_stats("13:00|call|gap>0.3%", gap, day, frame, 780, "both", "prev_close", all_dates, years)
    grow.update(entry="13:00", direction="call", gate="gap>0.3%", rankable=False, params=1, family="gapup")
    res = pd.DataFrame(rows + [grow])
    trades["13:00|call|gap>0.3%"] = gw
    # multiple testing within the 16 momentum trials (family-wide FDR incl. gap-up, xmarket, flow: pipeline/trials.py)
    mom = res["family"] == "momentum"
    res.loc[mom, "fdr_pass_10pct_within16"] = stats.bh_fdr(res.loc[mom, "p_boot_month"].fillna(1.0).to_numpy(), alpha=0.10)
    sr_pool = res.loc[res["rankable"], "sr_trade"].dropna().to_numpy()
    for i, r in res.iterrows():
        w = trades[r["candidate"]]
        if len(w) >= 20:
            x = w["net_pct"].to_numpy()
            if r["family"] == "momentum":
                res.loc[i, "dsr_N12"] = stats.deflated_sharpe(x, sr_pool, n=12)[0]
                res.loc[i, "dsr_N42"] = stats.deflated_sharpe(x, sr_pool, n=N_HIST)[0]
            else:
                res.loc[i, "dsr_N12"] = stats.deflated_sharpe(x, sr_pool, n=1)[0]          # PSR: pre-registered
                res.loc[i, "dsr_N42"] = stats.deflated_sharpe(x, sr_pool, n=N_GAP_HIST)[0]  # historical N, 12-config dispersion
    # ranking
    rk = res[res["rankable"]].sort_values("sharpe_calday", ascending=False).reset_index(drop=True)
    best = rk.iloc[0]
    tied = rk[(best["sharpe_calday"] - rk["sharpe_calday"]) <= 0.10]
    winner = tied.sort_values(["params", "sharpe_calday"], ascending=[True, False]).iloc[0]
    res["rank"] = res["candidate"].map({c: i + 1 for i, c in enumerate(rk["candidate"])})
    res["winner"] = res["candidate"] == winner["candidate"]
    res = res.sort_values(["family", "rankable", "rank"], ascending=[False, False, True])
    res["window"] = f"{SEL_START}..{SEL_END}"
    # the gap-up call is pre-registered by Thread A itself, not chosen by this ranking (see module docstring)
    res["label"] = np.where(res["family"] == "gapup", "PRE-REGISTERED", "SELECTION")
    res.to_csv("out/reconcile_candidates.csv", index=False, float_format="%.6f")
    pd.concat([w.assign(candidate=n) for n, w in trades.items()]).to_csv("out/reconcile_trades_selection.csv", index=False, float_format="%.6f")
    res[["candidate", "family", "n", "p_boot_month", "p_boot_day", "sr_trade", "dsr_N12", "dsr_N42"]].to_csv(
        "out/reconcile_trials.csv", index=False, float_format="%.6f")

    cols = ["candidate", "params", "n", "win", "net_pts", "net_pct", "sharpe_calday", "sharpe_threadB_conv", "p_boot_month", "p_boot_day",
            "fdr_pass_10pct_within16", "excess_over_control_pct", "frac_seeds_beaten", "timing_control_pct", "dsr_N12", "dsr_N42"]
    ff = lambda x: f"{x:.4f}"  # noqa: E731
    lines = ["# out/reconcile_decision.md — D1 pre-registration", "",
             f"Selection window {SEL_START} → {SEL_END}, Oanda SPX500_USD, America/New_York sessions, cost {COST_PTS} pt; "
             f"calendar-day Sharpe over {len(all_dates)} NYSE trading days.",
             f"vixmove_fixed thresholds (Oanda 2005-2012 upper terciles): 15:00 VIX>{fixed[900][0]:.2f} & |move|>{fixed[900][1]:.3f}%; "
             f"15:30 VIX>{fixed[930][0]:.2f} & |move|>{fixed[930][1]:.3f}%.",
             f"Sessions with a valid prior-close reference in the window: {signals.ref_report(day.loc[SEL_START:SEL_END])}.", "",
             "## Ranking of the 12 rankable configurations (calendar-day Sharpe, net of cost)", "",
             rk[cols].to_string(index=False, float_format=ff), "",
             "p_boot_month is NA when the trades span fewer than 20 calendar months (survival rule 2); p_boot_day is the",
             "one-observation-per-day bootstrap. sharpe_threadB_conv is per-trade Sharpe × √252 (step17_intramom.py:77), which",
             "overstates the annualised figure by √(252 / trades per year); sharpe_calday is the ranking metric. The timing control",
             "enters at a random minute in the two hours before the decision on the same days and so captures the pre-decision",
             "drift as well; it is reported, not a survival test (A16). params counts FITTED numbers only.", "",
             "## Literal-threshold rows (Thread B's 17.06 / 0.665 — in-sample on 2013-2018; reported, not ranked)", "",
             res[(res["family"] == "momentum") & ~res["rankable"]][cols].to_string(index=False, float_format=ff), "",
             "## Thread A's gap-up call (pre-registered by Thread A; dsr_N12 column = PSR at N = 1, dsr_N42 column = DSR at N = 1,099)", "",
             res[res["family"] == "gapup"][cols].to_string(index=False, float_format=ff), "",
             "## PRE-REGISTERED holdout test", "",
             f"Tie set within 0.10 Sharpe of the top: {', '.join(f'{c} (params {p})' for c, p in zip(tied['candidate'], tied['params']))}.",
             f"Winner: **{winner['candidate']}** (fewest fitted parameters among the tied, then highest Sharpe).",
             "This ONE configuration is tested on the 2020-06-01 → 2026-09-11 holdout when data/ext arrives. Thread A's gap-up call "
             "(13:00, gap > 0.3%) is the second pre-registered holdout signal. The other 15 holdout rows are published in "
             "`out/reconcile_candidates.csv` (`label` column: POST-SELECTION, `window` column: 2020-06-01..2026-09-11) by "
             "`python -m pipeline.reconcile holdout` when data/ext arrives, and never promoted.", "",
             f"Written before any holdout data was read. Momentum trials this run: 16; historical N for DSR: {N_HIST} (gap-up: {N_GAP_HIST})."]
    with open("out/reconcile_decision.md", "w") as f:
        f.write("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "insample")
