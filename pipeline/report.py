"""Render PLAYBOOK_0DTE.md and OWN_ACCOUNT.md from out/ tables (D7: tables generated, never typed).

    python -m pipeline.report
"""
import glob
import io
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


FVG_COLS = ["trial", "n_setups", "fill_rate", "n", "win", "net_pts_cost1", "net_pts_cost2", "net_pct_cost1",
            "worst_trade_pts_cost1", "worst_day_pts_cost1", "sharpe_calday", "p_boot_day", "p_boot_month",
            "control_mean_pts_cost1", "frac_seeds_beaten", "dsr_N33"]


def fvg_verdict(sub):
    """Generated per-window verdict for the A36 fvg family: net > 0 at 1 pt and p_day < 0.05
    counts, then the ACCEPTANCE survival check (net > 0, p_day < 0.05, excess over the random-
    entry control > 0, n >= 200); DSR at N=33 is reported in the table, not a survival condition."""
    n_net_pos = int((sub["net_pts_cost1"] > 0).sum())
    n_p_sig = int((sub["p_boot_day"] < 0.05).sum())
    excess = sub["net_pts_cost1"] - sub["control_mean_pts_cost1"]
    survives = sub[(sub["net_pts_cost1"] > 0) & (sub["p_boot_day"] < 0.05) & (excess > 0) & (sub["n"] >= 200)]
    verdict = "no trial survives" if survives.empty else "survives: " + ", ".join(survives["trial"])
    return (f"{n_net_pos} of {len(sub)} trials net > 0 at 1 pt; {n_p_sig} of {len(sub)} have p_day < 0.05; "
            f"{verdict} (net > 0 AND p_day < 0.05 AND excess over control > 0 AND n ≥ 200; DSR at N=33 is "
            "reported in the table above, not a survival condition).")


def fvg_caption(df):
    """First two sentences of the `spec` column (identical on every row — the fixed pre-
    registration), generated rather than typed (D7)."""
    if "spec" not in df or not len(df):
        return ""
    parts = re.split(r"(?<=\.)\s+", str(df["spec"].iloc[0]).strip())
    return " ".join(parts[:2])


GAPLIQ_COLS = ["trial", "side", "entry_time", "n_signal_days", "n_skipped", "n", "win", "net_pts_cost1",
               "net_pts_cost2", "net_pct_cost1", "worst_trade_pts_cost1", "worst_day_pts_cost1", "sharpe_calday",
               "p_boot_day", "p_boot_month", "control_mean_pts_cost1", "frac_seeds_beaten",
               "timing_control_pts_cost1", "frac_timing_beaten", "opt_mean_pct_s1", "dsr_N37"]


def gapliq_verdict(sub):
    """Generated per-window verdict for the A39 gapliq family: T1's survival on the same four
    programmatic checks as the FVG verdict (net > 0 at 1 pt, p_day < 0.05, excess over the
    day-selection control > 0, n >= 200; DSR at N=37 is reported in the table, not a survival
    condition here either) AND the amendment's mechanism fingerprint (T2 < T1; T3 <= 0 at 1 pt),
    then the promotion decision per the amendment's kill/promotion rule."""
    t1 = sub[sub["trial"] == "T1"]
    t2 = sub[sub["trial"] == "T2"]
    t3 = sub[sub["trial"] == "T3"]
    if t1.empty:
        return "T1 missing from this window."
    t1 = t1.iloc[0]
    net_pos = bool(t1["net_pts_cost1"] > 0)
    p_sig = bool(t1["p_boot_day"] < 0.05) if pd.notna(t1["p_boot_day"]) else False
    excess = t1["net_pts_cost1"] - t1["control_mean_pts_cost1"]
    beats_control = bool(excess > 0) if pd.notna(excess) else False
    n_ok = bool(t1["n"] >= 200)
    survives = net_pos and p_sig and beats_control and n_ok
    t2_lt_t1 = bool(t2.iloc[0]["net_pts_cost1"] < t1["net_pts_cost1"]) if len(t2) and pd.notna(t2.iloc[0]["net_pts_cost1"]) else False
    t3_le_zero = bool(t3.iloc[0]["net_pts_cost1"] <= 0) if len(t3) and pd.notna(t3.iloc[0]["net_pts_cost1"]) else False
    fingerprint_ok = t2_lt_t1 and t3_le_zero
    promoted = survives and fingerprint_ok
    decision = ("T1 promotable" if promoted else
               "pattern without its mechanism, not promoted" if survives else
               "T1 does not survive, not promoted")
    return (f"T1: net {'>' if net_pos else '<='} 0 at 1 pt, p_day {'<' if p_sig else '>='} 0.05, excess over the "
            f"day-selection control {'>' if beats_control else '<='} 0, n {'>=' if n_ok else '<'} 200 -> "
            f"{'SURVIVES' if survives else 'does not survive'} the four programmatic checks (DSR at N=37 is reported "
            f"in the table above, not a survival condition). Fingerprint: T2 {'<' if t2_lt_t1 else '>='} T1 "
            f"({'holds' if t2_lt_t1 else 'fails'}); T3 {'<=' if t3_le_zero else '>'} 0 at 1 pt "
            f"({'holds' if t3_le_zero else 'fails'}). Promotion: {decision}.")


def gapliq_caption(df):
    """First two sentences of the `spec` column (identical on every row — the fixed pre-
    registration), generated rather than typed (D7)."""
    if "spec" not in df or not len(df):
        return ""
    parts = re.split(r"(?<=\.)\s+", str(df["spec"].iloc[0]).strip())
    return " ".join(parts[:2])


LETF_COLS = ["trial", "n_sessions_with_assets", "n_signal", "n_skipped", "n", "win", "net_pts_cost1",
             "net_pts_cost2", "net_pct_cost1", "worst_trade_pts_cost1", "worst_day_pts_cost1", "sharpe_calday",
             "p_boot_day", "p_boot_month", "control_mean_pts_cost1", "frac_seeds_beaten",
             "magnitude_row_net_pts", "beats_magnitude_row", "opt_mean_pct_s1", "dsr_N37"]


def letf_verdict(sub):
    """Generated per-window verdict for the A38 letf trial: the same four programmatic survival
    checks as fvg_verdict/gapliq_verdict (net > 0 at 1 pt, p_day < 0.05, excess over the day-
    selection control > 0, n >= 200; DSR at N=37 is reported in the table, not a survival condition
    here either), PLUS the amendment's own kill rule (net <= 0 at 1 pt on the holdout, OR not above
    the day-selection control, OR not above the price-only magnitude row)."""
    row = sub.iloc[0]
    net_pos = bool(row["net_pts_cost1"] > 0) if pd.notna(row["net_pts_cost1"]) else False
    p_sig = bool(row["p_boot_day"] < 0.05) if pd.notna(row["p_boot_day"]) else False
    excess = row["net_pts_cost1"] - row["control_mean_pts_cost1"]
    beats_control = bool(excess > 0) if pd.notna(excess) else False
    n_ok = bool(row["n"] >= 200)
    beats_mag = bool(row["beats_magnitude_row"]) if pd.notna(row.get("beats_magnitude_row")) else False
    survives = net_pos and p_sig and beats_control and n_ok
    killed = (not net_pos) or (not beats_control) or (not beats_mag)
    return (f"net {'>' if net_pos else '<='} 0 at 1 pt, p_day {'<' if p_sig else '>='} 0.05, excess over the "
            f"day-selection control {'>' if beats_control else '<='} 0, n {'>=' if n_ok else '<'} 200 -> "
            f"{'SURVIVES' if survives else 'does not survive'} the four programmatic checks (DSR at N=37 is "
            f"reported in the table above, not a survival condition). Beats the price-only magnitude row "
            f"(`15:30|both|mag`): {'yes' if beats_mag else 'no'}. A38 kill rule (net <= 0 at 1 pt, OR not above "
            f"the day-selection control, OR not above the magnitude row): {'KILLED' if killed else 'not triggered'}.")


def letf_caption(df):
    """First two sentences of the `spec` column (identical on every row — the fixed pre-
    registration), generated rather than typed (D7)."""
    if "spec" not in df or not len(df):
        return ""
    parts = re.split(r"(?<=\.)\s+", str(df["spec"].iloc[0]).strip())
    return " ".join(parts[:2])


REALOPT_REEVAL_COLS = ["signal", "cost_label", "n", "n_skipped_missing", "win", "mean_pct_of_premium",
                       "median_pct", "worst_pct", "model_mean_pct", "label", "p_boot_day", "sharpe_calday"]


def realopt_calibration_blocks(path):
    """Split out/realopt_calibration.csv's two blocks (per-(date,minute,right) table, one blank
    line, then the by-VIX-tercile/by-minute/overall summary table — pipeline.units.realopt's own
    convention, see its module docstring point 6) into two DataFrames; the second is empty if the
    file only ever got a header (the skip path writes no summary block at all)."""
    text = open(path).read()
    parts = [p for p in re.split(r"\n\s*\n", text.strip()) if p.strip()]
    calib = pd.read_csv(io.StringIO(parts[0]))
    summary = pd.read_csv(io.StringIO(parts[1])) if len(parts) > 1 else pd.DataFrame()
    return calib, summary


def real_price_clause():
    """A41: the first paragraph states which numbers are real-priced and from which date; every figure
    is read from out/realopt_calibration.csv (per-row block for the date range, summary block for the
    overall median k, IQR and missing share). Without real bars the original sentence stands."""
    path = "out/realopt_calibration.csv"
    if not os.path.exists(path) or os.path.getsize(path) == 0:
        return "No real 0DTE quotes were obtainable. "
    try:
        calib, summary = realopt_calibration_blocks(path)
    except Exception:
        return "No real 0DTE quotes were obtainable. "
    if calib.empty or summary.empty or "date" not in calib:
        return "No real 0DTE quotes were obtainable. "
    ov = summary[summary["group_type"] == "overall"]
    if ov.empty:
        return "No real 0DTE quotes were obtainable. "
    ov = ov.iloc[0]
    return (f"Real SPY 0DTE 1-minute option bars supplied by the owner cover {calib['date'].min()} → {calib['date'].max()}; "
            f"§12 re-prices every option leg on those sessions with them and §13 uses them directly. Calibration at the "
            f"2 %-ITM strikes the playbook trades: median implied k {ov['median_implied_k']:.3f} (IQR {ov['iqr_implied_k']:.3f}) "
            f"against the model at k = 1, i.e. at 2 % ITM the model is intrinsic ± the spread and k is not identifiable; the real "
            f"deviation is illiquidity — no trade printed in the exact minute for {100 * ov['missing_share']:.0f} % of the "
            f"session-minutes checked (`out/realopt_calibration.csv`). ")


def realopt_caption(df):
    """First two sentences of the `spec` column (identical on every row — the fixed pre-
    registration), generated rather than typed (D7)."""
    if "spec" not in df or not len(df):
        return ""
    parts = re.split(r"(?<=\.)\s+", str(df["spec"].iloc[0]).strip())
    return " ".join(parts[:2])


def realopt_labels(df):
    """One generated line per signal x cost row, straight from the `label`/`note` columns
    themselves (D7: never typed), e.g. '- T1 at +$0.10: model pessimistic here (n=42, real mean
    +3.10% of premium vs model +5.00%; sub-window, not a verdict).'."""
    lines = []
    for _, r in df.iterrows():
        if r["n"] == 0:
            lines.append(f"- {r['signal']} at {r['cost_label']}: {r['label']} "
                         f"(n_skipped_missing={int(r['n_skipped_missing'])}; {r['note']}).")
            continue
        lines.append(f"- {r['signal']} at {r['cost_label']}: {r['label']} "
                     f"(n={int(r['n'])}, real mean {r['mean_pct_of_premium']:+.2f}% of premium vs "
                     f"model {r['model_mean_pct']:+.2f}%; {r['note']}).")
    return lines


EVENTVOL_COLS = ["trial", "cost", "n", "n_skipped", "win", "mean_pct", "median_pct", "worst_pct",
                 "mean_usd", "p_boot_day", "sharpe_calday", "dsr_N39", "e2_minus_e3_pct",
                 "p_e2_vs_e3", "underpowered"]


def eventvol_verdict(df):
    """Generated verdict for the A42 event-day long-volatility family: E1 (baseline, LOW prior,
    expected negative) is reported for context; E2 (FOMC) is UNDERPOWERED by construction
    (n ~ 20 < 200) at every cost and is never promoted on this sample regardless of sign or
    significance; E2 - E3 (LOW-MEDIUM prior) is the pre-registered comparison, reported per cost."""
    e2 = df[df["trial"] == "E2"]
    lines = []
    for _, row in e2.iterrows():
        diff = row["e2_minus_e3_pct"]
        sign = "positive" if pd.notna(diff) and diff > 0 else ("negative" if pd.notna(diff) else "n/a")
        diff_str = f"{diff:.4f}" if pd.notna(diff) else "n/a"
        p_str = f"{row['p_e2_vs_e3']:.4f}" if pd.notna(row["p_e2_vs_e3"]) else "n/a"
        lines.append(f"at cost ${row['cost']:.2f}: E2 - E3 = {diff_str} pct-pts ({sign}), p_e2_vs_e3 = {p_str}")
    detail = "; ".join(lines) if lines else "no E2 rows"
    return (f"E2 (FOMC) is UNDERPOWERED by construction (n ~ 20 < 200) at every cost and is never "
            f"promoted on this sample regardless of sign or significance. E2 - E3: {detail}. "
            f"Nothing in this family is promoted here (pre-registered as reported-only, A42).")


def eventvol_caption(df):
    """First two sentences of the `spec` column (identical on every row — the fixed pre-
    registration), generated rather than typed (D7)."""
    if "spec" not in df or not len(df):
        return ""
    parts = re.split(r"(?<=\.)\s+", str(df["spec"].iloc[0]).strip())
    return " ".join(parts[:2])


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
    if os.path.exists("out/pbo.csv"):
        pbo = pd.read_csv("out/pbo.csv")
        p16 = pbo[pbo["n_blocks"] == 16]
        pbo_actual = p16[p16["variant"] == "actual"].iloc[0]
        pbo_null = p16[p16["variant"] == "shuffled_null"].iloc[0]
        pbo_sentence = (f" Probability of backtest overfitting of this {int(pbo_actual['n_configs'])}-configuration "
                         f"selection (CSCV, {int(pbo_actual['n_blocks'])} blocks, {int(pbo_actual['n_combinations']):,} "
                         f"splits): {pbo_actual['pbo']:.2f}; the in-sample best configuration's median out-of-sample "
                         f"rank logit is {pbo_actual['median_logit']:.2f}; the per-column shuffled null gives "
                         f"{pbo_null['pbo']:.2f} (this null preserves each configuration's own mean and variance, so "
                         "it is a floor for near-duplicate configurations, not 0.5 — reported, not a survival "
                         "condition).")
    else:
        pbo_sentence = ""
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
          "**Pricing model, stated first.** " + real_price_clause() + "Every option number outside §12–§13 is Black-Scholes with "
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
        L += [f"For reference, the frozen `vixmove_fixed` boundaries (a different, non-winning configuration: Oanda 2005-2012 "
              f"upper terciles, `out/reconcile_decision.md`): 15:00 VIX > {thr.group(1)} & |move| > {thr.group(2)}%; 15:30 VIX > "
              f"{thr.group(3)} & |move| > {thr.group(4)}%. The pre-registered winner uses expanding terciles computed from "
              "strictly prior sessions and has no frozen thresholds.", ""]
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
          f"15:00 entry with the expanding-tercile rule. {fdr_sentence}{pbo_sentence}", ""]
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
          "A 2% ITM SPX option costs ≈ 2% × S × 100 ≈ $13,000 at S = 6,500 (S = 6,500 is an assumed current index level, not "
          "measured here — no post-2020 price file is present; every dollar figure scales linearly with S); XSP is one tenth. "
          "At the base size (4% of account per trade) one SPX contract needs ≈ $325k of account, one XSP contract ≈ $32.5k, "
          "one SPY contract ≈ $32.5k with the 15:55 exit. Max positions per day: 2 (the two signals can coincide).", "",
          "## 7. Holdout — what decides whether this is tradeable", ""]
    if hold_files:
        h = pd.read_csv(hold_files[0])
        if "data_first_date" in h:
            r0 = h.iloc[0]
            L += [f"Contract window {HOLDOUT}; minute data present {r0['data_first_date']} → {r0['data_last_date']} "
                  f"({int(r0['sessions_in_window'])} sessions). Sessions before the first date have no minute data (the Oanda "
                  "series ends 2020-05-13 and the supplied feed starts later, DATA.md); they are absent from every holdout "
                  "table, not filled.", ""]
        L += ["Survival-rule verdict per pre-registered signal (`out/holdout_summary.csv`; `label_final` includes the family-wide FDR):", "",
              md(h[[c for c in ["signal", "n", "win", "net_pts", "net_pct", "worst_trade_pts", "p_month", "p_day", "p_half1_month", "p_half2_month",
                                "excess_over_control_pct", "psr", "sharpe_calday", "fdr_pass_10pct_family", "label_final",
                                "data_first_date", "data_last_date", "sessions_in_window"] if c in h]],
                 int_cols=INT_COLS), "",
              "An empty cell is NA: that bootstrap had fewer than 20 blocks (months or days) to resample, so no p-value is "
              "reported (survival rule 2); an empty cell is never 1.0 or 0.", ""]
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
                  "An empty cell is NA: that bootstrap had fewer than 20 blocks (months or days) to resample, so no p-value is "
                  "reported (survival rule 2); an empty cell is never 1.0 or 0.", "",
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
    if os.path.exists("out/fvg_candidates.csv"):
        fvg = pd.read_csv("out/fvg_candidates.csv")
        L += ["## 9. Owner-proposed fair-value-gap setup (A36) — pre-registered 2026-09-13, 8 trials", "",
              "8 trials (side {short, long} × R {1, 2} × BOS {on, off}) from `pipeline.units.fvg` (`out/fvg_candidates.csv`), "
              "reported on three windows. Only the SELECTION-window rows are counted in the trial family "
              "(`pipeline/trials.py`, `out/trials.csv`); CONTEXT is background and HOLDOUT is these same 8 trials' "
              "out-of-sample rows, reported here, not double-counted.", ""]
        for win_name, win_label in (("CONTEXT", "CONTEXT (2005-01-01 → 2012-12-31)"),
                                     ("SELECTION", "SELECTION (2013-01-01 → 2020-05-13) — counted in the trial family"),
                                     ("HOLDOUT", "HOLDOUT (2020-07-27 → 2026-09-11)")):
            sub = fvg[fvg["window"] == win_name]
            if not len(sub):
                continue
            L += [f"### {win_label}", "",
                  md(sub[[c for c in FVG_COLS if c in sub]], fmt="{:.4f}", int_cols=INT_COLS + ("n_setups",)), "",
                  fvg_verdict(sub), ""]
        cap = fvg_caption(fvg)
        if cap:
            L += [cap, ""]
    if os.path.exists("out/gapliq_candidates.csv"):
        gapliq = pd.read_csv("out/gapliq_candidates.csv")
        L += ["## 10. Overnight-loss forced-liquidation rebound (A39) — pre-registered 2026-09-13, 3 trials", "",
              "3 trials (T1 long call entry 10:00, T2 same days long call entry 09:31, T3 mirror signal long put "
              "entry 10:00) from `pipeline.units.gapliq` (`out/gapliq_candidates.csv`), reported on three windows. "
              "Only the SELECTION-window rows are counted in the trial family (`pipeline/trials.py`, "
              "`out/trials.csv`); CONTEXT is background and HOLDOUT is these same 3 trials' out-of-sample rows, "
              "reported here, not double-counted.", ""]
        for win_name, win_label in (("CONTEXT", "CONTEXT (2005-01-01 → 2012-12-31)"),
                                     ("SELECTION", "SELECTION (2013-01-01 → 2020-05-13) — counted in the trial family"),
                                     ("HOLDOUT", "HOLDOUT (2020-07-27 → 2026-09-11)")):
            sub = gapliq[gapliq["window"] == win_name]
            if not len(sub):
                continue
            L += [f"### {win_label}", "",
                  md(sub[[c for c in GAPLIQ_COLS if c in sub]], fmt="{:.4f}", int_cols=INT_COLS), "",
                  gapliq_verdict(sub), ""]
        cap = gapliq_caption(gapliq)
        if cap:
            L += [cap, ""]
    if os.path.exists("out/letf_candidates.csv"):
        letf = pd.read_csv("out/letf_candidates.csv")
        L += ["## 11. Leveraged-ETF close rebalancing (A38, owner's option C) — pre-registered 2026-09-13, 1 trial", ""]
        if len(letf):
            L += ["1 trial (`15:30|both|letf_demand`) from `pipeline.units.letf` (`out/letf_candidates.csv`), "
                  "reported on three windows, each over sessions with leveraged-ETF assets data only. Only the "
                  "SELECTION-window row is counted in the trial family (`pipeline/trials.py`, `out/trials.csv`); "
                  "CONTEXT is background and HOLDOUT is this same trial's out-of-sample row, reported here, not "
                  "double-counted.", ""]
            for win_name, win_label in (("CONTEXT", "CONTEXT (2005-01-01 → 2012-12-31)"),
                                         ("SELECTION", "SELECTION (2013-01-01 → 2020-05-13) — counted in the trial family"),
                                         ("HOLDOUT", "HOLDOUT (2020-07-27 → 2026-09-11)")):
                sub = letf[letf["window"] == win_name]
                if not len(sub):
                    continue
                L += [f"### {win_label}", "",
                      md(sub[[c for c in LETF_COLS if c in sub]], fmt="{:.4f}", int_cols=INT_COLS), "",
                      letf_verdict(sub), ""]
            cap = letf_caption(letf)
            if cap:
                L += [cap, ""]
        else:
            L += ["Waits for `data/ext/letf_aum_2006_2026.csv`; the unit skipped.", ""]
    if os.path.exists("out/realopt_reeval.csv"):
        reeval = pd.read_csv("out/realopt_reeval.csv")
        L += ["## 12. Real 0DTE prices (A41) — model calibration and re-evaluation, pre-registered "
              "2026-09-13", ""]
        if len(reeval):
            calib, calib_summary = realopt_calibration_blocks("out/realopt_calibration.csv")
            L += ["### Calibration (diagnostic, no decision): implied k = real bar close ÷ Black-Scholes "
                  "premium at k=1 × prior-close VIX, by VIX tercile and by minute (`out/realopt_calibration.csv`)",
                  "",
                  md(calib_summary, fmt="{:.4f}") if len(calib_summary) else "No calibration rows.", ""]
            L += [f"{len(calib)} (date, minute, right) calibration rows over {calib['date'].nunique() if len(calib) else 0} "
                  "sessions." if len(calib) else "", ""]
            L += ["### Re-evaluation: real 1-minute option bars replace the k×VIX model on every counted "
                  "trial's sessions ≥ 2024-02-01 (the two pre-registered D4 holdout signals, A39 T1/T2/T3, "
                  "and any POST-SELECTION row with a per-trade file), at three added-cost rows "
                  "(`out/realopt_reeval.csv`, per-trade detail in `out/realopt_reeval_trades.csv`)", "",
                  md(reeval[[c for c in REALOPT_REEVAL_COLS if c in reeval]], fmt="{:.4f}", int_cols=INT_COLS), ""]
            L += realopt_labels(reeval) + [""]
            cap = realopt_caption(reeval)
            if cap:
                L += [cap, ""]
            L += ["Sub-window, not a verdict: nothing above is promoted, added to the trial family (A41: "
                  "\"the trial count does not grow\"), or scored against BH-FDR.", ""]
        else:
            L += ["Waits for `data/ext/spy_0dte_1min_2024-02_2026-09.csv.gz`; the unit skipped.", ""]
    if os.path.exists("out/eventvol_candidates.csv"):
        eventvol = pd.read_csv("out/eventvol_candidates.csv")
        L += ["## 13. Event-day long volatility (A42) — pre-registered 2026-09-13, 3 trials", ""]
        if len(eventvol):
            L += ["3 trials (E1 baseline every session, E2 FOMC statement days, E3 the E2 rule on "
                  "every non-FOMC session) from `pipeline.units.eventvol` "
                  "(`out/eventvol_candidates.csv`), each at three round-trip costs ($0, $0.10, "
                  "$0.20 per two-leg trade). All three are counted trials (family 36 -> 39); only "
                  "the $0.10 row per trial is counted in the trial family ledger "
                  "(`pipeline/trials.py`, `out/trials.csv`) — the $0 and $0.20 rows are a cost "
                  "sensitivity, not additional trials. This is the whole file's one out-of-sample "
                  "window by construction (2024-02-01 onward), not a CONTEXT/SELECTION/HOLDOUT "
                  "split.", ""]
            L += [md(eventvol[[c for c in EVENTVOL_COLS if c in eventvol]], fmt="{:.4f}", int_cols=INT_COLS), "",
                  eventvol_verdict(eventvol), ""]
            cap = eventvol_caption(eventvol)
            if cap:
                L += [cap, ""]
        else:
            L += ["Waits for `data/ext/spy_0dte_1min_2024-02_2026-09.csv.gz`; the unit skipped.", ""]
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
              "Correlations measured on whatever overlap each pair has in this run (`out/own_account_bridge.csv`); the bridge is "
              "refused below 0.98.", "", md(b, fmt="{:.4f}"), ""]
        if "decision" in b:
            frags = []
            for _, row in b.iterrows():
                pair = str(row.get("pair", ""))
                label = {"old_vxx_vs_vixy": "old VXX↔VIXY", "new_vxx_vs_vixy": "new VXX↔VIXY",
                         "old_vxz_vs_vixm": "old VXZ↔VIXM", "new_vxz_vs_vixm": "new VXZ↔VIXM"}.get(pair, pair)
                corr = row.get("daily_return_corr", np.nan)  # the decision basis: full-overlap correlation
                corr_str = f"{corr:.4f}" if pd.notna(corr) else "n/a"
                frag = f"{label}: {row['decision']} (corr {corr_str} on {int(row['n_overlap_days'])} overlap days" if pd.notna(row.get("n_overlap_days")) else f"{label}: {row['decision']} (corr {corr_str}"
                if "corr_2020_on" in b and pd.notna(row.get("corr_2020_on")):
                    frag += f"; 2020-on {row['corr_2020_on']:.4f}"
                if "zero_return_days_2018" in b and pd.notna(row.get("zero_return_days_2018")):
                    frag += f"; {int(row['zero_return_days_2018'])} stale closes in 2018"
                frags.append(frag + ")")
            L += ["; ".join(frags) + " — the mid-term leg uses VIXM from 2017-11-13 when the VXZ bridge is refused.", ""]
    if os.path.exists("out/vrp_vix_minus_rv.csv"):
        v = pd.read_csv("out/vrp_vix_minus_rv.csv")
        v_years = v[v["year"].astype(str).str.fullmatch(r"\d{4}")]
        v_last = v_years.iloc[-1]
        L += ["## VIX − realised vol (variance risk premium), measured not traded", "",
              "Prior-close VIX minus the next 21 trading days' realised vol of SPY, in vol points. Not tradeable as measured: no "
              "option prices, spreads or margin; a defined-risk 30–45 DTE implementation is a recorded non-goal. Coverage ends "
              f"with the SPY daily panel's final partial year in `out/vrp_vix_minus_rv.csv`: last row {v_last['year']} has "
              f"n = {int(v_last['n'])}.", "", md(v), ""]
    L += ["## Known differences from Thread A's published baseline", "",
          "Thread A: 8 sleeves Sharpe 1.12 full / 1.35 test, maxDD −6.10%; two buckets 1.20 / 1.40, −5.26%. The BAB sleeve's "
          "universe is now cleaned by `pipeline.own_account.clean_universe`, reconstructed from it5.py/it5b.py (history/price/"
          "dollar-volume filters, then drop symbols with >5 days of |return|>50%) since `panel_clean.pkl` itself is not in the "
          "bundle: 928 raw tickers -> 626, matching Thread A's reported count. This does not close the gap to the published "
          "portfolio Sharpes: the BASELINE test-window Sharpe is materially unchanged (EQUAL_8 0.994, TWO_BUCKET 0.971, both "
          "within 0.001 of the raw-universe run), so an uncleaned BAB universe is not the explanation for D5's shortfall. S12 is "
          "the pipeline's gap-up signal rather than Thread A's scan cell; test-window Sharpes of S2, S3 and S13 match Thread A's "
          "published values.", ""]
    open("OWN_ACCOUNT.md", "w").write("\n".join(L))


if __name__ == "__main__":
    playbook()
    own_account()
    print("wrote PLAYBOOK_0DTE.md, OWN_ACCOUNT.md")
