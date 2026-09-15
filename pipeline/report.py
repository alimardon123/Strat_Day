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


FLATTEN_COLS = ["trial", "side", "entry_time", "n_signal_days", "n_skipped", "n", "win", "net_pts_cost1",
                "net_pts_cost2", "net_pct_cost1", "worst_trade_pts_cost1", "worst_day_pts_cost1", "sharpe_calday",
                "p_boot_day", "p_boot_month", "control_mean_pts_cost1", "frac_seeds_beaten",
                "timing_control_pts_cost1", "frac_timing_beaten", "opt_mean_pct_s1", "dsr_N45"]


def flatten_verdict(sub):
    """Generated per-window verdict for the A46/A46a flatten family: U1's survival on the same
    four programmatic checks as the FVG/GAPLIQ verdicts (net > 0 at 1 pt, p_day < 0.05, excess
    over the day-selection control > 0, n >= 200; DSR at N=45 is reported in the table, not a
    survival condition here either) AND the amendment's mechanism fingerprint (U2 < U1; U3 <= 0 at
    1 pt), then the promotion decision per the amendment's kill/promotion rule."""
    u1 = sub[sub["trial"] == "U1"]
    u2 = sub[sub["trial"] == "U2"]
    u3 = sub[sub["trial"] == "U3"]
    if u1.empty:
        return "U1 missing from this window."
    u1 = u1.iloc[0]
    net_pos = bool(u1["net_pts_cost1"] > 0)
    p_sig = bool(u1["p_boot_day"] < 0.05) if pd.notna(u1["p_boot_day"]) else False
    excess = u1["net_pts_cost1"] - u1["control_mean_pts_cost1"]
    beats_control = bool(excess > 0) if pd.notna(excess) else False
    n_ok = bool(u1["n"] >= 200)
    survives = net_pos and p_sig and beats_control and n_ok
    u2_lt_u1 = bool(u2.iloc[0]["net_pts_cost1"] < u1["net_pts_cost1"]) if len(u2) and pd.notna(u2.iloc[0]["net_pts_cost1"]) else False
    u3_le_zero = bool(u3.iloc[0]["net_pts_cost1"] <= 0) if len(u3) and pd.notna(u3.iloc[0]["net_pts_cost1"]) else False
    fingerprint_ok = u2_lt_u1 and u3_le_zero
    promoted = survives and fingerprint_ok
    decision = ("U1 promotable" if promoted else
               "pattern without its mechanism, not promoted" if survives else
               "U1 does not survive, not promoted")
    return (f"U1: net {'>' if net_pos else '<='} 0 at 1 pt, p_day {'<' if p_sig else '>='} 0.05, excess over the "
            f"day-selection control {'>' if beats_control else '<='} 0, n {'>=' if n_ok else '<'} 200 -> "
            f"{'SURVIVES' if survives else 'does not survive'} the four programmatic checks (DSR at N=45 is reported "
            f"in the table above, not a survival condition). Fingerprint: U2 {'<' if u2_lt_u1 else '>='} U1 "
            f"({'holds' if u2_lt_u1 else 'fails'}); U3 {'<=' if u3_le_zero else '>'} 0 at 1 pt "
            f"({'holds' if u3_le_zero else 'fails'}). Promotion: {decision}.")


def flatten_caption(df):
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


def _csv_rows_or_none(path, filt=None):
    """Read `path` and return the (optionally `filt`-filtered) DataFrame, or None when there is no
    usable row: file missing, zero bytes, an unparsable CSV (`pd.errors.EmptyDataError`), or a
    frame `filt` reduces to zero rows. A bare exists()/getsize() guard is not enough — a
    header-only CSV (size > 0, zero data rows) is exactly the empty-output convention four sibling
    fleet units (letf.py, realopt.py, eventvol.py, sellvol.py) already write in their own
    no-data branch, and it still raises IndexError on the caller's `.iloc[0]`."""
    if not os.path.exists(path) or os.path.getsize(path) == 0:
        return None
    try:
        df = pd.read_csv(path)
    except pd.errors.EmptyDataError:
        return None
    if filt is not None:
        df = filt(df)
    return df if len(df) else None


def contract_size_clause():
    """Section 6 (D7): the 2%-ITM contract cost, read from `out/sizing_forward.csv`
    (`pipeline.units.sizing`) when the measured level is available, so the dollar figures are
    anchored to the extended frame's own last COMPLETE regular-session close instead of an assumed
    index level. Falls back to the original assumed-S wording (S = 6,500) when the file is absent,
    empty, or has no row -- reason given precisely: the post-May-2020 minute feed is absent
    (`data/ext`, see DATA.md), never the false claim that no measured level exists when a stale
    minute file (or a header-only daily parquet) is actually sitting there.

    Per A45 rule 1, x = 1% of account equity per trade is the convention for every sizing figure
    published after the amendment (2026-09-15); this section was recomputing a NEW minimum-account
    figure at the OLD (pre-A45, 4%-of-equity) convention on every run, which is itself such a
    figure. This section therefore STOPS publishing any minimum account: it states the measured
    contract cost only (a market fact, not a sizing rule) and points to §15, the single place the
    minimum account is stated, under the rule in force."""
    sf = _csv_rows_or_none("out/sizing_forward.csv")
    if sf is None:
        return ("A 2% ITM SPX option costs ≈ 2% × S × 100 ≈ $13,000 at S = 6,500 (an assumed current index level: "
                "the post-May-2020 minute feed is absent, `data/ext`, see DATA.md, so no current level is measured "
                "here and the figure falls back to this assumed S; every dollar figure scales linearly with S); XSP "
                "and SPY are one tenth, SPY settled physically so its position is exited by 15:55, not held to the "
                "close. The minimum account per contract for forward trading is given in §15 under A45 rule 1 (x = "
                "1% of account equity per trade); the pre-A45 minimum account previously stated in this section is "
                "superseded by that rule, not restated here. Max positions per day: 2 (the two signals can "
                "coincide).")
    row = sf.iloc[0]   # level and costs are identical on every row of this file (one measured level); any row will do
    return (f"A 2% ITM SPX option costs ≈ 2% × S × 100 ≈ ${row['cost_spx_usd']:,.0f} at the measured "
            f"{row['level_date']} close S = {row['level_spx_pts']:,.2f} SPX-equivalent points "
            f"(`out/sizing_forward.csv`; every dollar figure scales linearly with S); XSP and SPY are one tenth "
            f"(≈ ${row['cost_xsp_usd']:,.0f}), SPY settled physically so its position is exited by 15:55, not held "
            "to the close. The minimum account per contract for forward trading is given in §15 under A45 rule 1 "
            "(x = 1% of account equity per trade); the pre-A45 minimum account previously stated in this section is "
            "superseded by that rule, not restated here. Max positions per day: 2 (the two signals can coincide).")


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


def k13_relabel_clause(calib_summary):
    """A41: "if the median k at 15:00/15:30 differs from 1.3 by more than 0.3, the playbook's k = 1.3
    base case is re-labelled with the measured value" — generated from out/realopt_calibration.csv's
    own by-minute summary rows (never typed). The conditional is evaluated at EACH of the two named
    minutes independently (the amendment names one threshold checked at two minutes, not which of the
    two wins a tie): it fires if EITHER |1.3 - median_implied_k| exceeds 0.3. Empty string if either
    minute's summary row is missing (calibration hasn't run)."""
    minute = calib_summary[calib_summary["group_type"] == "minute"] if len(calib_summary) else calib_summary
    row_1500 = minute[minute["group_value"] == "15:00"] if len(minute) else minute
    row_1530 = minute[minute["group_value"] == "15:30"] if len(minute) else minute
    if not len(row_1500) or not len(row_1530):
        return ""
    d1500 = abs(1.3 - float(row_1500["median_implied_k"].iloc[0]))
    d1530 = abs(1.3 - float(row_1530["median_implied_k"].iloc[0]))
    fired = d1500 > 0.3 or d1530 > 0.3
    verdict = ("fired: the playbook's k = 1.3 base case is re-labelled with the measured value"
              if fired else
              "did not fire: the label stands on the rule and on unidentifiability")
    return (f"A41's k = 1.3 re-label conditional against the 0.3 threshold: |1.3 − median implied k| "
            f"= {d1500:.3f} at 15:00 and {d1530:.3f} at 15:30 — the conditional {verdict}.")


def fill_delay_clause(trades):
    """A41 clarification (judge round 7): the fill-delay profile of every re-priced trade's entry
    fill against its own signal minute — `entry_bar_mod` (the bar actually used) minus `entry_mod`
    (the signal's nominal entry minute), both new TRADE_COLS columns added by the round-7 fix to
    `pipeline.units.realopt.reprice_trades` — read from out/realopt_reeval_trades.csv, never typed.
    Empty string if the trades file lacks the new columns (an older run) or has no rows."""
    if "entry_bar_mod" not in trades or "entry_mod" not in trades or not len(trades):
        return ""
    delay = trades["entry_bar_mod"] - trades["entry_mod"]
    return (f"Fill-delay profile (entry bar actually used vs. the signal's own entry minute, all "
            f"{len(trades)} re-priced trades, `out/realopt_reeval_trades.csv`): median "
            f"{delay.median():.0f} minutes, 90th percentile {delay.quantile(0.9):.0f} minutes, "
            f"maximum {delay.max():.0f} minutes, {int((delay >= 15).sum())} trades ≥ 15 minutes late.")


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


# §15: the owner's 8-rule trading rulebook (ACCEPTANCE.md amendment A45), typed from the
# amendment text (a contract, not a measured finding) -- never generated from out/, EXCEPT rule
# 1's stated x, which is derived from out/sizing_forward.csv's own A45-convention x_pct column
# (a45_rules() below) so the typed rule cannot silently drift from the generated sizing table it
# sits above.
def a45_rules(sf):
    """The 8-rule table for §15. `sf` is `out/sizing_forward.csv` (or None, absent/empty) --
    only rule 1's `x` is read from it (`x_pct` on its `A45`-convention rows, all identical by
    construction); every other cell is a typed transcription of the amendment text, unchanged by
    `sf`. A typed 1% default stands when `sf` is unavailable.

    Rule 2's status cell states BOTH halves of ACCEPTANCE.md's own self-contradicting contract:
    the A45 preamble lists rule 2 among those "already in force", but rule 2's own text calls
    itself "NEW for the prop account" and names A42 E1 and A43 S1/S3 as registered candidates that
    entered at 09:31, not 10:00. Silently picking one side would misstate the amendment; the other
    seven rules' status/audit cells are faithful as typed and are unchanged here."""
    a45_sz = sf[sf["convention"] == "A45"] if sf is not None and "convention" in sf else None
    x_pct = float(a45_sz["x_pct"].iloc[0]) if a45_sz is not None and len(a45_sz) else 1.0
    return [
        {"#": 1, "rule": f"Per-trade sizing (AMENDS the numeric budget): x = {x_pct:g}% of account equity per trade, "
                         "N = floor(daily limit / x) full-loss attempts per day", "status": "NEW", "audit": "owner journal"},
        {"#": 2, "rule": "No entries in the first 30 minutes (no entry before 10:00 ET)",
         "status": "already in force (A45 preamble); rule text marks it NEW for the prop account", "audit": "pipeline"},
        {"#": 3, "rule": "ITM-only strikes; no ATM or OTM contracts", "status": "already in force", "audit": "pipeline"},
        {"#": 4, "rule": "No increase in size or trade frequency after a loss", "status": "NEW", "audit": "owner journal"},
        {"#": 5, "rule": "Resting limit orders at the mid, not marketable orders", "status": "NEW",
         "audit": "owner journal; not measurable until the no-live-execution non-goal is relaxed"},
        {"#": 6, "rule": "Every rule and candidate is pre-registered and counted in the trial family before any run",
         "status": "already in force", "audit": "pipeline"},
        {"#": 7, "rule": "No trade taken only to satisfy a consistency or minimum-days rule", "status": "NEW", "audit": "owner journal"},
        {"#": 8, "rule": "Unaudited prop-firm statistics are never used as facts", "status": "already in force", "audit": "pipeline"},
    ]


# §16: A47's detectability floor -- an ANALYSIS of measurements already published, never a trial
# (ACCEPTANCE.md amendment A47). Both helpers below are generated straight from
# `out/power_analysis.csv` (D7: tables generated, never typed); neither computes anything new --
# `pipeline.units.power` is the only place any of these numbers is derived.
POWER_COLS = ["candidate", "window", "n", "mean_net_pts", "sd_net_pts", "mde_at_n", "mde_at_200",
              "n_req_1pt", "years_to_n_req_1pt"]


def power_caption(df):
    """Generated from `out/power_analysis.csv` itself: the worst case in the table -- the row with
    the largest `mde_at_200` (the effect the 200-trade floor is LEAST able to see) -- stated in
    plain words with its own numbers, then A47's own stated refutation condition (the 200-trade
    floor detects effects at or below the 1-2 point cost band) checked against every row's
    `mde_at_200` against 2.0 pts, written both ways so the sentence is correct whichever way the
    data falls (never assumed)."""
    if not len(df):
        return ""
    worst = df.loc[df["mde_at_200"].idxmax()]
    n_at_or_below_2 = int((df["mde_at_200"] <= 2.0).sum())
    if n_at_or_below_2 == len(df):
        refutation = (f"A47's own refutation condition -- the n=200 floor detects effects at or below the 1-2 "
                      f"point cost band -- is MET (all {len(df)} of {len(df)} rows have mde_at_200 <= 2.0 pts): "
                      "the survival rule is adequately powered at n=200, the UNDERPOWERED labels reflect a "
                      "genuine shortage of signals rather than a design limit, and option B (forward-testing to "
                      "n=200) is worth running.")
    else:
        refutation = (f"A47's own refutation condition -- the n=200 floor detects effects at or below the 1-2 "
                      f"point cost band -- is NOT met (only {n_at_or_below_2} of {len(df)} rows have mde_at_200 "
                      "<= 2.0 pts): the 200-trade floor cannot be assumed adequately powered for most of these "
                      "candidates, so at least part of the UNDERPOWERED label reflects the design's own "
                      "detectability floor, not only a shortage of signals.")
    years_clause = (f"{worst['years_to_n_req_1pt']:.1f} years of signals at its own observed rate"
                    if worst["years_to_n_req_1pt"] == worst["years_to_n_req_1pt"] else "an unknown number of years (no signal rate available)")
    return (f"Worst case in the table: `{worst['candidate']}` ({worst['window']}, n={int(worst['n'])}, "
            f"sd={worst['sd_net_pts']:.2f} pts/trade) -- the n=200 floor cannot detect an effect smaller than "
            f"{worst['mde_at_200']:.2f} pts/trade there, and establishing a 1.0-point edge ({int(worst['n_req_1pt']):,} "
            f"trades required) would take {years_clause}. {refutation}")


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
          contract_size_clause(), "",
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
            k13_clause = k13_relabel_clause(calib_summary)
            if k13_clause:
                L += [k13_clause, ""]
            L += ["### Re-evaluation: real 1-minute option bars replace the k×VIX model on every counted "
                  "trial's sessions ≥ 2024-02-01 (the two pre-registered D4 holdout signals, A39 T1/T2/T3, "
                  "and any POST-SELECTION row with a per-trade file), at three added-cost rows "
                  "(`out/realopt_reeval.csv`, per-trade detail in `out/realopt_reeval_trades.csv`)", "",
                  md(reeval[[c for c in REALOPT_REEVAL_COLS if c in reeval]], fmt="{:.4f}", int_cols=INT_COLS), ""]
            L += realopt_labels(reeval) + [""]
            cap = realopt_caption(reeval)
            if cap:
                L += [cap, ""]
            trades_path = "out/realopt_reeval_trades.csv"
            if os.path.exists(trades_path) and os.path.getsize(trades_path) > 0:
                delay_clause = fill_delay_clause(pd.read_csv(trades_path))
                if delay_clause:
                    L += [delay_clause, ""]
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
    if os.path.exists("out/flatten_candidates.csv"):
        flatten = pd.read_csv("out/flatten_candidates.csv")
        L += ["## 14. Intraday forced-flattening rebound (A46/A46a) — pre-registered 2026-09-15, 3 trials", "",
              "3 trials (U1 long call entry 11:00 on days with open->11:00 return <= the expanding 10th pct, "
              "U2 long call entry 11:00 on the mild-decline band -- <= the expanding 30th pct AND > the expanding "
              "10th pct, A46a's causal replacement for the registered-but-defective 09:45 timing fingerprint -- "
              "U3 mirror signal long put entry 11:00 on days >= the expanding 90th pct) from `pipeline.units."
              "flatten` (`out/flatten_candidates.csv`), reported on three windows. Only the SELECTION-window rows "
              "are counted in the trial family (`pipeline/trials.py`, `out/trials.csv`); CONTEXT is background and "
              "HOLDOUT is these same 3 trials' out-of-sample rows, reported here, not double-counted -- the "
              "amendment's verdict is judged on HOLDOUT.", ""]
        for win_name, win_label in (("CONTEXT", "CONTEXT (2005-01-01 → 2012-12-31)"),
                                     ("SELECTION", "SELECTION (2013-01-01 → 2020-05-13) — counted in the trial family"),
                                     ("HOLDOUT", "HOLDOUT (2020-07-27 → 2026-09-11) — the verdict window (A46)")):
            sub = flatten[flatten["window"] == win_name]
            if not len(sub):
                continue
            L += [f"### {win_label}", "",
                  md(sub[[c for c in FLATTEN_COLS if c in sub]], fmt="{:.4f}", int_cols=INT_COLS), "",
                  flatten_verdict(sub), ""]
        cap = flatten_caption(flatten)
        if cap:
            L += [cap, ""]
    sf = _csv_rows_or_none("out/sizing_forward.csv")
    L += ["## 15. Trading rulebook in force (A45) — adopted 2026-09-15 (owner's option F)", "",
          "This is a contract the owner adopted, recorded in `ACCEPTANCE.md` amendment A45, not a measured finding; it "
          "governs how the signals above are traded, and every candidate registered after it must comply with rules 2 "
          "and 3 at registration time.", "",
          "The table below is typed from `ACCEPTANCE.md` amendment A45's own text, not generated from out/ — it is a "
          "transcription of a contract, not a measured table — except rule 1's stated x, read from "
          "`out/sizing_forward.csv` when available so it cannot silently drift from the generated sizing table below it.", "",
          md(pd.DataFrame(a45_rules(sf))), ""]
    a45_sz = sf[sf["convention"] == "A45"] if sf is not None and "convention" in sf else None
    if a45_sz is not None and len(a45_sz):
        r0 = a45_sz.iloc[0]
        L += [f"A45 forward-sizing table (rule 1), generated from `out/sizing_forward.csv`, anchored to the "
              f"{r0['level_date']} measured close (S = {r0['level_spx_pts']:,.2f} SPX-equivalent points):", "",
              md(a45_sz[["daily_limit_pct", "x_pct", "attempts_per_day", "cost_spx_usd", "min_account_spx_usd",
                         "min_account_xsp_usd", "min_account_spy_usd"]], fmt="{:,.0f}",
                 int_cols=("attempts_per_day",)), "",
              "The minimum account is the same on all three rows because A45 rule 1 fixes x at 1% of equity "
              "independently of the daily limit; the limit changes only how many full-loss attempts the day "
              "allows.", ""]
    else:
        L += ["The measured level is unavailable (`out/sizing_forward.csv` is absent, empty, or has no usable row), "
              "so the A45 forward-sizing table is not produced.", ""]
    L += ["§4's sizing table and `TRACK_C.md`'s A43 table are NOT restated and remain labelled under the convention "
          "in force when they were computed. §6's pre-A45 minimum account has been RETIRED from §6 rather than "
          "restated: A45 rule 1 (x = 1% of account equity per trade) governs any sizing figure published after the "
          "amendment, and the table above is the single minimum-account statement for forward trading.", ""]
    pw = _csv_rows_or_none("out/power_analysis.csv")
    L += ["## 16. What this design can detect (A47) — an analysis of published measurements, not a trial", "",
          "This section computes, for every candidate that already has a published per-trade series, the minimum "
          "effect the six-condition survival rule's n=200 holdout-trade floor is capable of detecting, from the "
          "per-trade dispersion already observed in each candidate's own trades (`out/power_analysis.csv`, "
          "`pipeline.units.power`). **It adds ZERO trials, computes no new signal, opens no new window, fits no "
          "parameter and can promote nothing: the family stays at 45.**", ""]
    if pw is not None:
        L += [md(pw[[c for c in POWER_COLS if c in pw]], int_cols=INT_COLS), "", power_caption(pw), ""]
    else:
        L += ["`out/power_analysis.csv` is absent, empty, or has no usable row (e.g. the post-May-2020 minute "
              "feed, `data/ext`, is absent, DATA.md); this section cannot be generated.", ""]
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
