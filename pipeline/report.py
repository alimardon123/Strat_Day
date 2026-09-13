"""Render PLAYBOOK_0DTE.md and OWN_ACCOUNT.md from out/ tables (D7: tables generated, never typed).

    python -m pipeline.report
"""
import glob
import os
import re
import sys

import numpy as np
import pandas as pd

from pipeline import sessions

HOLDOUT = "2020-06-01 → 2026-09-11"
EXT_MIN = "data/ext/spx_1min_2020-05_2026-09.csv.gz"
EXT_ETF = "data/ext/etf_daily_2017-11_2026-09.csv.gz"
SEL_WINDOW = "2013-01-01..2020-05-13"     # reconcile.py's `window` value for the selection-window rows
HOLD_WINDOW = "2020-06-01..2026-09-11"    # reconcile.py's `window` value for the published-not-promoted holdout rows
INT_COLS = ("rank", "days_with_two_positions", "n", "year", "full_loss_trades")   # whole-valued columns a NaN
                                                                                    # elsewhere upcasts to float64


def md(df, cols=None, fmt="{:.3f}", int_cols=()):
    d = df if cols is None else df[[c for c in cols if c in df]]
    # iterrows() upcasts an all-numeric row to float, so int-dtype columns are checked on the
    # column itself. A float column only renders as an integer when the caller names it in
    # `int_cols` (a NaN elsewhere in the column upcasts it to float64 even though every value
    # present is whole, e.g. `rank`, `days_with_two_positions`) AND every non-NaN value is
    # integral; a mean that happens to land on a whole number is never auto-detected.
    ints = {c for c in d.columns if pd.api.types.is_integer_dtype(d[c])
            or (c in int_cols and pd.api.types.is_float_dtype(d[c]) and d[c].dropna().apply(float.is_integer).all())}
    lines = ["| " + " | ".join(str(c) for c in d.columns) + " |", "|" + "---|" * len(d.columns)]
    for _, r in d.iterrows():
        cells = []
        for c, v in zip(d.columns, r):
            if c in ints:
                cells.append("" if (isinstance(v, (float, np.floating)) and np.isnan(v)) else str(int(v)))
            elif isinstance(v, (float, np.floating)):
                cells.append("" if np.isnan(v) else fmt.format(v))
            else:
                cells.append(str(v).replace("|", "\\|"))
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def winner():
    m = re.search(r"Winner: \*\*(.+?)\*\*", open("out/reconcile_decision.md").read())
    return m.group(1)


def describe(label):
    hm, direction, gate = label.split("|")
    g = {"mag": "|open → entry| above the expanding 70th percentile of prior sessions",
         "vixmove_exp": "prior-close VIX above its expanding upper tercile AND |prior close → entry| above its expanding upper tercile",
         "vixmove_fixed": "prior-close VIX and |prior close → entry| above upper-tercile boundaries frozen from Oanda 2005–2012",
         "vixmove_lit": "prior-close VIX > 17.06 AND |prior close → entry| > 0.665%"}[gate]
    d = "puts only, on down moves" if direction == "put" else "call on an up move, put on a down move"
    return f"decision at {hm} ET on the bar close; gate: {g}; direction: {d}; entry at the next bar's open; hold to the 16:00 settlement"


def playbook():
    ext = sessions.ext_present()
    w = winner()
    cand = pd.read_csv("out/reconcile_candidates.csv")
    # Section 2 is the selection-window story only; fall back to all rows for a CSV written before
    # reconcile.py grew a `window` column (D1 holdout-publication amendment).
    cand_sel = cand[cand["window"] == SEL_WINDOW] if "window" in cand else cand
    summ = pd.read_csv("out/insample_summary.csv")
    sz = pd.read_csv("out/insample_sizing.csv")
    ex = pd.read_csv("out/insample_execution.csv")
    trials = pd.read_csv("out/trials.csv")
    dec = open("out/reconcile_decision.md").read()
    thr = re.search(r"15:00 VIX>([\d.]+) & \|move\|>([\d.]+)%; 15:30 VIX>([\d.]+) & \|move\|>([\d.]+)%", dec)
    hold_files = [f for f in ("out/holdout_summary.csv",) if os.path.exists(f)]
    n_pass = int(trials["fdr_pass_10pct_family"].sum())
    if n_pass:
        fdr_sentence = (f"{n_pass} of {len(trials)} trials pass BH-FDR at 10% across the family (`out/trials.csv`): "
                         + ", ".join(f"`{t}`" for t in trials.loc[trials["fdr_pass_10pct_family"], "trial"]) + ".")
    else:
        fdr_sentence = f"0 of {len(trials)} trials pass BH-FDR at 10% across the family (`out/trials.csv`)."
    if os.path.exists("out/options_timevalue.csv"):
        tv = pd.read_csv("out/options_timevalue.csv")
        tv60 = tv[(tv["mins_to_close"] == 60) & (tv["k"] == 1.0)]
        tv_le40 = tv60.loc[tv60["vix"] <= 40, "time_value"].max()
        tv_max_row = tv60.loc[tv60["time_value"].idxmax()]
        tv_clause = (f"time value ≤ {tv_le40:.3f} index points at 60 minutes for VIX ≤ 40 and "
                     f"≤ {tv_max_row['time_value']:.3f} at VIX {int(tv_max_row['vix'])}, `out/options_timevalue.csv`")
    else:
        print("WARNING: out/options_timevalue.csv missing; playbook() falling back to the hand-typed time-value wording "
              "(run `python -m pipeline.options` to generate it)", file=sys.stderr)
        tv_clause = "time value < 0.02 index points for VIX ≤ 40"
    L = []
    L += ["# PLAYBOOK_0DTE.md — the constrained book, every number measured", "",
          "**Account constraint.** 0DTE options only, long-only, naked calls or puts; no selling, spreads, futures, shares or "
          "overnight holds; daily loss limit 3–5% (base case 4%) on marked intraday P&L.", "",
          "**Pricing model, stated first.** No real 0DTE quotes were obtainable. Every option number below is Black-Scholes with "
          "r = 0 and IV = k × prior-close VIX (both prior threads used k = 1.0 and called it generous). At 2% in the money with "
          f"less than an hour to expiry that model is intrinsic value ± the spread ({tv_clause}), "
          "so k only matters for the 13:00 leg and the spread is the real sensitivity axis. SPX/XSP are PM cash-settled: buy at "
          "the ask (half the quoted spread), settle at intrinsic. SPY is physically settled and must be sold by 15:55 with both "
          "spread halves paid; SPY rows are for that exit.", ""]
    if not ext:
        L += [f"**Holdout status: PENDING.** The post-May-2020 minute file (`{EXT_MIN}`) has not been supplied, so the holdout "
              f"({HOLDOUT}) has not run. Every table below is measured on the 2013-01-01 → 2020-05-13 SELECTION WINDOW and is "
              "labelled IN-SAMPLE. It is not the headline and must not be traded on. The headline block will be generated from "
              "`out/holdout_*.csv` when the file arrives.", ""]
    L += ["## 1. The pre-registered specification", "",
          f"**Reconciled last-hour momentum signal (D1 winner):** `{w}` — {describe(w)}."]
    if thr:
        L += [f"Frozen gate values: 15:00 → VIX > {thr.group(1)} and |move| > {thr.group(2)}%; 15:30 → VIX > {thr.group(3)} and |move| > {thr.group(4)}%.", ""]
    L += ["**Thread A's gap-up call (pre-registered by Thread A):** open / prior close − 1 > 0.3% → 2% ITM call at the first bar "
          "after 13:00 ET, hold to settlement.", "",
          "Strike: 2% in the money, rounded away from spot to the grid (5 points SPX, $1 SPY/XSP). Never at-the-money or "
          "out-of-the-money (−53% per trade at a 17% hit rate in both threads).", "",
          "## 2. How the specification was chosen (selection window 2013-01 → 2020-05-13, Oanda SPX, net of 1.0 pt)", "",
          md(cand_sel[cand_sel["rankable"]].sort_values("rank")[["rank", "candidate", "params", "n", "win", "net_pts", "net_pct", "sharpe_calday",
                                                          "p_boot_month", "p_boot_day", "excess_over_control_pct", "timing_control_pct", "dsr_N12", "dsr_N42"]],
             int_cols=INT_COLS), "",
          "Literal Thread B thresholds (17.06 / 0.665, in-sample on 2013–2018, reported not ranked):", ""]
    if "window" in cand:
        # `family` splits the 5 non-rankable rows cleanly once `window` tells us this is the new-style
        # CSV; a CSV from before D1's holdout-publication amendment has no `family`-safe way to do this
        # split, so it keeps the old merged (literal + gap-up) rendering below.
        L += [md(cand_sel[(~cand_sel["rankable"]) & (cand_sel["family"] == "momentum")][["candidate", "n", "win", "net_pts", "net_pct",
                                                                                          "sharpe_calday", "p_boot_month", "p_boot_day"]],
                 int_cols=INT_COLS), "",
              "Thread A's gap-up call, same selection window (pre-registered by Thread A, not part of this ranking — see §1):", "",
              md(cand_sel[cand_sel["family"] == "gapup"][["candidate", "n", "win", "net_pts", "net_pct", "sharpe_calday",
                                                           "p_boot_month", "p_boot_day"]],
                 int_cols=INT_COLS), ""]
    else:
        L += [md(cand_sel[~cand_sel["rankable"]][["candidate", "n", "win", "net_pts", "net_pct", "sharpe_calday", "p_boot_month", "p_boot_day"]],
                 int_cols=INT_COLS), ""]
    L += ["Every VIX-gated two-sided configuration outranks every magnitude-gated or put-only one; the four VIX-gated two-sided "
          "variants tie within 0.10 Sharpe and the tie-break (fewest FITTED parameters — an expanding rule has none) picks the "
          f"15:00 entry with the expanding-tercile rule. {fdr_sentence}", ""]
    L += ["## 3. Option-level results — IN-SAMPLE (% of premium per trade)", "",
          md(summ[["signal", "spread", "settle", "k", "n", "trades_per_year", "win", "mean", "median", "worst_trade", "worst_day",
                   "mae_worst", "full_loss_trades", "premium_mean"]], int_cols=INT_COLS), "",
          "mae_worst is the worst intraday excursion of the underlying against the position during the hold, in % of premium, "
          "capped at −100% (what a prop desk marks; ACCEPTANCE budgets).", "",
          "## 4. Sizing — IN-SAMPLE, % of account", "",
          "Position size = daily limit ÷ worst-trade loss with a 100% floor (a hold-to-close option has no stop). The combined "
          "book sizes on the worst day when both signals fire.", "",
          md(sz[["signal", "limit", "size_pct", "worst_trade_loss_pct", "exp_annual_pct", "worst_year_pct", "best_year_pct",
                 "days_with_two_positions", "worst_day_both_positions_pct"]], int_cols=INT_COLS), "",
          "## 5. Execution — IN-SAMPLE (underlying index points per signal; unfilled limits count as zero)", "",
          md(ex[["candidate", "entry", "fill_rate", "n_signals", "mean_net_per_signal", "mean_net_if_filled", "improvement",
                 "improvement_cost_part", "improvement_price_part", "p_improvement"]]), "",
          "The improvement over market entry splits into the part that is a cost assumption (fill rate × the 0.40 pt saved by "
          "paying commission instead of crossing the entry half of the spread) and the part that is price improvement net of "
          "adverse selection (unfilled signals count as zero).", "",
          "## 6. Contract size and minimum account", "",
          "A 2% ITM SPX option costs ≈ 2% × S × 100 ≈ $13,000 at S = 6,500; XSP is one tenth. At the base size (4% of account "
          "per trade) one SPX contract needs ≈ $325k of account, one XSP contract ≈ $32.5k, one SPY contract ≈ $32.5k with the "
          "15:55 exit. Max positions per day: 2 (the two signals can coincide).", "",
          "## 7. Holdout — what decides whether this is tradeable", ""]
    if hold_files:
        h = pd.read_csv(hold_files[0])
        L += ["Survival-rule verdict per pre-registered signal (`out/holdout_summary.csv`; `label_final` includes the family-wide FDR):", "",
              md(h[[c for c in ["signal", "n", "win", "net_pts", "net_pct", "worst_trade_pts", "p_month", "p_day", "p_half1_month", "p_half2_month",
                                "excess_over_control_pct", "psr", "sharpe_calday", "fdr_pass_10pct_family", "label_final"] if c in h]],
                 int_cols=INT_COLS), ""]
        hold_pub = cand[cand["window"] == HOLD_WINDOW] if "window" in cand else cand.iloc[0:0]
        if len(hold_pub):
            pub_cols = [c for c in ["candidate", "label", "params", "n", "win", "net_pts", "net_pct", "sharpe_calday",
                                    "p_boot_month", "p_boot_day", "excess_over_control_pct", "timing_control_pct"] if c in hold_pub]
            pub = pd.concat([hold_pub[hold_pub["label"] == "PRE-REGISTERED"],
                             hold_pub[hold_pub["label"] != "PRE-REGISTERED"].sort_values("sharpe_calday", ascending=False)])
            L += ["All 16 configurations on the holdout — published, not promoted (`out/reconcile_candidates.csv`, `label` column):", "",
                  md(pub[pub_cols], int_cols=INT_COLS), "",
                  "These 15 POST-SELECTION rows are published for transparency only; they do not enter the survival verdict above "
                  "or pipeline/trials.py's trial family (never promoted).", ""]
        if os.path.exists("out/holdout_by_year.csv"):
            L += ["By calendar year (`out/holdout_by_year.csv`):", "", md(pd.read_csv("out/holdout_by_year.csv"), int_cols=INT_COLS), "",
                  "opt_mean_s1/s2/s3 = option return in % of premium at quoted spread 1/2/3 (cash settlement); worst_day_pts = the "
                  "worst calendar day's net index points; mae_worst_pct = the worst intraday adverse excursion in % of premium at "
                  "spread 1.", ""]
        if os.path.exists("out/holdout_d4_summary.csv"):
            hs = pd.read_csv("out/holdout_d4_summary.csv")
            L += ["Option-level results on the HOLDOUT (% of premium; `out/holdout_d4_summary.csv`) — THE HEADLINE:", "",
                  md(hs[["signal", "spread", "settle", "k", "n", "trades_per_year", "win", "mean", "median", "worst_trade", "worst_day",
                         "mae_worst", "full_loss_trades", "premium_mean"]], int_cols=INT_COLS), ""]
        if os.path.exists("out/holdout_d4_sizing.csv"):
            L += ["Sizing on the HOLDOUT (% of account; `out/holdout_d4_sizing.csv`):", "",
                  md(pd.read_csv("out/holdout_d4_sizing.csv"), int_cols=INT_COLS), ""]
        if os.path.exists("out/holdout_d4_execution.csv"):
            L += ["Execution on the HOLDOUT (`out/holdout_d4_execution.csv`):", "", md(pd.read_csv("out/holdout_d4_execution.csv")), ""]
    else:
        L += [f"PENDING `{EXT_MIN}`. When it arrives, `make all` runs the holdout step (`python -m pipeline.insample 2020-06-01 "
              "2026-09-11 HOLDOUT`), the family-wide FDR in `pipeline/trials.py` finalises the labels, and this section is generated "
              "from `out/holdout_*.csv`. If the pre-registered signal fails, that is the result; no re-tuning.", ""]
    if os.path.exists("out/fullsample_summary.csv"):
        fs = pd.read_csv("out/fullsample_summary.csv")
        fsz = pd.read_csv("out/fullsample_sizing.csv")
        fex = pd.read_csv("out/fullsample_execution.csv")
        L += ["IN-SAMPLE + HOLDOUT (2013-01..2026-09-11) — full-sample figures, NOT the headline:", "",
              "Option-level results (% of premium; `out/fullsample_summary.csv`):", "",
              md(fs[[c for c in ["signal", "spread", "settle", "k", "n", "trades_per_year", "win", "mean", "median", "worst_trade",
                                  "worst_day", "mae_worst", "full_loss_trades", "premium_mean"] if c in fs]], int_cols=INT_COLS), "",
              "Sizing (% of account; `out/fullsample_sizing.csv`):", "",
              md(fsz[[c for c in ["signal", "limit", "size_pct", "worst_trade_loss_pct", "exp_annual_pct", "worst_year_pct",
                                   "best_year_pct", "days_with_two_positions", "worst_day_both_positions_pct"] if c in fsz]],
                 int_cols=INT_COLS), "",
              "Execution (`out/fullsample_execution.csv`):", "",
              md(fex[[c for c in ["candidate", "entry", "fill_rate", "n_signals", "mean_net_per_signal", "mean_net_if_filled",
                                   "improvement", "improvement_cost_part", "improvement_price_part", "p_improvement"] if c in fex]]), ""]
    L += ["## 8. Before any live capital (both threads' rule)", "",
          "Measure ten real 2%-ITM 0DTE fills at the mid; above 1.5 index points round-trip nothing here works. Paper-trade "
          "≥ 60 qualifying days. Real 0DTE IV runs above 30-day VIX; the 13:00 leg is the only one where that matters.", ""]
    open("PLAYBOOK_0DTE.md", "w").write("\n".join(L))


def own_account():
    ext = os.path.exists(EXT_ETF)
    s = pd.read_csv("out/own_account_summary.csv")
    yr = pd.read_csv("out/own_account_by_year.csv")
    reg = pd.read_csv("out/own_account_by_regime.csv")
    L = ["# OWN_ACCOUNT.md — the unconstrained 8-sleeve portfolio, re-measured", "",
         "Secondary track for a stock account with options approval. Sleeve code is Thread A's, imported unchanged where a "
         "script exists (it7/it8/it9/it11); TSMOM/XSMOM inverse-vol from it8b; S13 re-implemented from ASSESSMENT_iteration17 "
         "with a 0.5 weight cap. Each sleeve vol-targeted to 10% (60-day trailing, lagged), equal weight; two buckets 50/50.", ""]
    if not ext:
        L += [f"**ETF panel status: PENDING** `{EXT_ETF}`. S2, S3, S6 (25-ETF universe) and S13 (VXX/VXZ via the VIXY/VIXM bridge) "
              "stop at 2017-11-10; S1, S5, S8 run to 2026-03-20 on the fetched SPY and stock panels; S12 to 2020-05-13.", ""]
    for wname in s["window"].unique():
        L += [f"## {wname}", "", md(s[s["window"] == wname][["label", "cagr", "vol", "sharpe", "maxdd", "n_days", "start", "end"]]), ""]
    L += ["## By year (sum of daily returns at 10% sleeve vol)", "", md(yr, int_cols=INT_COLS), "",
          "## By regime (annualised mean; uptrend = SPY above a rising 200-day average, high-vol = prior VIX above its expanding upper tercile)", "",
          md(reg), ""]
    if os.path.exists("out/own_account_bridge.csv"):
        b = pd.read_csv("out/own_account_bridge.csv")
        L += ["## VXX / VXZ bridge (A13): daily-return correlations on the overlaps", "",
              "Old VXX ↔ VIXY and old VXZ ↔ VIXM are measurable now; new-VXX ↔ VIXY and new-VXZ ↔ VIXM need the ext panel. The bridge is "
              "refused below 0.98.", "", md(b, fmt="{:.4f}"), ""]
    if os.path.exists("out/vrp_vix_minus_rv.csv"):
        v = pd.read_csv("out/vrp_vix_minus_rv.csv")
        L += ["## VIX − realised vol (variance risk premium), measured not traded", "",
              "Prior-close VIX minus the next 21 trading days' realised vol of SPY, in vol points. Not tradeable as measured: no "
              "option prices, spreads or margin; a defined-risk 30–45 DTE implementation is a recorded non-goal.", "", md(v), ""]
    L += ["## Known differences from Thread A's published baseline", "",
          "Thread A: 8 sleeves Sharpe 1.12 full / 1.35 test, maxDD −6.10%; two buckets 1.20 / 1.40, −5.26%. Here the BAB sleeve "
          "runs on the raw 928-stock big_movers panel with a |return| < 0.5 mask because Thread A's cleaned 626-stock panel is not "
          "in the bundle, and S12 is the pipeline's gap-up signal rather than Thread A's scan cell; test-window Sharpes of S2, S3 "
          "and S13 match Thread A's published values.", ""]
    open("OWN_ACCOUNT.md", "w").write("\n".join(L))


if __name__ == "__main__":
    playbook()
    own_account()
    print("wrote PLAYBOOK_0DTE.md, OWN_ACCOUNT.md")
