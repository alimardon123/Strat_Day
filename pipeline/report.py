"""Render PLAYBOOK_0DTE.md and OWN_ACCOUNT.md from out/ tables (D7: tables generated, never typed).

    python -m pipeline.report
"""
import glob
import os
import re

import numpy as np
import pandas as pd

HOLDOUT = "2020-06-01 → 2026-09-11"
EXT_MIN = "data/ext/spx_1min_2020-05_2026-09.csv.gz"
EXT_ETF = "data/ext/etf_daily_2017-11_2026-09.csv.gz"


def md(df, cols=None, fmt="{:.3f}"):
    d = df if cols is None else df[[c for c in cols if c in df]]
    lines = ["| " + " | ".join(str(c) for c in d.columns) + " |", "|" + "---|" * len(d.columns)]
    for _, r in d.iterrows():
        cells = []
        for v in r:
            if isinstance(v, (float, np.floating)):
                cells.append("" if np.isnan(v) else fmt.format(v))
            else:
                cells.append(str(v))
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
    ext = os.path.exists(EXT_MIN)
    w = winner()
    cand = pd.read_csv("out/reconcile_candidates.csv")
    summ = pd.read_csv("out/insample_summary.csv")
    sz = pd.read_csv("out/insample_sizing.csv")
    ex = pd.read_csv("out/insample_execution.csv")
    dec = open("out/reconcile_decision.md").read()
    thr = re.search(r"15:00 VIX>([\d.]+) & \|move\|>([\d.]+)%; 15:30 VIX>([\d.]+) & \|move\|>([\d.]+)%", dec)
    hold_files = sorted(glob.glob("out/holdout_summary.csv"))
    L = []
    L += ["# PLAYBOOK_0DTE.md — the constrained book, every number measured", "",
          "**Account constraint.** 0DTE options only, long-only, naked calls or puts; no selling, spreads, futures, shares or "
          "overnight holds; daily loss limit 3–5% (base case 4%) on marked intraday P&L.", "",
          "**Pricing model, stated first.** No real 0DTE quotes were obtainable. Every option number below is Black-Scholes with "
          "r = 0 and IV = k × prior-close VIX (both prior threads used k = 1.0 and called it generous). At 2% in the money with "
          "less than an hour to expiry that model is intrinsic value ± the spread (time value < 0.02 index points for VIX ≤ 40), "
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
          md(cand[cand["rankable"]].sort_values("rank")[["rank", "candidate", "n", "win", "net_pts", "net_pct", "sharpe_calday",
                                                          "p_boot_month", "p_boot_day", "excess_over_control_pct", "dsr_N12", "dsr_N42"]]), "",
          "Literal Thread B thresholds (17.06 / 0.665, in-sample on 2013–2018, reported not ranked):", "",
          md(cand[~cand["rankable"]][["candidate", "n", "win", "net_pts", "net_pct", "sharpe_calday", "p_boot_month", "p_boot_day"]]), "",
          "Every VIX-gated two-sided configuration outranks every magnitude-gated or put-only one; the four VIX-gated two-sided "
          "variants tie within 0.10 Sharpe and the parameter-count tie-break picks the 15:00 entry with frozen thresholds. No "
          "configuration passes BH-FDR at 10% on the selection window.", ""]
    L += ["## 3. Option-level results — IN-SAMPLE (% of premium per trade)", "",
          md(summ[["signal", "spread", "settle", "k", "n", "trades_per_year", "win", "mean", "median", "worst_trade", "worst_day",
                   "full_loss_trades", "premium_mean"]]), "",
          "## 4. Sizing — IN-SAMPLE, % of account", "",
          "Position size = daily limit ÷ worst-trade loss with a 100% floor (a hold-to-close option has no stop). The combined "
          "book sizes on the worst day when both signals fire.", "",
          md(sz[["signal", "limit", "size_pct", "worst_trade_loss_pct", "exp_annual_pct", "worst_year_pct", "best_year_pct",
                 "days_with_two_positions", "worst_day_both_positions_pct"]]), "",
          "## 5. Execution — IN-SAMPLE (underlying index points per signal; unfilled limits count as zero)", "",
          md(ex[["candidate", "entry", "fill_rate", "n_signals", "mean_net_per_signal", "mean_net_if_filled", "improvement", "p_improvement"]]), "",
          "## 6. Contract size and minimum account", "",
          "A 2% ITM SPX option costs ≈ 2% × S × 100 ≈ $13,000 at S = 6,500; XSP is one tenth. At the base size (4% of account "
          "per trade) one SPX contract needs ≈ $325k of account, one XSP contract ≈ $32.5k, one SPY contract ≈ $32.5k with the "
          "15:55 exit. Max positions per day: 2 (the two signals can coincide).", "",
          "## 7. Holdout — what decides whether this is tradeable", ""]
    if hold_files:
        h = pd.read_csv(hold_files[0])
        L += [md(h), ""]
    else:
        L += [f"PENDING `{EXT_MIN}`. When it arrives: `python -m pipeline.insample 2020-06-01 2026-09-11 HOLDOUT out/holdout` "
              "and the survival rule in ACCEPTANCE.md decides. If the pre-registered signal fails, that is the result; no re-tuning.", ""]
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
    L += ["## By year (sum of daily returns at 10% sleeve vol)", "", md(yr), "",
          "## By regime (annualised mean; uptrend = SPY above a rising 200-day average, high-vol = prior VIX above its expanding upper tercile)", "",
          md(reg), ""]
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
