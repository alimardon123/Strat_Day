"""Inference adapter (COUPLED — one standard for every number).

Wraps research/thread_B_inversion/stats_engine.py unchanged (block bootstrap, BH-FDR) and adds
Thread A's effective-independent-bets adjustment and the deflated Sharpe ratio
(Bailey & López de Prado 2014). Differences from the threads, all deliberate:
  * the bootstrap generator is re-seeded per call (stats_engine keeps ONE module-level RNG, so
    its p-values depend on call order and never bit-reproduce);
  * the train/test split is a parameter, not stats_engine.TRAIN_END (hardcoded 2017-01-01).
Thread B's one-sided convention (p/2 when the mean is positive, else 1.0) is kept as-is.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import norm, skew, kurtosis

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "research" / "thread_B_inversion"))
import stats_engine as _se  # noqa: E402  (research code, imported unchanged)

SEED = 11
N_BOOT = 2000
bh_fdr = _se.bh_fdr


def block_bootstrap_p(vals, blocks, n_boot=N_BOOT, seed=SEED):
    """Two-sided p for mean != 0, resampling whole blocks (stats_engine algorithm, fresh RNG)."""
    _se.RNG = np.random.default_rng(seed)
    return _se.block_bootstrap_p(np.asarray(vals, float), np.asarray(blocks), n_boot)


def one_sided_p(vals, blocks, n_boot=N_BOOT, seed=SEED):
    """Thread B convention: half the two-sided p when the mean is positive, else 1.0."""
    vals = np.asarray(vals, float)
    if len(vals) == 0:
        return 1.0
    p = block_bootstrap_p(vals, blocks, n_boot, seed)
    return p / 2 if vals.mean() > 0 else 1.0


def n_eff(n, rho):
    """Thread A: effective independent bets among n instruments with mean pairwise correlation rho."""
    return n / (1 + (n - 1) * rho)


def sharpe(x, periods_per_year=252):
    x = np.asarray(x, float)
    return float(x.mean() / x.std(ddof=1) * np.sqrt(periods_per_year)) if len(x) > 1 and x.std(ddof=1) > 0 else np.nan


def expected_max_sharpe(sr_trials):
    """E[max SR] under the null across N trials (Bailey & López de Prado 2014, eq. for SR0),
    using the observed dispersion of the trials' Sharpe estimates."""
    sr_trials = np.asarray(sr_trials, float)
    n = len(sr_trials)
    if n < 2:
        return 0.0
    g = 0.5772156649
    return float(np.std(sr_trials, ddof=1) * ((1 - g) * norm.ppf(1 - 1 / n) + g * norm.ppf(1 - 1 / (n * np.e))))


def deflated_sharpe(x, sr_trials):
    """DSR = P(true SR > 0 | observed SR, N trials, T obs, skew, kurtosis). Per-period Sharpe.
    Returns (dsr, sr0, sr_hat)."""
    x = np.asarray(x, float)
    T = len(x)
    if T < 3 or x.std(ddof=1) == 0:
        return np.nan, np.nan, np.nan
    sr = x.mean() / x.std(ddof=1)
    sr0 = expected_max_sharpe(sr_trials) / np.sqrt(252) if len(sr_trials) > 1 else 0.0  # trials given annualised
    g3, g4 = skew(x), kurtosis(x, fisher=False)
    denom = np.sqrt(max(1 - g3 * sr + (g4 - 1) / 4 * sr ** 2, 1e-12))
    return float(norm.cdf((sr - sr0) * np.sqrt(T - 1) / denom)), float(sr0), float(sr)


def summarise(name, r, blocks, cost, sr_trials=(), periods_per_year=252):
    """One row of the standard table: n, win, gross, net, one-sided bootstrap p, Sharpe, DSR."""
    r = np.asarray(r, float)
    net = r - cost
    dsr, sr0, _ = deflated_sharpe(net, sr_trials)
    return dict(name=name, n=int(len(r)), win=float((r > 0).mean()) if len(r) else np.nan,
                gross=float(r.mean()) if len(r) else np.nan, net=float(net.mean()) if len(r) else np.nan,
                p_boot=one_sided_p(net, blocks), sharpe_net=sharpe(net, periods_per_year), dsr=dsr, sr0_annual=sr0 * np.sqrt(252) if sr0 == sr0 else np.nan)


def month_blocks(dates):
    return pd.PeriodIndex(pd.to_datetime(dates), freq="M").astype(str).to_numpy()
