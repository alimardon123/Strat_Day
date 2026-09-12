# ASSESSMENT — iteration 7: the improvement the evidence pointed at, and why it failed

You asked for a better system, and there was exactly one lever left that the
evidence supported. Iteration 6 showed the per-trade edge is capped and that the
real constraint is the number of independent bets (n_eff = 1.28 across 26 index
ETFs). Portfolio Sharpe scales with the square root of independent bets, so
holding the rule fixed and spreading it across decorrelated asset classes should
improve the system without needing a better rule.

I built it. It does not work.

---

## 1. The universe, and the number that made it look promising

23 ETFs across eleven sleeves: US / developed / EM / single-country equity,
duration, credit, inflation, precious metals, broad commodities, energy,
agriculture, four currencies, and real estate.

> Mean pairwise **price** correlation: **0.198**
> Effective independent bets: **4.30** — up from 1.28, a 3.4× improvement

That is a real structural gain, and if the edge transferred it would have been
worth roughly a 1.8× improvement in Sharpe for free.

## 2. The edge does not transfer

Pooled across all 23 assets: 1,977 trades, 62.3% win, **meanR −0.0062**.
Negative. Correlation-adjusted t on excess = 0.45, against a bar of 2.99.

Only a handful carry positive absolute expectancy — SPY (+0.120), TLT (+0.099),
GLD (+0.098), RWX (+0.064). Everything else is flat to negative.

A trap worth naming: several assets show large *positive excess* while being
flat in absolute terms — FXB's excess is +0.494 only because random long entries
in FXB lose 0.46R. Beating a terrible benchmark is not an edge. Excess over
control was the right metric when comparing signal against drift in a single
rising market; it is the wrong metric when the underlying has no drift to beat.
That is my error from iterations 4–6 carried one asset class too far, and
absolute expectancy is the correct screen here.

## 3. The out-of-sample test, which is unambiguous

Assets selected on **train 1999–2010 only** (positive absolute meanR, n ≥ 20)
→ 15 assets. Then run untouched on 2011–2017:

| Portfolio | trades | sumR | R/yr | **Sharpe** | max DD |
|---|---|---|---|---|---|
| **SPY only** | 95 | **+13.5** | +2.08 | **0.89** | **−3.6R** |
| Multi-asset (15 selected on train) | 761 | −9.0 | −1.32 | **−0.16** | −21.0R |
| All 23, no selection | 1,197 | −33.9 | −4.96 | −0.45 | −55.7R |

On the training period the multi-asset portfolio looked like a decisive win —
Sharpe 0.86 versus SPY's 0.25. Out of sample it inverts completely. The
train-period advantage was the 2003–2010 commodity, gold and EM supercycle;
2011–2017 was the other side of it, and a rising-200-day filter did not save it.

## 4. The diagnostic that makes this worth knowing

The 4.30 independent bets were an illusion, and I can show exactly why. Among
the 15 selected assets in the held-out period:

> Mean pairwise correlation of **realised R streams**: **0.529**
> → n_eff = **1.78**, not 4.30

**The strategy's returns are far more correlated than the underlying assets
are.** Price correlation across the universe is 0.198; strategy-return
correlation is 0.529. The reason is structural: DipScore is a long-only,
buy-the-dip-in-an-uptrend rule, so it fires on everything at once during
market-wide risk-off episodes and holds long into the same recoveries. It
manufactures a common factor out of assets that don't otherwise share one.

**Diversifying a directional rule across asset classes does not diversify the
bet.** You have to diversify the *rule*, not the instrument list. That is the
most useful thing this iteration produced, and it invalidates the plan I
recommended at the end of iteration 6.

## 5. Where that leaves the system

The best result in the entire seven-iteration programme is the simplest one:

**SPY only, wide stop, held-out 2011–2017: 95 trades, 76.8% win, +2.08 R/yr,
Sharpe 0.89, max drawdown −3.6R.**

Every attempt to improve it — finer resolution, tighter stops, intraday timing,
1:2 payoffs, 652 single stocks, 246 synthetic indices, 26 index ETFs, and now 23
multi-asset ETFs — has produced something worse. That is now seven independent
attempts, and the consistency of the result is itself the finding.

## 6. My honest recommendation

I don't think there is a better system to be found by continuing this loop, and
I'd rather say that than produce an eighth iteration that looks like progress.
Three things are worth doing instead:

1. **Paper-trade the SPY system forward.** At ~1.3 effective bets, forward
   results are the only genuinely new information that exists. Ten trades a
   year means about three years to a meaningful read, which is slow, and slow is
   the honest answer.
2. **If you want real diversification, diversify the RULE.** A short or
   trend-following or carry rule has a genuinely different return profile.
   Adding a second *uncorrelated strategy* raises n_eff; adding a 24th
   instrument to the same strategy does not. That is a new research programme,
   not a continuation of this one — and it is the one I'd actually fund.
3. **Set an expectation that matches the evidence.** ~1.3R/year at 70–76% win
   with a shallow drawdown is a real, small, unglamorous edge. It is not a
   60–70% win rate at 1:2. Nothing in 410 tested configurations across seven
   iterations was.
