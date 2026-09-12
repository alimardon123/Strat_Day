# ASSESSMENT — iteration 12: I was wrong twice, and the target metric turns out to be unmeasurable

This iteration set out to fix the payoff leg with a positively-skewed sleeve.
It corrected two claims I made in iteration 11 and found something more
important than either.

---

## Correction 1 — the sleeves are not uniformly negatively skewed

In iteration 11 I wrote that "every strategy in this portfolio is short some form
of tail risk," and used that to explain why the payoff ratio wouldn't move.
Measured, monthly:

| Sleeve | skew | Sharpe |
|---|---|---|
| S3 XSMOM | **+0.58** | 0.39 |
| S1 MEANREV | **+0.35** | 0.74 |
| S8 BAB | +0.07 | 0.81 |
| S5 VOLMANAGED | −0.25 | 0.63 |
| S2 TSMOM | −0.31 | 0.54 |
| S6 STREV | −0.38 | 0.07 |

Mixed, not uniform. And the **portfolio's quarterly skew is −0.07** — essentially
zero. My explanation was a story fitted to a number, and the number wasn't there.

## Correction 2 — the gap I was fixing was noise

Observed quarterly payoff 1:1.44 against a Gaussian prediction of 1:1.50 at
Sharpe 0.89. I treated that 0.06 as a structural shortfall requiring a new sleeve.

Bootstrapped on the actual 47 quarters:

> payoff ratio: point estimate **1:1.60**, 95% CI **[1:0.84, 1:3.15]**

The CI is nearly two and a half units wide. The "shortfall" I diagnosed sits in
the middle of it. There was nothing to explain.

## The sleeve I built anyway, and what it did

**S10 DONCHIAN** — enter long on a 50-day high, short on a 50-day low, exit on a
20-day counter-extreme, no profit target at all. The classic breakout profile:
many small losses, rare large gains.

**It failed on its own terms.** Sharpe 0.11 (train 0.12, test 0.09), and monthly
skew of **+0.00** — it did not even deliver the positive skew it was built for.
2006–2017 was a documented graveyard for trend-following.

And yet:

| Portfolio | TRAIN | TEST | FULL | quarterly win | quarterly payoff |
|---|---|---|---|---|---|
| 6 sleeves | 0.61 | **1.16** | **0.89** | **72.3%** | 1:1.44 |
| 7 sleeves (+Donchian) | 0.61 | 1.11 | 0.86 | 68.1% | **1:1.83** |

Adding a Sharpe-0.11 sleeve moved the payoff ratio from 1:1.44 to 1:1.83 and
**nominally meets your full target** — 68.1% wins at 1:1.83. Not through skew,
which it doesn't have, but because it is uncorrelated-to-negatively-correlated
with S6 (−0.23) and S8 (−0.08), so its occasional large months land in the
portfolio's up-tail.

I could stop here and tell you the target is met. That would be the wrong answer.

## The real finding: the target metric cannot be measured

| System (47 quarters) | win rate | P(win ≥ 60%) | payoff | P(payoff ≥ 1.5) | **P(both)** |
|---|---|---|---|---|---|
| 6 sleeves | 72.4% [59.6, 85.1] | **0.96** | 1:1.60 [0.84, 3.15] | 0.46 | **0.45** |
| 7 sleeves | 68.2% [55.3, 80.9] | 0.87 | 1:1.91 [1.17, 3.13] | 0.79 | **0.68** |

**The win-rate leg of your target is established.** 96% probability the 6-sleeve
system genuinely wins more than 60% of quarters. That is a real result and you
can rely on it.

**The payoff leg is a coin flip and will stay one.** How much data would settle
it?

| To narrow the payoff CI to | Quarters needed | Years |
|---|---|---|
| ±0.50 | 249 | **62** |
| ±0.25 | 997 | **249** |
| ±0.15 | 2,770 | **692** |

Verifying a payoff-ratio target to any useful precision requires more years of
market history than exist. The ratio is a quotient of two conditional means, each
estimated from ~15–35 observations, so its error compounds. This is not a
limitation of my search — it is a property of the statistic.

## What this means for your target

Your target has two legs and they are not equally knowable:

- **Win rate**: converges reasonably fast. Met, at 96% confidence, quarterly.
- **Payoff ratio**: converges so slowly it is not a usable criterion. Anyone
  quoting you a strategy's win/payoff pair from a decade of data — including me,
  in iterations 9 and 11 — is quoting a number with an error bar they haven't shown.

**Replace the payoff leg with something that converges.** Sharpe and maximum
drawdown are estimable from a decade; the payoff ratio is not. Concretely, the
6-sleeve system's Sharpe of 0.89 has a 95% CI of [0.21, 1.57] — wide, but it
narrows in decades, not centuries.

## Where things stand

**Recommended: the 6-sleeve system**, chosen on the metrics that can actually be
measured. Sharpe 0.89 full / 1.16 out-of-sample, max drawdown −7.6% against
SPY's −56.5%, 72.3% winning quarters.

The 7-sleeve version scores better on the unmeasurable metric and worse on the
measurable ones. I would not pay 0.03 of Sharpe for a payoff ratio whose
confidence interval spans 0.84 to 3.15.

## Next

Nothing in this iteration changes the ranking from iteration 11: more data,
then more uncorrelated sleeves, never more conditioning. But it does add one
thing — **stop optimising against the payoff ratio.** Twelve iterations in, that
number has been driving decisions it is far too noisy to inform, including two of
mine.
