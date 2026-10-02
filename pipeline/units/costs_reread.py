"""A51 M4 -- the published HOLDOUT per-trade series re-read at the measured cost Cm (information, never a verdict).

    from pipeline.units import costs_reread
    df = costs_reread.reread(cm, cm_intraday)      # 19 rows, columns COLS, sorted by family then trial

A51 M4 (ACCEPTANCE.md:1033-1060, fixed before any quote existed): each of the 19 enumerated HOLDOUT per-trade series is shifted
from the 1.0-point round trip every published net was charged to the measured cost `cm` (per-trade net = gross - cm, gross = net
at 1 pt + 1.0) and scored by the survival rule's six conditions, unchanged (R2):
  1. net mean > 0;
  2. one-sided day-block bootstrap p < 0.05 (`stats.one_sided_p`, seed 11, `stats.day_blocks`);
  3. BH-FDR at 10% across the 19 re-read rows jointly (`stats.bh_fdr`, one test per row, not per family);
  4. the PUBLISHED excess over the day-selection control > 0 -- read from the family's own candidates file, never recomputed: the
     control pays the same cost as the trade, so a uniform cost change cannot move it (A51's R4 paragraph);
  5. deflated Sharpe > 0.95 at the trial's OWN published N, built exactly the way its family's unit builds it;
  6. n >= 200.
A row passing all six is labelled QUALIFIES FOR A FORWARD TEST (otherwise DOES NOT QUALIFY); `cond_failed` lists the failing
numbers, comma-separated and ascending, empty when all six pass. fvg and oflow rows also get net mean and day-block p at
`cm_intraday` (a sensitivity, not a second test; blank for the other families).
Nothing here is a trial: out/trials.csv is untouched and no published number is revised.

Where each family's gross series comes from (gross = per-trade index points before any cost). File:line references are to
commit c77ed45 (the tree A51 was registered on); only gapliq.py has moved since (A52.3: +1 line in summarize(), +4 in main()):
  * D1 winner / gap-up call: `pts` of out/holdout_d4_*_s1_cash_k1.0.csv. `pts` IS gross: mean(pts) - 1.0 is the published
    holdout net_pts (insample.py:59). The k and spread in the file name only price the option leg, `pts` is the same in all of them.
  * fvg: `pts` of the FILLED HOLDOUT rows of out/fvg_candidates_trades.csv (fvg.py:288, net_pts_cost1 = pts - COST1).
  * gapliq / flatten / oflow: `net_pts_cost1 + 1.0` of the HOLDOUT rows of their `*_trades.csv` (these files carry no gross column;
    gapliq.py:189, flatten.py:250, oflow.py:369).

Decisions A51's text leaves open (each found by reading the family's unit, and each needed for the self-check to be exact):
  * Conditions 2 and 5 are computed on the NET-PERCENT series, as every family's unit computes its published p_boot_day and DSR:
    net % = ret_pct - 100*cost/entry_px = 100*net pts/entry_px (fvg.py:304-307, gapliq.py:193,206, flatten.py:254,267,
    oflow.py:373,386; D1/D2: insample.py:58,67,77). The cost shift is the same cm in points, expressed in the unit the family
    infers in. The published PSR of the D1 winner is 0.363546 on net % and 0.456946 on net points, so this is not cosmetic.
    Conditions 1 and 4 stay in points (insample.py:71 `net_pts.mean() > 0`; report.py:64,101,149,200 `net_pts_cost1 - control`).
  * DSR: PSR (N = 1, SR0 = 0) for the two pre-registered D1/D2 signals (insample.py:67); for fvg / gapliq / flatten / oflow
    `stats.deflated_sharpe(x, sr_trials=sr_pool, n=DSR_N)` with N = 33 / 37 / 45 / 48 and sr_pool = the per-trade Sharpe of
    the net-% series of ALL the family's HOLDOUT trials (fvg.py:343-349, gapliq.py:245-251, flatten.py:306-312, oflow.py:437-439).
    At cm the pool is rebuilt from the SHIFTED series of the sibling trials, so SR0 moves with cm, as a re-run would move it.
  * published_excess_over_control is `net_pts_cost1 - control_mean_pts_cost1` (points) for fvg / gapliq / flatten / oflow and the
    published `excess_over_control_pct` (percent, the only form insample.py publishes) for the two D1/D2 rows. Only its sign is used.
  * `window` is HOLDOUT for every row (D1/D2 2020-06-01.., fvg/gapliq/flatten 2020-07-27.., oflow 2025-07-01.., all to 2026-09-11).

Self-check, built in: every call also scores the series at the published 1.0-pt cost (`reread_net_at_1pt`, `reread_p_day_at_1pt`,
`reread_dsr_at_1pt`) next to the published values and sets `reproduces_published`. n must match exactly; net, p and DSR must match
within REPRO_TOL = 1e-6 (the published precision is six decimals, and the per-trade inputs are themselves rounded to six decimals,
so identical arithmetic can differ in the last digit). Observed on the committed files: n identical, every p identical, net and
DSR within 5e-7. `self_check()` raises if any row fails.

Reads whatever the committed out/ files hold and checks that it reproduces itself, so it must run after the units that write them
(the D2 holdout, fvg, gapliq, flatten, oflow); a regeneration that changes a published row changes the re-read with it.

A51's R4 paragraph says gapliq and flatten (holdout n < 200) can never qualify. On the files committed with A52.3 that holds for
gapliq (n = 159 / 159 / 154) and flatten U1 / U3 (144 / 166). flatten U2 has n = 299, so condition 6 does not stop it; its
negative published excess (-1.17 pts) does, which is the paragraph's other clause ("neither can any row with a negative
published excess"). The conclusion stands.
"""
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from pipeline import stats

ROOT = Path(__file__).resolve().parents[2]
WINDOW = "HOLDOUT"
BASE_COST = 1.0             # SPX points round trip every published HOLDOUT net was charged (ACCEPTANCE.md:51)
P_MAX = 0.05                # survival rule 2
FDR_ALPHA = 0.10            # survival rule 3, across the re-read rows
DSR_MIN = 0.95              # survival rule 5
N_MIN = 200                 # survival rule 6
REPRO_TOL = 1e-6            # published values carry six decimals (float_format="%.6f")
N_SERIES = 19               # A51 M4 enumerates exactly 19 (R5)
LABEL_YES = "QUALIFIES FOR A FORWARD TEST"
LABEL_NO = "DOES NOT QUALIFY"

COLS = ["family", "trial", "window", "source_file", "n", "cm", "net_at_cm", "p_day_at_cm", "fdr_pass_at_cm",
        "published_excess_over_control", "dsr_N", "dsr_at_cm", "cond_failed", "label",
        "cm_intraday", "net_at_cm_intraday", "p_day_at_cm_intraday",
        "published_net_1pt", "reread_net_at_1pt", "published_p_day", "reread_p_day_at_1pt",
        "published_dsr", "reread_dsr_at_1pt", "reproduces_published", "note"]

HOLDOUT_SUMMARY = "out/holdout_summary.csv"
# family label (reconcile.py's own), published `signal` name, per-trade file (column `pts` = gross); N = 1 -> PSR
D4_SERIES = (("momentum", "15:00|both|vixmove_exp", "out/holdout_d4_1500_both_vixmove_exp_s1_cash_k1.0.csv"),
             ("gapup", "13:00|call|gap>0.3%", "out/holdout_d4_1300_call_gapgt0.3pct_s1_cash_k1.0.csv"))
# family -> (candidates file, per-trade file, the unit's DSR_N, shown at cm_intraday, the enumerated trials)
FAMILIES = {
    "fvg": ("out/fvg_candidates.csv", "out/fvg_candidates_trades.csv", 33, True,
            ("short|R1|bos_on", "short|R2|bos_on", "short|R1|bos_off", "short|R2|bos_off",
             "long|R1|bos_on", "long|R2|bos_on", "long|R1|bos_off", "long|R2|bos_off")),
    "gapliq": ("out/gapliq_candidates.csv", "out/gapliq_candidates_trades.csv", 37, False, ("T1", "T2", "T3")),
    "flatten": ("out/flatten_candidates.csv", "out/flatten_candidates_trades.csv", 45, False, ("U1", "U2", "U3")),
    "oflow": ("out/oflow_candidates.csv", "out/oflow_candidates_trades.csv", 48, True, ("T1", "T2", "T3")),
}
NOTES = {   # function-level anchors, not line numbers: the units move (the module docstring pins line numbers to c77ed45)
    "momentum": "gross = pts; p and PSR on net % (insample.holdout_tables: net_pct, psr, p_day); excess in % units (excess_over_control_pct)",
    "gapup": "gross = pts; p and PSR on net % (insample.holdout_tables: net_pct, psr, p_day); excess in % units (excess_over_control_pct)",
    "fvg": "gross = pts of filled rows; p and DSR on net % (fvg.summarize p_boot_day, fvg.main dsr_N33); excess in pts; touch-equals-fill entry",
    "gapliq": "gross = net_pts_cost1 + 1.0; p and DSR on net % (gapliq.summarize p_boot_day, gapliq.main dsr_N37); excess in pts",
    "flatten": "gross = net_pts_cost1 + 1.0; p and DSR on net % (flatten.summarize p_boot_day, flatten.main dsr_N45); excess in pts",
    "oflow": "gross = net_pts_cost1 + 1.0; p and DSR on net % (oflow.summarize p_boot_day, oflow.main dsr_N48); excess in pts (minute-level control)",
}


@dataclass(frozen=True, eq=False)
class TradeSeries:
    """One enumerated HOLDOUT series: per-trade gross points in the unit's own row order (the order the bootstrap's blocks are
    drawn in), the entry level its net-% series needs, and the family's PUBLISHED values it must reproduce at 1.0 pt."""
    family: str
    trial: str
    source_file: str
    dates: np.ndarray       # session date of each trade (the day blocks)
    gross: np.ndarray       # index points per trade before any cost = published net at 1 pt + 1.0
    entry_px: np.ndarray    # index level at entry: net % = 100 * net pts / entry_px
    dsr_n: int              # the trial's own published N (1 = PSR)
    intraday: bool          # fvg / oflow: also shown at cm_intraday
    pub_n: int
    pub_net: float          # published net mean at 1 pt (points)
    pub_p_day: float        # published one-sided day-block p (NaN = not published)
    pub_dsr: float          # published DSR / PSR (NaN = not published)
    pub_excess: float       # published excess over the day-selection control (condition 4; only its sign is used)
    note: str


def _finite(x, what):
    v = float(x)
    if not np.isfinite(v):
        raise ValueError(f"{what} must be finite, got {x!r}")
    return v


def net_pts(s, cost):
    """Per-trade net in index points at a round-trip `cost`."""
    return s.gross - cost


def net_pct(s, cost):
    """Per-trade net in percent at `cost`: the series every family's unit runs its bootstrap and DSR on."""
    return 100.0 * (s.gross - cost) / s.entry_px


def p_day(s, cost):
    """One-sided day-block bootstrap p (stats.one_sided_p, seed 11) of the net-% series at `cost`."""
    return stats.one_sided_p(net_pct(s, cost), stats.day_blocks(s.dates))


def family_dsr(series, cost):
    """DSR of every series at `cost`, indexed like `series`: N = the trial's own published N, SR0's pool = the per-trade Sharpe of
    the net-% series of every sibling trial (same family) at the SAME `cost` -- the unit's own construction, with shifted siblings."""
    out = {}
    for fam in dict.fromkeys(s.family for s in series):
        members = [i for i, s in enumerate(series) if s.family == fam]
        x = {i: net_pct(series[i], cost) for i in members}
        pool = [stats.per_trade_sharpe(x[i]) for i in members]
        for i in members:
            out[i] = (stats.deflated_sharpe(x[i], sr_trials=pool, n=series[i].dsr_n)[0] if len(x[i]) >= 3 else np.nan)
    return out


def failing_conditions(net, p, fdr_pass, excess, dsr, n):
    """The survival rule's six conditions (A51 M4), unchanged; returns the failing numbers, ascending. A NaN never passes."""
    checks = ((1, net > 0), (2, p < P_MAX), (3, bool(fdr_pass)), (4, excess > 0), (5, dsr > DSR_MIN), (6, n >= N_MIN))
    return [k for k, ok in checks if not ok]


def _matches(got, published, tol=REPRO_TOL):
    """True when `published` is absent (NaN: nothing to reproduce) or `got` agrees with it to the published precision."""
    if pd.isna(published):
        return True
    return bool(np.isfinite(got) and abs(got - published) <= tol)


def score_trials(series, cm, cm_intraday=None):
    """The M4 table for `series` at cost `cm` (and, for the intraday families, at `cm_intraday`): one row per series, COLS columns,
    sorted by family then trial. BH-FDR runs over every row passed in (the 19, jointly)."""
    cm = _finite(cm, "cm")
    ci = None if cm_intraday is None or pd.isna(cm_intraday) else _finite(cm_intraday, "cm_intraday")
    p_cm = np.array([p_day(s, cm) for s in series], float)
    fdr = stats.bh_fdr(np.where(np.isnan(p_cm), 1.0, p_cm), alpha=FDR_ALPHA)
    dsr_cm, dsr_base = family_dsr(series, cm), family_dsr(series, BASE_COST)
    rows = []
    for i, s in enumerate(series):
        n = len(s.gross)
        net = float(net_pts(s, cm).mean())
        failed = failing_conditions(net, p_cm[i], fdr[i], s.pub_excess, dsr_cm[i], n)
        net1, p1, dsr1 = float(net_pts(s, BASE_COST).mean()), p_day(s, BASE_COST), dsr_base[i]
        bad = [name for name, ok in (("n", n == s.pub_n), ("net", _matches(net1, s.pub_net)), ("p", _matches(p1, s.pub_p_day)),
                                     ("dsr", _matches(dsr1, s.pub_dsr))) if not ok]
        rows.append(dict(
            family=s.family, trial=s.trial, window=WINDOW, source_file=s.source_file, n=n, cm=cm, net_at_cm=net,
            p_day_at_cm=float(p_cm[i]), fdr_pass_at_cm=bool(fdr[i]), published_excess_over_control=s.pub_excess,
            dsr_N=s.dsr_n, dsr_at_cm=dsr_cm[i], cond_failed=",".join(str(k) for k in failed),
            label=LABEL_YES if not failed else LABEL_NO,
            cm_intraday=ci if (s.intraday and ci is not None) else np.nan,
            net_at_cm_intraday=float(net_pts(s, ci).mean()) if (s.intraday and ci is not None) else np.nan,
            p_day_at_cm_intraday=p_day(s, ci) if (s.intraday and ci is not None) else np.nan,
            published_net_1pt=s.pub_net, reread_net_at_1pt=net1, published_p_day=s.pub_p_day, reread_p_day_at_1pt=p1,
            published_dsr=s.pub_dsr, reread_dsr_at_1pt=dsr1, reproduces_published=not bad,
            note=s.note + (f"; DOES NOT REPRODUCE PUBLISHED: {','.join(bad)}" if bad else "")))
    df = pd.DataFrame(rows, columns=COLS)
    return df.sort_values(["family", "trial"], kind="stable").reset_index(drop=True)


def _read(rel):
    return pd.read_csv(ROOT / rel)


def _clean(a, what):
    a = np.asarray(a, float)
    if np.isnan(a).any():
        raise ValueError(f"{what}: NaN in a per-trade column")
    return a


def load_series():
    """The 19 enumerated series, built from the committed out/ files; raises if the enumeration does not hold (R5)."""
    summ = _read(HOLDOUT_SUMMARY)
    if not summ["signal"].is_unique:
        raise ValueError(f"{HOLDOUT_SUMMARY}: duplicate signal rows")
    summ = summ.set_index("signal")
    series = []
    for family, trial, rel in D4_SERIES:
        t, h = _read(rel), summ.loc[trial]
        series.append(TradeSeries(
            family=family, trial=trial, source_file=rel, dates=t["date"].to_numpy(), gross=_clean(t["pts"], rel),
            entry_px=_clean(t["entry_px"], rel), dsr_n=1, intraday=False, pub_n=int(h["n"]), pub_net=float(h["net_pts"]),
            pub_p_day=float(h["p_day"]), pub_dsr=float(h["psr"]), pub_excess=float(h["excess_over_control_pct"]),
            note=NOTES[family]))
    for family, (cand_rel, trades_rel, dsr_n, intraday, trials) in FAMILIES.items():
        cand = _read(cand_rel)
        cand = cand[cand["window"] == WINDOW].set_index("trial")
        tr = _read(trades_rel)
        tr = tr[tr["window"] == WINDOW]
        if sorted(tr["trial"].unique()) != sorted(trials) or sorted(cand.index) != sorted(trials):
            raise AssertionError(f"{family}: HOLDOUT trials {sorted(tr['trial'].unique())} / {sorted(cand.index)} != {sorted(trials)}")
        dsr_col = f"dsr_N{dsr_n}"
        for trial in trials:
            g, c = tr[tr["trial"] == trial], cand.loc[trial]
            if family == "fvg":
                if g["filled"].dtype != bool:
                    raise ValueError(f"{trades_rel}: `filled` is {g['filled'].dtype}, expected bool")
                g = g[g["filled"]]
                gross = g["pts"]
            else:
                gross = g["net_pts_cost1"] + BASE_COST
            series.append(TradeSeries(
                family=family, trial=trial, source_file=trades_rel, dates=g["date"].to_numpy(), gross=_clean(gross, trades_rel),
                entry_px=_clean(g["entry_px"], trades_rel), dsr_n=dsr_n, intraday=intraday, pub_n=int(c["n"]),
                pub_net=float(c["net_pts_cost1"]), pub_p_day=float(c["p_boot_day"]), pub_dsr=float(c[dsr_col]),
                pub_excess=float(c["net_pts_cost1"] - c["control_mean_pts_cost1"]), note=NOTES[family]))
    if len(series) != N_SERIES:
        raise AssertionError(f"A51 M4 enumerates {N_SERIES} series, built {len(series)}")
    return series


def reread(cm, cm_intraday=None):
    """A51 M4: the 19 published HOLDOUT series at the measured cost `cm` (SPX index points) and, for fvg and oflow, also at
    `cm_intraday`. Columns COLS, rows sorted by family then trial; floats are written with float_format "%.6f" by the caller."""
    return score_trials(load_series(), cm, cm_intraday)


def self_check():
    """reread(1.0, 1.0) must reproduce every published n, net, p and DSR; raises AssertionError naming the rows that do not."""
    df = reread(BASE_COST, BASE_COST)
    bad = df.loc[~df["reproduces_published"], ["family", "trial", "note"]]
    if len(bad):
        raise AssertionError("published HOLDOUT rows not reproduced at 1.0 pt:\n" + bad.to_string(index=False))
    return df
