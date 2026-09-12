# ASSESSMENT — iteration 17: the volatility sleeve

You were right that VIX data was reachable. The Kaggle ETF set contains VXX,
VXZ, SVXY, UVXY, VIXY, VXZ and TVIX — VXX and VXZ both from 2009. That closed
the gap iteration 14 identified.

## The sleeve

**S13 VOL TERM STRUCTURE.** VXX is the short-dated VIX futures ETN; VXZ is the
mid-dated one. When VXX outperforms VXZ over five days, the futures curve is in
backwardation and long volatility pays; otherwise it is in contango and short
volatility pays. Signal is the sign of that five-day spread, lagged one day.
Costs 5 bp per side.

Why this and not just "hold VXX in a crisis": VXX loses **60% a year** held long
and VXZ loses 29%. There is no passive long-volatility position worth having.
The entire edge is in timing the curve.

| Position | CAGR | vol | Sharpe | max DD |
|---|---|---|---|---|
| Short vol always | +70.9% | 61% | 1.19 | −72.2% |
| Long vol always | −60.0% | 61% | −1.19 | −100.0% |
| **Term-structure timed** | +11.3% | 61% | **0.48** | −66.6% |

Train 0.54 / test 0.41 — stable, which is what matters. The always-short line
looks better and is a trap; see the warning below.

## What it did to the portfolio

| Variant | TRAIN | TEST | FULL | max DD |
|---|---|---|---|---|
| 6 sleeves | 0.61 | 1.16 | 0.89 | −7.57% |
| 7 (+ intraday) | 0.80 | 1.20 | 1.00 | −6.95% |
| **8 (+ vol term structure)** | **0.88** | **1.35** | **1.12** | **−6.10%** |

Sharpe up and drawdown down at the same time. Correlation of S13 to the rest of
the portfolio is **−0.137** — the first genuinely negatively-correlated sleeve
found in seventeen iterations.

## It fixed the measured weak spot

Annualised return by regime:

| Regime | 6 sleeves | 8 sleeves |
|---|---|---|
| Uptrend | +8.85% | +7.76% |
| Downtrend | **−0.36%** | **+0.63%** |
| High volatility | **−1.87%** | **+1.93%** |

S13 standalone: uptrend +2.81%, downtrend **+7.97%**, high-vol **+6.93%**. It
earns most exactly where the rest of the portfolio struggles, which is the whole
reason it was worth building.

This is the first version of the system that is positive in all three regimes
rather than merely defensive in two.

## The warning that matters more than the result

**The VXX data ends 10 November 2017. On 5 February 2018 short-volatility
products lost most of their value in a single session** — XIV fell roughly 96%
and was liquidated. The term-structure signal would have been short volatility
going into it.

That event is not in this backtest, and it is the single most important missing
observation in the entire study.

Mitigating facts: the sleeve is volatility-targeted, so at a 10% target against
VXX's 61% volatility its notional is about one sixth of capital, and it is one of
eight equal-weighted sleeves. A one-day 33% adverse move costs roughly 5% of the
portfolio, not everything. But volatility targeting protects against normal days,
not gap days, and short-volatility positions are the canonical example of a
strategy whose backtest Sharpe overstates its risk.

Concretely: cap this sleeve's weight, never scale it on the strength of its
Sharpe, and treat its 0.48 as an upper bound rather than an estimate.

## Where the system stands

Eight sleeves, equal weight, no conditioning. **Sharpe 1.12 full-sample, 1.35
out-of-sample, max drawdown −6.10%, positive in all three regimes.** Levered with
futures to SPY's volatility that is roughly 17%/yr against SPY's 7.4%, with a
−22% drawdown against −56%.

Progression of the whole programme: 0.46 (SPY) → 0.68 (4 sleeves) → 0.77 (5) →
0.89 (6, +BAB) → 1.00 (7, +intraday) → **1.12 (8, +vol)**. Every single step came
from adding an uncorrelated return driver. Not one came from a better rule, a
filter, or a weighting scheme.

## Next

1. **Extend past 2017.** The confidence interval on Sharpe 1.12 is roughly
   [0.4, 1.8], and February 2018 is the specific missing observation.
2. **More uncorrelated drivers** — carry, or a rates-specific trend. The one
   lever that has ever worked.
3. Still not more conditioning. Twelve failures.
