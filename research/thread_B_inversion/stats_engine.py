"""Hypothesis engine: test many structural effects at once, then discount for having
tested many.

Three guards, all of which most retail research skips:
  1. train/test split  — screen on 2013-2016, confirm on 2017-2018
  2. block bootstrap   — p-values that respect intraday autocorrelation (day-level blocks)
  3. Benjamini-Hochberg FDR — the correction for having asked N questions

A result is only reported as REAL if it survives all three AND clears the cost wall.
"""
import numpy as np
import pandas as pd

RNG = np.random.default_rng(11)
TRAIN_END = pd.Timestamp("2017-01-01")


def block_bootstrap_p(vals, days, n_boot=2000):
    """Two-sided p-value for mean != 0, resampling whole days to preserve autocorrelation."""
    vals = np.asarray(vals, float)
    obs = vals.mean()
    codes, uniq = pd.factorize(days)
    groups = [vals[codes == i] for i in range(len(uniq))]
    if len(groups) < 20:
        return 1.0
    centered = [g - obs for g in groups]      # null: mean zero
    n = len(groups)
    means = np.empty(n_boot)
    for b in range(n_boot):
        pick = RNG.integers(0, n, n)
        means[b] = np.concatenate([centered[i] for i in pick]).mean()
    return float((np.abs(means) >= abs(obs)).mean())


def bh_fdr(pvals, alpha=0.10):
    """Benjamini-Hochberg. Returns boolean array of which pass at FDR=alpha."""
    p = np.asarray(pvals, float)
    order = np.argsort(p)
    m = len(p)
    passed = np.zeros(m, bool)
    thresh = alpha * (np.arange(1, m + 1)) / m
    below = p[order] <= thresh
    if below.any():
        k = np.max(np.where(below)[0])
        passed[order[:k + 1]] = True
    return passed


def evaluate(name, mask, fwd_ret, days, ts, cost_pts, direction=1):
    """Score one hypothesis. fwd_ret in points, signed by `direction`."""
    sel = mask.to_numpy() if hasattr(mask, "to_numpy") else mask
    r = (fwd_ret * direction)[sel]
    d = days[sel]
    t_ = ts[sel]
    tr, te = t_ < TRAIN_END, t_ >= TRAIN_END
    if sel.sum() < 200 or tr.sum() < 100 or te.sum() < 60:
        return None

    def blk(x, dd):
        if len(x) < 30 or x.std() == 0:
            return dict(n=len(x), mean=np.nan, t=np.nan)
        return dict(n=len(x), mean=x.mean(), t=x.mean() / (x.std() / np.sqrt(len(x))))

    a, b = blk(r[tr], d[tr]), blk(r[te], d[te])
    return dict(name=name, n=int(sel.sum()),
                tr_n=a["n"], tr_mean=a["mean"], tr_t=a["t"],
                te_n=b["n"], te_mean=b["mean"], te_t=b["t"],
                gross_pts=r.mean(), net_pts=r.mean() - cost_pts,
                _te_vals=r[te], _te_days=d[te])
