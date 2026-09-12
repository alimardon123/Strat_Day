# ASSESSMENT — iteration 16: combining the patterns instead of picking one

Iteration 15 found a train/test t correlation of +0.256 and then did the wrong
thing with it — picked the single best cell out of 1,092 and watched it decay
from Sharpe 1.01 to 0.32. The statistically correct response to many weak-but-real
signals is aggregation, not selection. This iteration did that properly.

**Expanded pattern space:** 13 entry × 13 exit 30-minute windows × **24
pre-open and calendar conditions** — gap direction and size, prior-day direction
and range, volatility regime, day of week, turn of month, month start/end, and
monthly option expiry week. **2,275 cells** scored on train (pre-2013), test
(2013+) untouched.

**Method:** keep *every* cell that passes a train threshold — no cherry-picking —
and hold the whole basket, netting overlapping positions bucket by bucket.

---

## 1. Aggregation did not help

| Train threshold | cells kept | TRAIN Sharpe | **TEST Sharpe** | test ann. |
|---|---|---|---|---|
| \|t\| > 1.0 | 762 | 1.92 | **0.24** | +1.85% |
| \|t\| > 1.5 | 349 | 2.04 | **0.34** | +2.87% |
| \|t\| > 2.0 | 132 | 1.74 | **0.32** | +3.23% |
| \|t\| > 2.5 | 38 | 1.68 | **−0.09** | −0.98% |

**349 combined patterns produce the same out-of-sample result as the single best
one did (0.34 versus 0.32).** Train Sharpe above 2.0 collapsing to 0.34 is a
sixfold shrinkage.

## 2. Why — and this is the number that explains everything

Two measurements settle it.

**First, the patterns are not as independent as the count suggests**, though less
correlated than I expected: mean pairwise correlation 0.097 across the 132
survivors, giving **9.6 effective independent patterns**, not 132.

**Second, and more decisive — most of the "patterns" are false positives:**

| Train threshold | passed | expected by chance | excess | share plausibly real |
|---|---|---|---|---|
| \|t\| > 2.0 | 132 | 103.5 | 28.5 | **22%** |
| \|t\| > 2.5 | 38 | 28.3 | 9.7 | 26% |
| \|t\| > 3.0 | 13 | 6.1 | 6.9 | 53% |
| \|t\| > 3.5 | 4 | 1.1 | 2.9 | 74% |

At the threshold that gave the best basket, **roughly four out of five surviving
patterns are noise.** Combining them dilutes the real ones with an equal or
larger quantity of randomness — which is exactly why the basket does no better
than the single best cell. Aggregation works when the components are real and
independent; here they are neither, enough.

Raising the bar to |t| > 3.5 gets you to 74% real, but leaves four patterns and
~9.6 effective bets' worth of nothing — and the basket at that level went
negative out of sample.

## 3. What the survivors actually are

The clustering is informative:

- **Conditions:** Monday (21 cells), gap-up days (18), gap-up-after-a-down-day
  (14), wide prior range (11), option expiry week (10)
- **Windows:** the **14:30–15:30 ET block** dominates (windows 10-10, 10-11,
  11-12, 12-12)

So the exhaustive search rediscovered three things: **a Monday effect, a
gap-continuation effect, and a late-afternoon drift.** All three are documented
in the academic literature going back decades. None is undiscovered. And all
three are worth 1–2 bp per day, against ES round-trip friction of 0.7 bp.

That is what your loophole looks like when you find it: real, named, decades old,
and roughly the size of the fee.

## 4. Where this leaves the system

**Iteration 16 did not improve on iteration 15.** The best intraday construction
remains the single gap-up afternoon sleeve: 138 trades/year, 54.4% hit rate,
Sharpe 0.74 full-sample and 0.32 out-of-sample, correlation +0.16 to the daily
portfolio.

**Current system: seven sleeves, equal weight, Sharpe 1.02 full-sample / 1.10
out-of-sample**, versus SPY's 0.46 — unchanged from iteration 15.

## 5. My honest read on the pattern-hunting approach

Sixteen iterations in, the intraday pattern search has now been run three ways:
hand-picked mechanisms, a single-best selection from 1,092 cells, and an
aggregate of 349 cells from 2,275. All three converge on **out-of-sample Sharpe
of about 0.3.** That consistency is itself the finding — it is what the
underlying effect is actually worth, and no amount of additional slicing has
moved it.

The pattern space is now well characterised, and I would not spend another
iteration in it. The things that have actually raised the system's Sharpe were
never pattern searches — they were **new, structurally different return drivers**
(betting-against-beta took it 0.77 → 0.89; the intraday sleeve took it 0.89 →
1.02). Each came from a different data source or a different economic mechanism,
not from re-slicing the same series.

The measured weak spot is still the high-volatility regime (−1.87%/yr, iteration
14), and the honest fix still needs data I cannot reach here: VIX futures or a
credit series. That is a specific request rather than another search, and it
would do more for the system than a seventeenth pass over 30-minute buckets.
