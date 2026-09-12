"""Hypothesis families. Each returns (signal, risk_pts, direction, note).
Ordered hardest-first: the families whose MECHANISM implies an asymmetric
payoff are tested before the comfortable high-win-rate reversion ideas.
"""
import numpy as np, pandas as pd


def prep(d):
    d = d.copy()
    rng_ = (d.high - d.low)
    d["atr30"] = rng_.groupby(d.date).transform(lambda s: s.rolling(30, min_periods=10).mean())
    d["atr30"] = d.atr30.fillna(rng_.mean())
    d["ext"] = (d.close - d.vwap) / d.vwap_sd.replace(0, np.nan)
    d["prev_close"] = d.close.shift(1)
    d["gap"] = d.sess_open / d.p_dc - 1
    d["day_trend"] = np.sign(d.p_dc - d.p_do)
    return d


def families(d):
    F = {}
    b = d.bar.values
    mid = (b >= 30) & (b <= 340)

    # H1 — opening-range break. Mechanism: the first 30 minutes set the day's
    # auction boundary; a decisive break signals imbalance that tends to extend.
    # Asymmetric by construction: stop inside the range, target a measured move.
    orb_up = (b >= 30) & (b <= 180) & (d.close > d.or_hi) & (d.close.shift(1) <= d.or_hi)
    orb_dn = (b >= 30) & (b <= 180) & (d.close < d.or_lo) & (d.close.shift(1) >= d.or_lo)
    F["H1_ORB_long"] = (orb_up.values, (0.5 * d.or_rng).values, 1)
    F["H1_ORB_short"] = (orb_dn.values, (0.5 * d.or_rng).values, -1)
    F["H1_ORB_long_vwap"] = ((orb_up & (d.close > d.vwap)).values, (0.5 * d.or_rng).values, 1)
    F["H1_ORB_short_vwap"] = ((orb_dn & (d.close < d.vwap)).values, (0.5 * d.or_rng).values, -1)

    # H2 — liquidity sweep + reclaim of the PRIOR DAY level. Mechanism: resting
    # stops below yesterday's low get run, the auction rejects, trapped sellers
    # fuel the reversal. Stop goes just past the sweep extreme, so risk is
    # structurally small while the target is a full measured move.
    swept_lo = (d.run_lo < d.p_dl) & (d.close > d.p_dl)
    swept_hi = (d.run_hi > d.p_dh) & (d.close < d.p_dh)
    first_reclaim_lo = swept_lo & ~swept_lo.groupby(d.date).shift(1).fillna(False)
    first_reclaim_hi = swept_hi & ~swept_hi.groupby(d.date).shift(1).fillna(False)
    risk_lo = (d.close - d.run_lo).clip(lower=0.25)
    risk_hi = (d.run_hi - d.close).clip(lower=0.25)
    F["H2_sweep_pdl_long"] = ((first_reclaim_lo & mid).values, risk_lo.values, 1)
    F["H2_sweep_pdh_short"] = ((first_reclaim_hi & mid).values, risk_hi.values, -1)
    F["H2_sweep_pdl_long_vw"] = ((first_reclaim_lo & mid & (d.close > d.vwap)).values,
                                 risk_lo.values, 1)

    # H3 — session-VWAP band reversion. Mechanism: VWAP is the day's fair value
    # for benchmarked flow; 2-sigma excursions on no news mean-revert to it.
    # Expected to be HIGH win rate but structurally LOW payoff.
    F["H3_vwap_lo"] = ((mid & (d.ext < -2.0) & (d.ext.shift(1) >= -2.0)).values,
                       (1.0 * d.atr30 * 3).values, 1)
    F["H3_vwap_hi"] = ((mid & (d.ext > 2.0) & (d.ext.shift(1) <= 2.0)).values,
                       (1.0 * d.atr30 * 3).values, -1)
    F["H3_vwap_lo_trend"] = ((mid & (d.ext < -2.0) & (d.ext.shift(1) >= -2.0)
                              & (d.day_trend > 0)).values, (1.0 * d.atr30 * 3).values, 1)

    # H4 — first-hour range fade into the afternoon. Mechanism: on non-trend
    # days the opening range brackets the session; touches of its edge after
    # 12:00 ET are absorbed.
    late = (b >= 150) & (b <= 330)
    F["H4_fade_or_hi"] = ((late & (d.high >= d.or_hi) & (d.close < d.or_hi)).values,
                          (0.5 * d.or_rng).values, -1)
    F["H4_fade_or_lo"] = ((late & (d.low <= d.or_lo) & (d.close > d.or_lo)).values,
                          (0.5 * d.or_rng).values, 1)

    # H5 — afternoon momentum continuation. Mechanism: index rebalancing and
    # close-oriented flow extend the prevailing session direction after 14:00.
    pm = (b >= 270) & (b <= 360)
    F["H5_pm_cont_long"] = ((pm & (d.close > d.vwap) & (d.close >= d.run_hi)).values,
                            (1.0 * d.atr30 * 3).values, 1)
    F["H5_pm_cont_short"] = ((pm & (d.close < d.vwap) & (d.close <= d.run_lo)).values,
                             (1.0 * d.atr30 * 3).values, -1)
    return F
