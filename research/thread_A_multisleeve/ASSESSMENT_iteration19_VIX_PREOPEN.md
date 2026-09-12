# ASSESSMENT — iteration 19: real VIX data, and the pre-open question

You were right to push on the data. I searched again and found a much better
source than the VXX/VXZ ETNs I was using.

## The dataset

**CBOE VIX daily OHLC, 2 January 1990 to 4 September 2026.** 9,266 sessions,
current to two days ago. That is 36 years against the 8 years of VXX history,
and it extends past the November 2017 cutoff that has limited every other part
of this study.

Source: the `datasets/finance-vix` repository on GitHub, which mirrors CBOE's
official series. For live use, CBOE publishes it directly and free at
cboe.com/tradable_products/vix — no vendor needed.

## Your question: does pre-open VIX tell you about the day?

**Yes, decisively — but for one thing only.** Correlations against the same
session's open-to-close move, using only information available before the open:

| Pre-open signal | vs **size** of the day | vs **direction** of the day |
|---|---|---|
| Prior-day VIX close | **+0.574** | +0.060 |
| Overnight VIX change | +0.025 | −0.034 |
| 5-day VIX change | +0.209 | +0.042 |

**VIX predicts how big the day will be, with a correlation of 0.574. It tells
you essentially nothing about which way it goes.** That is one of the strongest
and most reliable relationships in this entire study — far stronger than any
trading signal I have found — and it is not a directional edge. It is a
*planning* tool.

## The pre-open table — use this every morning

| Prior VIX | Regime | Expected \|open→close\| | Typical range (20th–80th pct) |
|---|---|---|---|
| 9–13 | very calm | **0.35%** | 0.10% – 0.55% |
| 13–15 | calm | 0.37% | 0.11% – 0.58% |
| 15–18 | normal | 0.49% | 0.14% – 0.81% |
| 18–23 | elevated | 0.66% | 0.20% – 1.03% |
| 23–83 | stressed | **1.26%** | 0.32% – 1.98% |

A stressed-VIX day moves **3.6× as much** as a very-calm one. Practically:

- **Set targets and stops off this table, not off a fixed point value.** A 0.5%
  target is routine at VIX 25 and near-impossible at VIX 11.
- **Size inversely to it.** Same dollar risk means a smaller position when VIX
  is high. This is what the volatility-managed sleeve already does mechanically.
- **Know when not to bother.** At VIX under 15 the average day moves 0.36%.
  A 2 bp intraday edge is a rounding error inside that, and after costs there is
  usually nothing to trade.

## Does VIX filtering improve the intraday sleeve?

Tested with an **expanding-window median** so there is no lookahead:

| Version | trades/yr | hit rate | TRAIN Sharpe | TEST Sharpe |
|---|---|---|---|---|
| Gap-up only (current) | 138 | 54.4% | 1.02 | **0.32** |
| Gap-up + VIX above median | 38 (test era) | **56.9%** | 1.14 | **0.32** |
| Gap-up + VIX below median | — | 51.9% | −0.13 | −0.29 |

Two clear results. **The edge lives entirely in higher-VIX days** — the low-VIX
half is negative in both train and test, which confirms the mechanism: a 2 bp
edge only clears a 0.7 bp cost when the day is big enough to contain it.

But the filter **raises the hit rate (54.4% → 56.9%) without raising Sharpe**,
and it cuts trading from 138 to 38 days a year in the recent low-volatility era.
Portfolio effect: FULL 1.20 → 1.23, TEST 1.33 → 1.24. A wash.

**Recommendation: keep the unfiltered sleeve for frequency, and use VIX for
sizing rather than filtering.** Trade the gap-up setup on all gap-up days, but
size it up when VIX is above its running median and down when below. That
captures the same relationship without throwing away two thirds of your trades.

## The honest limit

This is the fifth conditioning idea tested since iteration 9, and like the other
four it did not raise Sharpe. What it *did* do — and this is genuinely useful —
is give you a calibrated expectation of the day ahead. That is worth having even
though it is not alpha.

## System status

Unchanged: two buckets, 50/50. Sharpe 1.20 full-sample, 1.33 out-of-sample,
max drawdown −5.26% unlevered.

The VIX series now runs to September 2026, so extending the rest of the study
past 2017 is more tractable than it was — that remains the highest-value next
step, because the confidence interval on Sharpe, not the strategy, is still the
binding constraint on every decision.
