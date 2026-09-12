# ASSESSMENT — iteration 14: winning daily, and what it costs

Two results and one correction to something I told you in iteration 8.

---

## 1. A 60% *calendar-daily* hit rate is not reachable

Daily hit rate is fully determined by Sharpe: hit = Φ(Sharpe / √252). Inverting:

| Target daily hit rate | Required Sharpe | Reference point |
|---|---|---|
| 52.0% | 0.80 | |
| **54.5%** | **1.79** | where this system is now |
| 55.0% | 1.99 | a top discretionary macro fund |
| 57.0% | 2.80 | |
| **60.0%** | **4.02** | elite quant / market making |
| 65.0% | 6.12 | HFT with queue priority |
| 70.0% | 8.32 | not publicly known to exist |

Renaissance Medallion — the best documented record in financial history — ran a
gross Sharpe in the 2–3 range. **A 60% daily hit rate requires Sharpe ~4.0.**
This is not a statement about how hard I have searched; it is arithmetic. No
amount of iteration gets there, and any system advertising a 60% daily win rate
is either not measuring calendar days or not telling the truth.

## 2. A 60% hit rate on *trading days* is reachable — and I built it

Your intuition was right, just about a different quantity. When the DipScore
sleeve is positioned, the portfolio hits **60.5%** on those days at a Sharpe of
2.57 *while active*. It is only positioned 10.1% of the time.

So: hold the portfolio **only** on high-conviction days, sized 1.55× so total
volatility matches the always-on version. Flat 90% of the time, risk budget
spent where the edge concentrates.

| | CAGR | vol | Sharpe | max DD | calendar-daily hit | **hit on trading days** |
|---|---|---|---|---|---|---|
| Always-on (6 sleeves) | 5.44% | 6.2% | **0.89** | **−7.57%** | 54.7% | 54.7% |
| **Concentrated** | 4.93% | 6.2% | 0.81 | −8.88% | 6.1% | **60.5%** |

**What you would actually experience:** 26 trading days a year, **60.5% of them
winners** (train 66.7%, test 57.6%), average win +0.92% against average loss
−0.92%, best day +3.39%, worst day −6.09%, longest losing streak 7 trades.

## 3. The price, stated plainly

Concentrating does not create edge. It repackages the same edge into fewer,
larger days — and the calendar statistics collapse:

| Horizon | Always-on hit | **Concentrated hit** |
|---|---|---|
| Weekly | 60.9% | **14.5%** |
| Monthly | 64.3% | **31.4%** |
| Quarterly | 72.3% | **46.8%** |

Most weeks and months contain no trades at all, so they are flat, and flat is not
a win. **You can have 60.5% winning trading days or 72.3% winning quarters. Not
both.** They are the same edge measured two ways, and concentrating trades one
for the other.

It also costs Sharpe (0.89 → 0.81), worsens the drawdown (−7.6% → −8.9%), and the
payoff on trading days is 1:1.01, not the 1:1.5 you wanted. On every metric that
can actually be measured, the concentrated version is slightly worse.

My recommendation is the always-on version — but this is a genuine preference
question, not a technical one. If you would rather place 26 trades a year and win
60% of them than hold a position continuously and win 55% of days, the
concentrated variant is a legitimate way to buy that, and now you know the exact
price.

## 4. Correction to iteration 8 — "works in any market condition"

In iteration 8 I wrote that the system is "as close to works-in-any-market-
condition as the evidence supports." Measured properly by daily regime, that was
too generous:

| Regime | days | System ann. return | System Sharpe | SPY ann. return |
|---|---|---|---|---|
| Uptrend | 1,952 | **+8.85%** | 1.35 | +17.01% |
| Downtrend | 391 | **−0.36%** | −0.07 | −28.82% |
| High volatility | 581 | **−1.87%** | −0.35 | +7.69% |

**The system does not make money in downtrends or high-volatility regimes. It
avoids losing much.** Against SPY's −28.82% in downtrends that is enormously
valuable, and it is what produced the −4.0% in 2008. But "defensive" and
"all-weather profitable" are different claims and I conflated them.

Sleeve-level diagnosis of where the damage is:

| Sleeve | Uptrend | Downtrend | High-vol |
|---|---|---|---|
| S1 MEANREV | +13.02% | −2.38% | −2.17% |
| S2 TSMOM | +9.50% | **+8.54%** | **−9.78%** |
| S3 XSMOM | +7.15% | **+10.44%** | **−10.63%** |
| S5 VOLMANAGED | +10.65% | −9.50% | +3.33% |
| S6 STREV | −0.01% | −4.72% | **+7.08%** |
| S8 BAB | +12.81% | −4.54% | +0.96% |

TSMOM and XSMOM carry the downtrends and get destroyed in high-vol — the classic
trend-follower whipsaw. **High volatility is the portfolio's genuine weak spot**,
and S6 STREV is the only sleeve that profits there, which is the single reason it
still earns its slot despite a standalone Sharpe of 0.07.

## 5. Where to go next

The high-vol regime is now the clearest identified gap: −1.87% annualised across
581 days, with only one sleeve contributing positively. A sleeve that profits in
high-volatility regimes would close it — and unlike everything else I have tried
since iteration 9, it is targeted at a *measured* weakness rather than a
statistical artifact.

The honest candidates need data I do not have: a long-volatility position (VIX
futures or options), or a short-credit position. Both are genuinely
high-vol-profitable and genuinely unavailable here. That is a specific,
well-defined data request rather than another search.
