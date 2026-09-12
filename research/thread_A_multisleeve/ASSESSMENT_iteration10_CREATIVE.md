# ASSESSMENT — iteration 10: four new ideas, four failures, one real pattern

You asked for creativity and out-of-the-box thinking. I brought four ideas that
are different in kind rather than degree. **All four failed.** One of them failed
in a way that is genuinely worth understanding, and the four failures together
form a pattern that is more useful than any of them would have been individually.

---

## Idea A — session decomposition (the most promising, and the most instructive)

Every strategy in ten iterations treated a day as one object. But a day is two
different markets: the overnight session (close → next open), where the tape is
shut and positioning happens through futures and news; and the intraday auction
(open → close). Nobody in this study had looked at the split.

**The raw numbers were spectacular:**

| Asset | total CAGR | overnight | intraday | ON Sharpe | ID Sharpe |
|---|---|---|---|---|---|
| SPY | 7.28% | 5.24% | 2.01% | 0.53 | 0.21 |
| VNQ | 6.05% | **+14.25%** | **−7.08%** | 1.08 | −0.11 |
| XOP | 1.16% | **+19.11%** | **−15.05%** | 1.00 | −0.34 |
| HYG | 2.04% | +9.88% | −7.13% | **1.44** | −0.66 |

Mean across assets: **4.78%/yr overnight versus 0.59% intraday**, Sharpe 0.44
versus 0.16. A 34-percentage-point annual gap on XOP. This looks exactly like the
kind of structural asymmetry you have been describing.

**First problem — the cost wall.** Harvesting it means trading every session
boundary. At 2 bp per side that is **9.6%/yr in costs**, against SPY's 5.24%
gross overnight return. So I built a cost-aware version instead: a monthly
rebalanced tilt toward assets with high trailing overnight Sharpe. It scored
0.38 on train — **against 0.49 for a random-rank control.** The ranking added
nothing; the sleeve was just long equity beta wearing a costume.

**Second problem, and this is the real one.** I tested the direct spread trade
(long overnight, short intraday) on the widest gaps:

| | TRAIN Sharpe | TEST Sharpe |
|---|---|---|
| HYG @1bp | **1.40** | **−1.12** |
| XOP @1bp | 0.93 | 0.13 |
| VNQ @1bp | 0.37 | −0.10 |
| SPY @1bp | −0.18 | −0.94 |

Complete collapse. And the pattern identifies the cause: the effect is enormous
in 2006–2011, absent afterwards, largest in the *least liquid* ETFs, and smallest
in SPY. That is the signature of **opening-print and NAV-dislocation artifacts
during the financial crisis**, when thinly-traded ETFs printed opens far from
fair value. It is not a risk premium. The most liquid instrument, where a real
premium would be cleanest to see, shows the smallest gap and loses money.

This was the best idea in the batch and it was a measurement artifact. Worth
knowing: a 34-point annual gap that dissolves under a liquidity cross-check is
what most "discovered loopholes" turn out to be.

## Idea B — correlation-scaled gross exposure (my own, from iteration 7's failure)

Iteration 7 found that realised strategy correlation (0.529) far exceeded
underlying asset correlation (0.198) — the portfolio silently becomes one bet
when it matters most. So: measure effective independent bets in a trailing
window and scale gross exposure by it. Cut risk when *diversification* fails
rather than when volatility rises. I have not seen this construction elsewhere
and it falls straight out of this programme's own result.

Trailing n_eff moved between 1.59 and 6.00, median 2.35 — so there was real
signal to act on.

**Result: TRAIN 0.51, TEST 0.88, against a baseline of 0.60 / 0.94.** Worse on
both. The trailing correlation estimate is too noisy at a 126-day window; it cut
exposure after correlation had already spiked, which is after the damage.

## Idea C — strategy momentum

Weight sleeves by trailing Sharpe instead of equally. Documented for factors.
**Result: TRAIN 0.48, TEST 0.84.** The worst of the four.

## The pattern, which is the actual output of this iteration

| Variant | TRAIN | TEST | TEST maxDD |
|---|---|---|---|
| **Baseline: 5 sleeves, equal weight, no conditioning** | **0.60** | **0.94** | **−6.60%** |
| + overnight tilt | 0.57 | 0.94 | −7.72% |
| + correlation-scaled exposure | 0.51 | 0.88 | −7.66% |
| + strategy-momentum weights | 0.48 | 0.84 | −9.07% |

Add iteration 9's results — sleeve selection was noise, and three weighting
schemes landed within 0.03 of each other — and that is **five independent
attempts to be clever about allocation, all of which lost to doing nothing.**

The reason is not that the ideas are bad. It is that every conditioning rule
requires estimating something from a trailing window, and at 11.6 years of data
the estimation error is larger than the effect being estimated. Equal weight
estimates nothing, so it has no estimation error to lose to. At this sample size
that is not laziness — it is the optimal response to uncertainty.

## On the loophole hypothesis

Your intuition that markets contain rules is right, and iteration 8 proved it:
momentum, mean reversion, volatility persistence and calendar flows are all real
and all measurable here. What ten iterations have shown is a different thing —
that the large, undiscovered version does not appear to be reachable from price
data with public tools, and that things which *look* like one (a 34-point
overnight gap, a monotonic volatility gradient in iteration 4, a t-statistic of
14.8 in iteration 4, a Sharpe of 1.40 in this one) have each dissolved under a
specific, boring check: a control, a lookahead audit, a liquidity cross-check, a
correlation adjustment.

I have run 410-plus configurations and roughly a dozen genuinely distinct
hypotheses. The consistent finding is not "nothing works." It is that **the
things that work are small, known, and only useful in combination** — which is
exactly what the five-sleeve portfolio is.

## Recommendation

The best system remains iteration 9's: **five sleeves, equal weight, Sharpe 0.77
full-sample, 68.1% quarterly win rate at 1:1.45, −7.5% max drawdown against
SPY's −56.5%.** Ten iterations have not improved on it, and the last five
attempts made it worse.

What would actually move it, in order of expected value:

1. **More data.** Sharpe 0.77 with a 95% CI of [0.05, 1.33] is the binding
   constraint on every decision here. Extending past 2017 and back before 2006
   narrows that interval and costs nothing but a data file.
2. **A genuinely uncorrelated sleeve** — carry, volatility risk premium, or a
   rates-specific trend. n_eff has been the only variable that moved Sharpe
   (1.78 → 2.42 → 2.89, Sharpe 0.46 → 0.68 → 0.77).
3. **Not more conditioning.** That has now failed five times for a reason that
   will not change until item 1 does.
