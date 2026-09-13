"""PBO — probability of backtest overfitting of the D1 selection procedure (COUPLED — one file).

D1 (ACCEPTANCE.md "Decision rule for D1") ranks the 12 rankable momentum configurations on
2013-01-01..2020-05-13 by calendar-day Sharpe and promotes the single top-ranked one to the
holdout. D6 (SCORECARD.md, out/trials.csv) reports DSR/PSR/bootstrap p per trial but never asks
how much of the D1 SELECTION step itself is combinatorial luck. This module answers that with
combinatorially symmetric cross-validation (CSCV; Bailey, Borwein, López de Prado & Zhu 2015,
"The Probability of Backtest Overfitting"): split the T selection-window days into S contiguous
blocks; for every way of using half the blocks as the training set and the complementary half as
the test set, find the training-Sharpe winner and see where it ranks out of sample. PBO = the
fraction of splits in which the in-sample winner is a below-median performer out of sample.

Inputs (read-only — this module runs no signal code, it only reads D1's own outputs):
  out/reconcile_candidates.csv        — which of the 17 D1 rows are `rankable`, on which window
  out/reconcile_trades_selection.csv  — every configuration's per-trade rows on the selection
                                         window (columns include candidate, date, pts, ret_pct,
                                         entry_px)

Series: the day x configuration matrix is the NET calendar-day P&L in SPX points at 1.0 pt
round-trip cost per trade (pts - COST_PTS, summed per day, zero on days with no trade) over the
NYSE trading days of the selection window (sessions.trading_days_from_vix(), filtered to the
window exactly as reconcile.py does) — the same construction as stats.calendar_day_sharpe's
zero-filled series, applied to points instead of the ranking metric's percent so a single round-
trip cost is exact (ACCEPTANCE: D1/D2 are scored in points; sharpe_calday is in percent so a
price level that doubled does not weight late trades — irrelevant here since PBO only needs a
CROSS-SECTIONAL comparison of Sharpe ratios within one fixed window).

Method per S: performance metric = calendar-day Sharpe (mean/std x sqrt(252), ddof=1, zeros
included — pipeline.stats.sharpe's own formula) computed on the training rows and on the test
rows for every configuration, for every C(S, S/2) combination; n* = the training argmax; its
out-of-sample relative rank omega = rank_test(n*) / (N+1) (ties -> average rank, rank 1 = worst,
rank N = best); logit lambda = log(omega / (1-omega)); PBO = fraction of combinations with
lambda < 0. Also reported: mean/median lambda, the fraction of combinations where the IS-best's
test Sharpe is <= 0, the degradation regression of test Sharpe on training Sharpe for the IS-best
across combinations (slope, intercept), the stochastic-dominance summary (mean test Sharpe of the
IS-best vs of all configurations) and the most frequently chosen IS-best configuration.

S = 16 is the paper's own worked example (headline row); S = 8 is a robustness row. A null check
(seed 11) shuffles each configuration's day series independently — destroying any temporal
structure (day-to-day autocorrelation, clustering by regime) while EXACTLY preserving each
configuration's own full-window mean and variance (a permutation, not a resample) — and re-runs
CSCV on the shuffled matrix. This is the estimator-calibration check the module is asked to
report; the caller should not assume it lands at exactly 0.5 without checking: with T this large
(1854 days, ~927-day train/test halves) a genuine full-sample quality difference between two
configurations survives ANY within-column permutation (the block means it produces are still
close to their own configuration's true mean, since both halves are large), so a shuffled PBO
far from 0.5 here says the 12 configurations differ in unconditional quality, not that the
estimator is miscalibrated — see the printed table and the accompanying report.

Adaptations from the paper (both logged here rather than silently rounded, both immaterial):
  1. the paper assumes T divisible by S. T = 1854 is divisible by neither 16 nor 8, so blocks are
     built with numpy's own equal-as-possible contiguous split (the first T % S blocks get one
     extra day; still contiguous, still equal-size to within one day).
  2. the paper assumes the performance metric is always defined. A handful of splits give a
     sparse VIX-and-move-gated configuration exactly zero trades on one side (train or test),
     making its calendar-day Sharpe an undefined 0/0; the paper has no rule for this. Those
     splits are dropped from every statistic (logged per row in `spec` as combos_used=used/total)
     while `n_combinations` still reports the full C(S, S/2).

    python -m pipeline.pbo   → out/pbo.csv
"""
import itertools

import numpy as np
import pandas as pd

from pipeline import sessions

SEL_START, SEL_END = "2013-01-01", "2020-05-13"   # D1's selection window (reconcile.py SEL_START/SEL_END)
COST_PTS = 1.0                                     # ACCEPTANCE's round-trip cost, SPX points (reconcile.py COST_PTS)
SEED = 11                                          # ACCEPTANCE's fixed seed convention (stats.SEED)
S_VALUES = (16, 8)                                 # headline (paper's worked example) + robustness row
PERIODS_PER_YEAR = 252
SPEC = ("blocks=contiguous_equal_numpy_array_split;metric=calendar_day_sharpe(net_pts,cost=1.0pt/trade,ddof=1);"
        "isbest_tie_break=argmax_first_by_sorted_name;test_rank_ties=average;"
        "null=per_config_independent_shuffle_seed11")


def load_matrix():
    """Day x rankable-configuration matrix of NET calendar-day P&L in SPX points, zero-filled
    over every NYSE trading day of the D1 selection window."""
    cand = pd.read_csv("out/reconcile_candidates.csv")
    win = f"{SEL_START}..{SEL_END}"
    names = sorted(cand.loc[(cand["window"] == win) & cand["rankable"], "candidate"])
    t = pd.read_csv("out/reconcile_trades_selection.csv", parse_dates=["date"])
    t = t[t["candidate"].isin(names) & (t["date"] >= SEL_START) & (t["date"] <= SEL_END)].copy()
    t["net"] = t["pts"] - COST_PTS
    td = sessions.trading_days_from_vix()
    all_dates = pd.DatetimeIndex(sorted(d for d in td if pd.Timestamp(SEL_START) <= d <= pd.Timestamp(SEL_END)))
    piv = t.pivot_table(index="date", columns="candidate", values="net", aggfunc="sum", fill_value=0.0)
    return piv.reindex(index=all_dates, columns=names, fill_value=0.0)


def _blocks(T, S):
    """S contiguous blocks, as equal as possible (adaptation logged in the module docstring)."""
    return np.array_split(np.arange(T), S)


def _block_moments(M, splits):
    """Per block: sum, sum-of-squares (per config) and day count -> (S, N) / (S, N) / (S,)."""
    S, N = len(splits), M.shape[1]
    bsum, bsq, blen = np.zeros((S, N)), np.zeros((S, N)), np.zeros(S)
    for s, idx in enumerate(splits):
        bsum[s] = M[idx].sum(axis=0)
        bsq[s] = (M[idx] ** 2).sum(axis=0)
        blen[s] = len(idx)
    return bsum, bsq, blen


def _sharpe_from_moments(sum_, sq_, n_):
    """stats.sharpe (mean/std x sqrt(252), ddof=1, NaN if std==0 or n<=1), vectorised from
    block-aggregated moments. sum_/sq_: (C, N); n_: (C,) -> (C, N)."""
    n = n_[:, None]
    mean = sum_ / n
    var = np.clip((sq_ - sum_ ** 2 / n) / np.clip(n - 1, 1, None), 0.0, None)   # clip: float round-off below 0
    std = np.sqrt(var)
    ok = (std > 0) & (n > 1)
    sh = np.full(sum_.shape, np.nan)
    sh[ok] = mean[ok] / std[ok] * np.sqrt(PERIODS_PER_YEAR)
    return sh


def _shuffle_columns(M, seed):
    """Null check: each configuration's day series permuted independently (own marginal kept,
    cross-sectional/temporal structure destroyed)."""
    rng = np.random.default_rng(seed)
    out = np.empty_like(M)
    for j in range(M.shape[1]):
        out[:, j] = M[rng.permutation(M.shape[0]), j]
    return out


def cscv(M, S, names, seed=None):
    """One CSCV pass at block count S. `M`: DataFrame (T days x N configs). `seed`: None for the
    actual matrix, an int to run the independent-per-column-shuffle null first."""
    T, N = M.shape
    Mv = M.to_numpy(dtype=float)
    if seed is not None:
        Mv = _shuffle_columns(Mv, seed)
    splits = _blocks(T, S)
    bsum, bsq, blen = _block_moments(Mv, splits)

    half = S // 2
    combos = list(itertools.combinations(range(S), half))
    C = len(combos)
    train_mask = np.zeros((C, S))
    for i, combo in enumerate(combos):
        train_mask[i, combo] = 1.0
    test_mask = 1.0 - train_mask   # S even, |train| == |test| == S/2 -> exact complement

    train_sh = _sharpe_from_moments(train_mask @ bsum, train_mask @ bsq, train_mask @ blen)
    test_sh = _sharpe_from_moments(test_mask @ bsum, test_mask @ bsq, test_mask @ blen)

    # A rare, low-frequency configuration (a VIX-and-move gate that fires in only a few blocks)
    # can draw zero trades on one side of a split -> zero variance -> an undefined (0/0) calendar-
    # day Sharpe. The paper has no rule for this (it is written for metrics that are always
    # defined). Adaptation, logged rather than papered over: drop that split from every statistic
    # below (it has no defined rank), but keep n_combinations = C(S, S/2) as reported and note the
    # dropped count in `spec`.
    ok = ~(np.isnan(train_sh).any(axis=1) | np.isnan(test_sh).any(axis=1))
    n_dropped = int((~ok).sum())
    train_sh, test_sh = train_sh[ok], test_sh[ok]
    Cu = int(ok.sum())

    n_star = np.argmax(train_sh, axis=1)                                         # ties -> first (sorted name order)
    ranks = pd.DataFrame(test_sh).rank(axis=1, method="average").to_numpy()      # 1 = worst .. N = best
    rows = np.arange(Cu)
    r_star = ranks[rows, n_star]
    omega = r_star / (N + 1)
    logit = np.log(omega / (1 - omega))
    test_star, train_star = test_sh[rows, n_star], train_sh[rows, n_star]

    slope, intercept = np.polyfit(train_star, test_star, 1)
    counts = np.bincount(n_star, minlength=N)
    top = int(np.argmax(counts))
    spec = f"{SPEC};combos_used={Cu}/{C}(dropped {n_dropped} degenerate: zero-variance split)"

    return dict(n_configs=N, n_days=T, n_blocks=S, n_combinations=C,
                pbo=float(np.mean(logit < 0)),
                mean_logit=float(np.mean(logit)), median_logit=float(np.median(logit)),
                frac_isbest_test_sharpe_le_0=float(np.mean(test_star <= 0)),
                degradation_slope=float(slope), degradation_intercept=float(intercept),
                mean_test_sharpe_isbest=float(np.mean(test_star)),
                mean_test_sharpe_all=float(np.mean(test_sh)),
                isbest_most_frequent=f"{names[top]} (n={int(counts[top])}, freq={counts[top] / Cu:.4f})",
                seed=float(seed) if seed is not None else np.nan, spec=spec)


def main():
    M = load_matrix()
    names = list(M.columns)
    rows = []
    for S in S_VALUES:
        for variant, seed in (("actual", None), ("shuffled_null", SEED)):
            r = cscv(M, S, names, seed=seed)
            r["variant"] = variant
            rows.append(r)
    cols = ["variant", "n_configs", "n_days", "n_blocks", "n_combinations", "pbo", "mean_logit", "median_logit",
            "frac_isbest_test_sharpe_le_0", "degradation_slope", "degradation_intercept",
            "mean_test_sharpe_isbest", "mean_test_sharpe_all", "isbest_most_frequent", "seed", "spec"]
    out = pd.DataFrame(rows)[cols]
    out.to_csv("out/pbo.csv", index=False, float_format="%.6f")
    print(out.to_string(index=False))


if __name__ == "__main__":
    main()
