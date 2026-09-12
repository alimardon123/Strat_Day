# ASSESSMENT — iteration 18: the return target, and consolidating to two things

Three questions answered: yes you run them simultaneously, here is what 60-100%
a year actually costs, and here is how to collapse eight sleeves into two
tradeable buckets without losing the diversification.

---

## 1. Yes — all eight run at once

Your understanding is correct. Each sleeve is scaled to the same volatility and
all are held simultaneously. On any given day some are positioned and some are
flat. That simultaneity IS the system — it is where the Sharpe comes from, not an
implementation detail.

## 2. The return target, priced honestly

Return scales linearly with leverage. So does volatility. So does drawdown.
There is no version of this where returns rise and risk does not.

Base system: Sharpe 1.12, volatility 5.1%, CAGR 5.68%, max drawdown −6.10%.

| Annual target | Leverage | Volatility | Historical maxDD | Worst single day |
|---|---|---|---|---|
| 10% | 1.8× | 8.9% | −10.8% | −5.2% |
| 20% | 3.5× | 17.9% | −21.5% | −10.4% |
| 40% | 7.0× | 35.7% | −43.0% | −20.7% |
| **60%** | **10.6×** | **53.6%** | **−64.5%** | **−31.1%** |
| **100%** | **17.6×** | **89.3%** | **−107.5%** | **−51.8%** |

A −107% historical drawdown is not a typo — it means the leverage required for
100%/yr would have wiped the account out during the worst historical stretch.

**Block-bootstrap simulation** (3,000 paths, 20-day blocks, so drawdown
clustering is preserved):

| Target | Leverage | Median maxDD | 5% worst case | P(drawdown > 50%) | P(ruin) |
|---|---|---|---|---|---|
| 20% | 3.5× | −25.2% | −37.7% | 0.3% | 0.0% |
| 40% | 7.0× | −45.9% | −63.4% | 33.8% | 0.0% |
| **60%** | 10.6× | **−62.4%** | −80.4% | **91.0%** | 0.1% |
| **100%** | 17.6× | **−84.7%** | −96.4% | **100.0%** | **8.7%** |

At a 60% target you have a **91% chance of losing more than half your capital**
at some point. At 100%, that is a certainty, with a roughly 1-in-11 chance of
total ruin.

**And the asymmetry that matters most.** Sharpe 1.12 has a 95% confidence
interval of **[0.38, 1.85]** over 11.6 years. If the true Sharpe is the low end,
here is what the same leverage delivers:

| Target at Sharpe 1.12 | Actual return if true Sharpe is 0.4 |
|---|---|
| 20% | 7.2% |
| 60% | 21.5% |
| 100% | 35.9% |

**The risk is unchanged; only the return shrinks.** You would take a 91%
probability of a 50% drawdown to earn 21%. This is the specific reason leverage
decisions should be made against the bottom of the confidence interval, not the
point estimate.

**60–100% a year is not a strategy problem. It is a leverage decision with a
known and very bad risk profile.** My recommendation is 2–3.5× — roughly 12–20%
a year with a 20–25% worst drawdown. That is a genuinely good outcome and it is
survivable.

## 3. Consolidating to fewer strategies — what it costs

Best combination of each size, selected on train, scored on test:

| Sleeves | TRAIN | TEST | FULL | maxDD | Composition |
|---|---|---|---|---|---|
| 1 | 0.87 | 0.62 | 0.75 | −15.5% | Intraday |
| 2 | 1.02 | 0.99 | 1.01 | −8.3% | DipScore + Intraday |
| **3** | **1.13** | **1.20** | **1.17** | −7.4% | **DipScore + Intraday + Vol term structure** |
| 6 | 1.10 | 1.22 | 1.16 | −7.6% | |
| 8 | 0.88 | 1.35 | 1.12 | −6.1% | all |

**Three sleeves get you essentially the whole thing.** One does not — a single
strategy drops to Sharpe 0.62 out-of-sample with a 15.5% drawdown.

Caveat: "best of 56 triples chosen on train" is itself a selection, so the FULL
column is optimistic. The TEST column is clean because the test period was not
used for selection.

## 4. The better answer — two execution buckets

Rather than throwing away five sleeves, group all eight by **how they trade**:

**BUCKET A — fast (futures, near-daily decisions)**
DipScore, intraday gap-up, volatility term structure.
TRAIN 1.13 · TEST 1.20 · FULL **1.17** · maxDD −7.4%

**BUCKET B — slow (monthly rebalance, ETFs and stocks)**
Time-series momentum, cross-sectional momentum, volatility-managed equity,
short-term reversal, betting-against-beta.
TRAIN 0.51 · TEST 1.06 · FULL 0.79 · maxDD −9.0%

**A + B at 50/50: TRAIN 0.99 · TEST 1.40 · FULL 1.20 · maxDD −5.26%**

That is the best result of the entire programme — better than equal-weighting all
eight (1.12 / 1.35 / −6.10%), because 50/50 gives the faster bucket more weight
than its 3-of-8 share. Correlation between buckets is +0.316.

Honest flag: the fast bucket contains the two most recently added sleeves, which
are also the two best performers, so upweighting it is partly a
performance-driven choice rather than a purely structural one. Treat 1.20 as
mildly optimistic.

**Practically: Bucket A is your day-trading book — futures only, roughly 140
decision-days a year. Bucket B is a monthly rebalance you can do in twenty
minutes.** Two things to run, eight sleeves of diversification.

## 5. On 0DTE options

I have no options data, so this is reasoning rather than a backtest.

The intraday sleeve's edge is roughly **2 bp per day on the index**. Expressed
through MES/ES futures, friction is ~0.7 bp — the edge survives, barely, which is
what the backtest shows.

Through 0DTE options it does not. An at-the-money 0DTE SPX option carries a
bid-ask of roughly 1.5–3% of premium round-trip. Worse, holding from 13:00 to
the close means several hours of theta decay on a position whose entire thesis is
a 2 bp directional drift. The decay is an order of magnitude larger than the
edge, and gamma makes the payoff path-dependent in a way a linear edge cannot
compensate for.

**0DTE is the wrong instrument for this specific edge.** It is a leverage tool
for high-conviction directional views, and this sleeve is a low-conviction,
high-frequency drift. Futures express it correctly and cheaply. If you want
leverage, get it from futures notional, not from option convexity.

## 6. Where things stand

**Recommended: two buckets, 50/50, levered 2–3.5× with futures.**
Sharpe 1.20 full-sample / 1.40 out-of-sample, maxDD −5.26% unlevered.
At 3.5× that is roughly **20% a year with a −25% expected worst drawdown.**

Programme arc: 0.46 → 0.68 → 0.77 → 0.89 → 1.00 → 1.12 → **1.20**.
