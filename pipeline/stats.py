"""Inference adapter (COUPLED — one standard for every number).

Wraps research/thread_B_inversion/stats_engine.py unchanged (block bootstrap, BH-FDR) and adds
Thread A's effective-independent-bets adjustment, the calendar-day Sharpe used to rank
configurations of different frequency, and the deflated Sharpe ratio (Bailey & López de Prado
2014). Differences from the threads, all deliberate (ACCEPTANCE A19, A26):
  * the bootstrap generator is re-seeded per call (stats_engine keeps ONE module-level RNG);
  * the train/test split is a parameter, not stats_engine.TRAIN_END;
  * any statistic with fewer than 20 blocks is NaN, never 1.0.
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
MIN_BLOCKS = 20
bh_fdr = _se.bh_fdr


def n_blocks(blocks):
    return len(pd.unique(np.asarray(blocks)))


def block_bootstrap_p(vals, blocks, n_boot=N_BOOT, seed=SEED):
    """Two-sided p for mean != 0 (stats_engine algorithm, fresh RNG); NaN below 20 blocks."""
    if n_blocks(blocks) < MIN_BLOCKS:
        return np.nan
    _se.RNG = np.random.default_rng(seed)
    return _se.block_bootstrap_p(np.asarray(vals, float), np.asarray(blocks), n_boot)


def one_sided_p(vals, blocks, n_boot=N_BOOT, seed=SEED):
    """Thread B convention: half the two-sided p when the mean is positive, else 1.0."""
    vals = np.asarray(vals, float)
    if len(vals) == 0:
        return np.nan
    p = block_bootstrap_p(vals, blocks, n_boot, seed)
    if np.isnan(p):
        return np.nan
    return p / 2 if vals.mean() > 0 else 1.0


def n_eff(n, rho):
    """Thread A: effective independent bets among n instruments with mean pairwise correlation rho."""
    return n / (1 + (n - 1) * rho)


def sharpe(x, periods_per_year=252):
    x = np.asarray(x, float)
    return float(x.mean() / x.std(ddof=1) * np.sqrt(periods_per_year)) if len(x) > 1 and x.std(ddof=1) > 0 else np.nan


def per_trade_sharpe(x):
    x = np.asarray(x, float)
    return float(x.mean() / x.std(ddof=1)) if len(x) > 1 and x.std(ddof=1) > 0 else np.nan


def calendar_day_sharpe(pnl, dates, all_dates):
    """Annualised Sharpe of the calendar-day P&L series with zeros on non-trade days — the
    ranking metric that makes a 34-trade/yr and a 60-trade/yr configuration comparable."""
    s = pd.Series(0.0, index=pd.DatetimeIndex(sorted(set(all_dates))))
    add = pd.Series(np.asarray(pnl, float), index=pd.DatetimeIndex(dates)).groupby(level=0).sum()
    s.loc[add.index] += add
    return sharpe(s.to_numpy(), 252)


def expected_max_sharpe(sr_trials, n=None):
    """E[max SR] under the null across N trials (Bailey & López de Prado 2014): the observed
    dispersion of the trials' per-trade Sharpe estimates times the expected maximum of N
    standard normals. `n` defaults to the number of observed trials; pass a larger N to
    deflate against a trial count wider than the observed pool (same dispersion estimate)."""
    sr_trials = np.asarray(sr_trials, float)
    sr_trials = sr_trials[~np.isnan(sr_trials)]
    n_obs = len(sr_trials)
    n = n_obs if n is None else int(n)
    if n_obs < 2 or n < 2:
        return 0.0
    g = 0.5772156649
    return float(np.std(sr_trials, ddof=1) * ((1 - g) * norm.ppf(1 - 1 / n) + g * norm.ppf(1 - 1 / (n * np.e))))


def deflated_sharpe(x, sr_trials=(), n=None):
    """DSR = P(true SR > 0 | observed per-trade SR, N trials, T trades, skew, kurtosis).
    With fewer than two trials (or n == 1) SR0 = 0 and this is the probabilistic Sharpe ratio.
    Returns (dsr, sr0, sr_hat), all per-trade."""
    x = np.asarray(x, float)
    T = len(x)
    if T < 3 or x.std(ddof=1) == 0:
        return np.nan, np.nan, np.nan
    sr = x.mean() / x.std(ddof=1)
    sr0 = 0.0 if n == 1 else expected_max_sharpe(sr_trials, n)
    g3, g4 = skew(x), kurtosis(x, fisher=False)
    denom = np.sqrt(max(1 - g3 * sr + (g4 - 1) / 4 * sr ** 2, 1e-12))
    return float(norm.cdf((sr - sr0) * np.sqrt(T - 1) / denom)), float(sr0), float(sr)


def summarise(name, r, blocks, cost, sr_trials=(), periods_per_year=252):
    """One row of the standard table (returns in the caller's unit; cost in the same unit)."""
    r = np.asarray(r, float)
    net = r - cost
    dsr, sr0, _ = deflated_sharpe(net, sr_trials)
    return dict(name=name, n=int(len(r)), win=float((r > 0).mean()) if len(r) else np.nan,
                gross=float(r.mean()) if len(r) else np.nan, net=float(net.mean()) if len(r) else np.nan,
                p_boot=one_sided_p(net, blocks), sharpe_net=sharpe(net, periods_per_year),
                sr_trade=per_trade_sharpe(net), dsr=dsr, sr0_trade=sr0)


def month_blocks(dates):
    return pd.PeriodIndex(pd.to_datetime(dates), freq="M").astype(str).to_numpy()


def day_blocks(dates):
    return pd.DatetimeIndex(pd.to_datetime(dates)).normalize().astype(str).to_numpy()
