# ASSESSMENT — iteration 11: a new sleeve that actually worked

Iteration 10 ended with a clear instruction from the evidence: stop adding
conditioning (five failures), and add uncorrelated sleeves (the only variable
that has ever moved Sharpe). This iteration did that, from a data source the
portfolio had never touched — the 626-name single-stock panel, 2000–2026.

---

## The two candidates

Both market-neutral by construction, so neither can inherit the long-equity
factor that iteration 7 showed contaminates everything else.

**S8 BAB — betting against beta.** Long the lowest-beta 30% of stocks, short the
highest-beta 30%, with the legs beta-balanced so the sleeve carries no market
exposure. Monthly rebalance to keep turnover costs sane at 5 bp. Mechanism:
leverage-constrained investors bid up high-beta names, so low-beta names are
systematically cheap. Documented since Black (1972).

**S9 STOCKREV — stock-level short-term reversal.** Long last week's losers, short
its winners, weekly rebalance. Liquidity provision to flow-driven moves.

| Sleeve | FULL Sharpe | TRAIN | TEST | max DD |
|---|---|---|---|---|
| **S8 BAB** | **0.81** | 0.86 | 0.77 | −20.6% |
| S9 STOCKREV | −0.54 | −0.02 | −0.95 | −84.7% |

S9 is dead — arbitraged away and buried by 5 bp weekly turnover. Dropped on
train evidence. S8 is the **strongest single sleeve found in eleven iterations**,
and it is stable across train and test rather than being a one-period result.

## Adding it to the portfolio

Correlation of S8 to the existing sleeves: +0.17 (MEANREV), +0.31 (TSMOM),
+0.13 (XSMOM), +0.34 (VOLMANAGED), +0.13 (STREV). Genuinely additive.

> n_eff: **2.61 → 2.83**

| Portfolio | TRAIN | TEST | FULL | CAGR | max DD |
|---|---|---|---|---|---|
| Iteration 9 baseline (5 sleeves) | 0.60 | 0.94 | 0.77 | 4.87% | −7.46% |
| **+ S8 BAB (6 sleeves)** | 0.61 | **1.16** | **0.89** | 5.44% | −7.57% |

Full-sample Sharpe **0.89**, 95% CI [0.21, 1.57]. Test-period Sharpe **1.16**.

## Against your target

| Horizon | win rate | payoff | worst period | vs iteration 9 |
|---|---|---|---|---|
| Weekly | 60.9% | 1:0.92 | −4.74% | was 58.6% / 1:0.97 |
| Monthly | **64.3%** | 1:1.14 | −3.92% | was 61.4% / 1:1.21 |
| Quarterly | **72.3%** | 1:1.44 | −5.08% | was 68.1% / 1:1.45 |

**The win rate moved up decisively and the payoff ratio did not move at all.**
That is worth understanding rather than glossing over. At Sharpe 0.89 the
Gaussian formula predicts 66.9% quarterly wins at 1:1.49. We got a *higher* win
rate (72.3%) and a *lower* payoff (1:1.44) than predicted. The reason is negative
skew: the portfolio wins more often than normal and loses bigger when it loses.

That has a direct consequence for your target. **The 1:1.5 payoff leg is harder
to reach empirically than the Sharpe arithmetic suggests**, because every
strategy in this portfolio is short some form of tail risk. Raising Sharpe
raises the win rate efficiently and the payoff ratio only grudgingly. If you want
the payoff leg, it has to come from a positively-skewed sleeve — a long-volatility
or trend-following-with-wide-stops construction — not from more Sharpe.

## The caveat that matters most

S8 BAB decays badly over time:

| Period | Sharpe | CAGR | max DD |
|---|---|---|---|
| 2000–2007 | **1.30** | 12.18% | −19.4% |
| 2008–2015 | 0.78 | 7.98% | −20.5% |
| **2016–2026** | **0.51** | 4.73% | −19.6% |

This is textbook post-publication factor decay — BAB became famous around 2014
and the money followed. The full-sample 0.81 overstates what to expect forward;
**0.51 is the honest recent estimate.** And because the ETF sleeves only span
2006–2017, the portfolio Sharpe of 0.89 is measured during BAB's stronger phase.
A forward estimate should be marked down accordingly — I would plan around
something closer to 0.7 than 0.9.

## Where the system stands after eleven iterations

**Six sleeves, equal weight, no conditioning:** DipScore mean reversion,
time-series momentum, cross-sectional momentum, volatility-managed equity,
short-term reversal, betting-against-beta.

- Sharpe **0.89** full-sample (**1.16** out-of-sample), against SPY's 0.46
- Max drawdown **−7.6%**, against SPY's −56.5%
- **72.3% winning quarters at 1:1.44**; 64.3% winning months
- Worst quarter −5.1%, worst month −3.9%

Your win-rate target is met at both monthly and quarterly horizons. The payoff
leg sits just under 1:1.5 and, per the skew argument above, will not get there by
adding Sharpe.

## Next, in order of expected value

1. **A positively-skewed sleeve** — long-vol, or trend-following with wide stops
   and long holding periods. This is now the specific missing ingredient, and it
   targets the payoff leg directly rather than hoping Sharpe drags it along.
2. **Extend the ETF panel past 2017.** The 95% CI is still [0.21, 1.57]. Nothing
   narrows it but years, and the BAB decay table shows why measuring the recent
   decade matters.
3. **Still not more conditioning.** Six failures now.
