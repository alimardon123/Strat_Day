# Part 7 — What VIX Actually Tells You Before the Open

## First: the VRP is not available to you

The Sharpe 2.10 comes from selling variance and **holding ~21 days**. A prop firm that
forces a flat close every session removes access to it entirely — you'd capture ~1/21 of
the premium per day while paying a full round trip daily. That is the frequency law from
Part 6 killing it again.

This is worth knowing before designing anything: **the single edge found in thirteen
studies is structurally unavailable under a day-only mandate.**

On 0DTE: I have no options data, so any number I gave you would be invention. What is
documented is the shape — small frequent credits against occasional losses of many times
the credit received. Extreme negative skew is not a detail of that trade; it *is* that
trade.

---

## What VIX predicts — three questions people constantly conflate

VIX taken at the **prior close**, so everything below is executable before the open.
SPX 2010–2018, train pre-2016, test 2016–2018.

### Q1. Today's RANGE — **strongly predictable**

| | train R² | **TEST R²** |
|---|---|---|
| VIX → today's range | 0.451 | **0.539** |
| VIX → today's \|return\| | 0.212 | 0.261 |

| VIX quintile | mean VIX | expected range |
|---|---|---|
| very low | 11.3 | **0.561%** |
| low | 13.3 | 0.713% |
| mid | 15.1 | 0.874% |
| high | 17.6 | 1.081% |
| very high | 25.3 | **1.710%** |

**R² = 0.54 out-of-sample.** VIX explains over half the variance in how big today will be.
Highest quintile is **3.05×** the lowest. This is one of the most robust relationships in
the entire project — stronger than anything in the 282-hypothesis sweep.

### Q2. Today's DIRECTION — **zero**

| | train R² | **TEST R²** |
|---|---|---|
| VIX → today's return | 0.0029 | **0.00002** |
| ΔVIX → today's return | 0.0007 | 0.0040 |

Every quintile: bootstrap p between 0.30 and 0.84. Win rates 52–56%, none significant.
**There is no directional information in VIX. None.**

### Q3. Today's CHARACTER (trend vs chop) — **essentially zero**

Efficiency ratio moves from 0.049 to 0.055 across the whole VIX range. Test R² = **0.0018**.
High VIX does not mean trendier days. It means bigger days.

---

## So how do you use it for day trading?

Not as a signal. As an **allocator**. Two concrete applications, both real.

### Application 1 — constant-risk sizing

Size positions inversely to VIX-predicted range instead of using a fixed size:

| | daily vol | vol-of-vol | worst day |
|---|---|---|---|
| fixed size | 0.721% | 0.208 | −4.311% |
| **VIX-scaled size** | 0.664% | **0.128** | **−3.497%** |

Vol-of-vol down **39%**, worst day improved **19%**. This creates no alpha — it makes your
risk stationary, which is what lets you survive long enough for an edge to show up. It
also stops the classic failure of using the same stop distance on a VIX-11 day and a
VIX-25 day.

### Application 2 — the trade budget, and this is the important one

Your round-trip cost is fixed. The size of the day is not. So cost as a fraction of the
opportunity varies **3×** with VIX:

| VIX regime | expected range | cost / range | relative difficulty |
|---|---|---|---|
| very low (11.3) | 0.561% | **2.80%** | **1.00× (hardest)** |
| low (13.3) | 0.713% | 2.20% | 0.79× |
| mid (15.1) | 0.874% | 1.80% | 0.64× |
| high (17.6) | 1.081% | 1.45% | 0.52× |
| very high (25.3) | 1.710% | **0.92%** | **0.33× (easiest)** |

Same trade, same skill, three times harder on a quiet day.

Combining with the Part 6 law — **maximum trades per day before cost drag exceeds a 0.6
gross Sharpe:**

| VIX regime | trade budget |
|---|---|
| very low (11.3) | **1.4/day** |
| low (13.3) | 1.7/day |
| mid (15.1) | 2.1/day |
| high (17.6) | 2.6/day |
| very high (25.3) | **4.2/day** |

**This is a real, executable day-trading rule and it's known before the open.** On a
VIX-11 morning you can afford roughly one trade. On a VIX-25 morning, four. Most retail
day traders trade the same number of times every day, which means they are structurally
over-trading two days out of five.

---

## The system this actually implies

| component | rule | source |
|---|---|---|
| **when to trade** | trade budget set by prior-close VIX (1–4/day) | Part 7 |
| **how big** | size inversely to VIX-predicted range | Part 7 |
| **stop distance** | scale with predicted range, not fixed points | Part 7 |
| **entry** | limit orders, never market | Part 3 |
| **instrument** | liquid futures, never CFDs | Part 6 |
| **required gross Sharpe** | ~0.56 at 4/day tight cost | Part 6 |
| **direction** | ← **still unsolved, and VIX does not help** | Part 7 |

Six of seven components are now specified from measured data. The seventh — which way to
bet — is the one thing thirteen studies have not produced, and VIX contributes exactly
nothing to it.

That is an honest place to be. It means any directional idea you bring can now be dropped
into a framework that won't waste it on over-trading, mis-sizing, or costs. It does not
mean the directional problem is solved.

---

*Historical research, not financial advice. 0DTE short-premium strategies carry risk of
losses far exceeding the credit received.*
