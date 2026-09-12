# ASSESSMENT — iteration 9: your target, measured where it can actually be met

You asked for >60% win rate with a payoff ratio of 1:1.5 to 1:3. Eight
iterations said that is impossible. Both statements are true, and the
distinction matters more than anything else in this report.

---

## 1. Why the target was impossible before, and isn't now

At the level of a **single trade**, win rate and payoff are locked together by
expectancy. 60% wins at 1:2 means +0.80R per trade. Nothing in 410 tested
configurations came within an order of magnitude.

At the level of a **portfolio over a holding period**, they are not locked
together — they are both just functions of Sharpe and horizon:

> win rate at horizon T = Φ(Sharpe × √T)

| Sharpe | monthly win | monthly payoff | quarterly win | quarterly payoff |
|---|---|---|---|---|
| 0.50 | 55.7% | 1:1.14 | 59.9% | 1:1.26 |
| 0.68 | 57.8% | 1:1.20 | 63.3% | 1:1.36 |
| **0.94** | **60.7%** | 1:1.28 | **68.1%** | **1:1.53** |
| 1.20 | 63.5% | 1:1.37 | 72.6% | 1:1.72 |
| 1.50 | 66.7% | **1:1.48** | 77.3% | 1:1.97 |

This is the whole answer to your question. **Your target is a Sharpe target in
disguise.** 60% win at 1:1.5 requires Sharpe ≈ 0.94 measured quarterly, or
≈ 1.50 measured monthly. It requires nothing at all from the trade geometry.

## 2. What was built

Two more sleeves added to iteration 8's four, chosen for different return
drivers, not better fit:

- **S5 VOLMANAGED** — scale equity exposure inversely to trailing variance
  (Moreira & Muir). Volatility is persistent, expected return is not.
- **S6 STREV** — cross-sectional 5-day reversal, long the week's losers, short
  its winners. Liquidity provision; structurally opposite to 12-month momentum.

| Sleeve | TRAIN Sharpe | TEST Sharpe |
|---|---|---|
| S1 MEANREV | 0.60 | 0.87 |
| S2 TSMOM | 0.51 | 0.58 |
| S3 XSMOM | 0.02 | 0.75 |
| S4 TURNMONTH | −0.20 | 0.42 |
| S5 VOLMANAGED | 0.32 | 0.93 |
| S6 STREV | 0.44 | −0.29 |

> Mean pairwise strategy correlation 0.215 → **n_eff = 2.89** (four sleeves gave 2.42, one rule across 23 assets gave 1.78)

Sleeves kept on **train evidence only** (positive train Sharpe): S1, S2, S3, S5,
S6. Note that this selection dropped S4, which then did well in test, and kept
S6, which then did badly. **Sleeve selection added nothing** — combined test
Sharpe was 0.94 either way. An honest null.

Weighting schemes, chosen on train and verified on test:

| Scheme | TRAIN | TEST | TEST maxDD |
|---|---|---|---|
| Equal weight | 0.45 | 0.94 | −6.69% |
| Correlation-adjusted risk parity | 0.39 | 0.97 | −6.49% |
| Inverse-vol | 0.34 | 0.96 | −6.66% |

All three land within 0.03 of each other. Clever weighting buys nothing;
equal weight wins on simplicity. Another honest null.

## 3. The final system, against your target

**Five sleeves, equal weight, each vol-targeted to 10%. Full sample 2006–2017:
Sharpe 0.77, CAGR 4.87%, vol 6.3%, max drawdown −7.46%.** SPY over the same
period: Sharpe 0.46, max drawdown −56.5%.

| Horizon | win rate | payoff | worst period | verdict |
|---|---|---|---|---|
| Weekly | 58.6% | 1:0.97 | −5.68% | not met |
| **Monthly** | **61.4%** | 1:1.21 | −3.98% | win met, payoff short |
| **Quarterly** | **68.1%** | **1:1.45** | −5.63% | win met, payoff just short of 1.5 |
| Annual | 83.3% | 1:7.23 | −1.05% | **met** |

**You are essentially there at the quarterly horizon** — 68.1% win at 1:1.45
against a target of 60% / 1:1.5. In the held-out test period alone, where Sharpe
was 0.94, the quarterly figures cross the line.

A comparison that reframes what "win rate" is worth: SPY buy-and-hold has a
*higher* monthly win rate than this system (65.7% vs 61.4%) — and a payoff of
1:0.81 and a worst month of −16.5% against this system's −3.98%. **A high win
rate with a bad payoff is how buy-and-hold looks.** Chasing win rate alone would
have led you to the worse system every time.

## 4. The number that should govern how you use this

**Sharpe 0.77 over 11.6 years carries a standard error of 0.33.**

> 95% confidence interval: **[0.05, 1.33]**

That interval contains "barely works" and "excellent." Eleven years cannot
distinguish them. Everything above — the sleeve rankings, the weighting
comparison, quarterly 1:1.45 versus a 1:1.5 target — sits inside that band. I
can tell you the system is probably positive and very likely far less
drawdown-prone than buy-and-hold. I cannot tell you it is Sharpe 0.94 rather
than 0.5, and neither can anyone else with 11 years of data.

Other limits, stated plainly: 2006–2017 only, one major crisis; S2–S6 have not
had the control tests and lookahead audits that S1 received in iterations 4–6;
no borrowing, shorting, or tax costs modelled; the levered variant assumes free
leverage, which does not exist.

## 5. What to do

1. **Target Sharpe, not win rate.** Your goal translates to Sharpe ≈ 0.94
   quarterly. That is the single number to optimise, and it is honest because it
   cannot be gamed by moving the target closer to the stop.
2. **The only reliable lever is more uncorrelated sleeves.** n_eff went
   1.78 → 2.42 → 2.89 across iterations 7–9, and Sharpe rose 0.46 → 0.68 → 0.77
   with it. A carry sleeve, a volatility-risk-premium sleeve, or a rates-specific
   trend sleeve would each plausibly add another 0.1–0.2. Nothing else has moved
   the number.
3. **Do not add sleeves that correlate with what you have.** S6 correlates with
   nothing and still failed out of sample; S4 was dropped by train selection and
   then worked. Sleeve-level selection is noise at this sample size — hold them
   all, equally weighted, and let the correlation matrix work.
4. **Extend the data past 2017 before trusting any of this.** The confidence
   interval is the binding constraint now, and only more years narrow it.
