# Inversion & Stop-Cascade Study — S&P 500, 1-minute bars

**Data:** Histdata SPXUSD 1-minute bars, 2013-01-02 → 2018-12-31
(559,751 RTH bars, 1,542 sessions), via `FutureSharks/financial-data` on GitHub.

**Method:** Signals generated on 5-minute bars, every stop/target resolved on the
**1-minute path** so intrabar ordering is never guessed. Stop is checked before
target within a bar (pessimistic). Costs charged in index points, round trip.
Train = 2013–2016, Test = 2017–2018.

---

## 1. The strategy we're inverting

Naive Donchian breakout, 20×5m lookback, stop 1.5 ATR, target 3.0 ATR, flat at 15:55.
4,383 trades.

| | win % | avg R:R | expectancy | t-stat |
|---|---|---|---|---|
| with 0.50 pt cost | 34.4% | 1 : 1.29 | **−0.2554R** | −12.43 |
| zero cost | 35.6% | 1 : 1.81 | **+0.0005R** | **+0.02** |

**This is the critical row.** The strategy has *literally zero* raw edge — t-stat +0.02
over 4,383 trades. It is a coin flip that loses because it pays a toll 4,383 times.

That matters because a zero-edge signal carries no information to invert.

---

## 2. Inverting it

Two things people mean by "trade the opposite":

| | win % | avg R:R | expectancy | zero-cost exp |
|---|---|---|---|---|
| Original | 34.4% | 1 : 1.29 | −0.2554R | +0.0005R |
| **A. Mirror** (flip dir, levels swap) | **62.8%** | **1 : 0.38** | **−0.1285R** | −0.0006R |
| **B. Symmetric** (flip dir, same 1.5/3.0) | 34.9% | 1 : 1.29 | −0.2371R | +0.0188R |

**The win rate did exactly what you predicted — it jumped from 34% to 63%.**
And it changed nothing, because R:R collapsed from 1:1.29 to 1:0.38 in near-exact
proportion. You now risk 2.6 to make 1. Expectancy stayed negative.

The zero-cost column is the proof of mechanism: +0.0005R became −0.0006R. Inversion
mapped zero onto zero. Everything else was the toll.

Break-even round-trip cost for the symmetric inversion: **≈0.04 points.** Real cost is
0.25–0.50. Not close.

---

## 3. The stop-cascade test (your real idea)

For all 2,681 stopped-out trades: at the stop-out bar, enter in the *continuation*
direction. Control = same session, same direction, same ATR, a random bar ≥30 min away.

### Excursion (ATR units, mean MFE − MAE)

| horizon | sweep | control | advantage | t |
|---|---|---|---|---|
| 15 min | −0.014 | −0.159 | +0.146 | +4.06 |
| 30 min | −0.056 | −0.301 | +0.245 | +4.86 |
| 60 min | −0.087 | −0.515 | +0.428 | +6.24 |
| 120 min | −0.042 | −0.888 | **+0.846** | **+9.37** |

**The stop-cascade effect is real.** t = +9.4 is not noise. Stop-out points are
genuinely better entries than random bars in the same session.

### But as an actual trade

| bracket | sweep exp | control exp | sweep @ zero cost |
|---|---|---|---|
| 1.0 / 2.0 ATR | −0.4307R | −0.5852R | −0.0368R (t −1.41) |
| 1.5 / 3.0 ATR | −0.2747R | −0.5199R | −0.0121R (t −0.49) |
| 2.0 / 2.0 ATR | −0.2253R | −0.3949R | −0.0284R (t −1.59) |

Sweep beats control by **+0.17 to +0.25R every time** — the edge is consistent and
directionally exactly what you argued. It is still **below zero before costs are even
charged.**

**Why the excursion table and the trade table disagree:** MFE is not capturable. You
don't know when the maximum happens. The bracket simulation is the honest number; the
excursion study is a screening tool that produces false positives. Worth remembering
whenever you see a promising MAE/MFE chart.

---

## 4. Conditional polarity — where the edge would have to live

Gross (zero-cost) expectancy by regime, buckets chosen on train, applied untouched to test:

| regime | bucket | train exp | train t | test exp | test t |
|---|---|---|---|---|---|
| time of day | morning | +0.0529 | +0.93 | **+0.1424** | +1.78 |
| time of day | into close | −0.0299 | −0.78 | **−0.1242** | −2.27 |
| efficiency ratio | all 4 buckets | — | <\|1.7\| | — | sign flips |
| volatility ratio | all 4 buckets | — | <\|0.8\| | — | sign flips |
| position in day | all 4 buckets | — | <\|1.4\| | — | sign flips |

Only **time of day** keeps its sign across train and test: breakouts work in the morning,
fail into the close. Everything else flips sign out-of-sample — i.e. it was noise.

### The cost wall

Median risk per trade = 2.17 points.

| | gross edge | in points | breakeven RT cost |
|---|---|---|---|
| unconditional | +0.0005R | 0.001 | 0.001 pts |
| best bucket (morning) | +0.1424R | 0.309 | **0.309 pts** |
| best bucket (close, inverted) | +0.1242R | 0.269 | **0.269 pts** |

| instrument | realistic round-trip cost |
|---|---|
| CFD (what this data is) | 0.50 pts |
| ES futures, 1 tick + commission | 0.33 pts |
| ES futures, spread only | 0.25 pts |

The best conditional variant needs costs under ~0.28 points. ES futures sit at ~0.33.
**It's close, but it's the wrong side of the line — and that's the *best* bucket found
after searching 16 of them, so it's inflated by selection.**

---

## Conclusions

1. **Inversion is not a strategy.** It transforms a signal's edge; it cannot create one.
   Here it mapped +0.0005R to −0.0006R.
2. **Your win-rate prediction was right and it didn't help.** 34% → 63% is real. R:R fell
   1:1.29 → 1:0.38 at the same time. Win rate alone is not an objective.
3. **Your stop-cascade intuition was right and it isn't enough.** The effect is strongly
   significant (t = +9.4) and worth +0.2R over random entry. It's still negative before
   costs.
4. **Costs are the binding constraint, not signal quality.** Every result here is
   dominated by the 0.25–0.50 pt toll, not by whether the direction was right.
5. **The only thing that survived out-of-sample was time of day** — and it's ~15% short of
   paying for itself on the cheapest realistic instrument.

## What would actually change the answer

- **Lower the toll, not the signal.** Trade a wider stop so cost is a smaller fraction of
  R, use limit entries instead of market, or move to an instrument with a tighter
  effective spread. Halving cost does more here than any signal work.
- **Fewer, bigger trades.** 4,383 trades × 0.25R of cost = 1,100R burned. At 400 trades
  the same gross edge survives.
- **Test on a source with a behavioral mechanism.** A breakout on an index has no reason
  to be systematically wrong. Crowded retail positioning or leveraged liquidation data
  does. That's where inversion has a story, and this pipeline will test it unchanged —
  swap the signal generator in `step1_baseline.py`.
