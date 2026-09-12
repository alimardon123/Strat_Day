# Part 2 — The Deep Search: 282 Hypotheses, Then Cross-Market Validation

## What was tested

57 structural / behavioural conditions × 5 forward horizons = **282 hypotheses**, all
tested simultaneously so the multiple-comparison correction is honest.

Conditions covered: time-of-day (6 windows), day-of-week, turn-of-month, overnight gap
behaviour, prior-day carryover, opening-range state, round-number magnetism (25/50/100
point levels), momentum and reversal at 4 timescales, consecutive-bar runs, volatility
regime, position within the day's range, VWAP deviation, and 6 interaction terms.

Guards applied: train (2013-16) / test (2017-18) split, direction locked on train only,
day-block bootstrap p-values, Benjamini-Hochberg FDR across all 282 tests.

## Result 1 — structure exists

| | count |
|---|---|
| tests run | 282 |
| correct direction held out-of-sample at \|t\|>1.96 | **35** |
| expected by chance | ~7 |

**Five times more than chance.** The market is not a random walk. Your instinct was right.

## Result 2 — but naive significance is inflated by ~10¹⁴

| candidate | naive t | implied p | day-block bootstrap p |
|---|---|---|---|
| gap_up + OR_breakout_up @ 60m | 8.51 | ~1e-17 | **0.0030** |
| gap_up_big @ close | 7.04 | ~1e-12 | **0.20** |
| dow_mon @ close | 6.91 | ~1e-11 | **0.17** |
| vol_quiet @ 60m | 6.26 | ~1e-9 | **0.020** |

Overlapping 60-minute forward returns on 5-minute bars share 11 of 12 bars. Nominal n is
~12x the effective n, and day-level clustering costs more on top. **A t-stat of 8.5
became p = 0.003.**

Survivors of Benjamini-Hochberg FDR at 10% across all 282 tests: **0**
Survivors of Bonferroni: **0**

## Result 3 — the best candidate, confronted with unseen data

Best candidate: *gap up + opening-range breakout up → 60-minute drift.*
It has a real mechanism (overnight information + intraday confirmation) and an effect
size above the cost wall. So it earned a proper out-of-sample test.

| market / period | days | n | effect (ATR) | lift vs drift | naive t | bootstrap p |
|---|---|---|---|---|---|---|
| **SPX 2013-2018 (discovery)** | 310 | 9,776 | **+0.283** | +0.248 | +10.63 | 0.0003 |
| SPX 2010-2012 (holdout) | 93 | 3,235 | +0.080 | +0.051 | +1.57 | 0.31 |
| DAX 2010-2018 | 446 | 12,807 | +0.084 | +0.098 | +4.06 | 0.10 |
| EuroStoxx 2010-2018 | 425 | 11,633 | **−0.020** | +0.038 | −0.73 | 1.00 |
| Nikkei 2010-2018 | 139 | 3,149 | +0.456 | n/a | +4.80 | 0.04 |

**Nikkei must be discarded** — session auto-detection failed (found 17:31 ET, produced
only 139 usable days of ~2,300, unconditional drift came back NaN). The one "confirmation"
is from the market where the measurement visibly broke.

That leaves: **0 of 3 reliable independent confirmations at p<0.05.**
Sign was positive in 2 of 3. Effect shrank from +0.283 to ~+0.08 ATR — **a 72% haircut**,
the classic signature of a small real effect buried in a large overfit.

## Result 4 — the cost wall, again

| | ATR units | SPX points |
|---|---|---|
| effect as discovered | +0.283 | +0.41 |
| effect out-of-sample | +0.082 | **+0.12** |
| ES futures round-trip cost | — | **0.25 – 0.33** |

The surviving effect is real-ish and roughly **one third of what it costs to trade it.**

---

## The honest answer to "there must be a loophole"

There are. This study found 35 of them at nominal significance. The problem is not that
they don't exist — it's the size they come in.

**Effect sizes aren't random. They're an equilibrium.** An anomaly persists only until
someone can profitably arbitrage it, and "profitably" means *bigger than transaction
costs*. So surviving anomalies cluster just underneath the cost wall of whoever is
cheapest to trade. That's not bad luck; it's the mechanism that sets the size. Every
finding in this study landed exactly there, which is what the theory predicts.

This is why "search harder" doesn't work as a plan. The binding constraint is not how
many hypotheses you test. It is:

| lever | what it does |
|---|---|
| **lower costs** | moves the wall down to meet the edge — the highest-leverage change available |
| **data others lack** | order flow, options positioning, cross-sectional universes, alt data |
| **capacity limits** | edges too small to interest a fund can still pay a small trader |
| **horizon** | fewer, larger trades pay the toll fewer times |
| **execution** | limit vs market orders can halve effective cost outright |

Note what is *not* on that list: better indicators, more creative signals, more search.

## What AI actually changes

Not intuition. This study did not "think outside the box" its way to a secret. What it
did was ask 282 questions in an afternoon **and then correctly discount for having asked
282 questions.** The second half is the part that's rare — and it's the part that turns
a t-stat of 8.5 into an honest 0.003.

That's the real edge available to you here: not finding what others missed, but not
fooling yourself about what you find. Most people running this search would have shipped
`gap_up_and_or_up` with a t-stat of 8.5 and lost money for two years.

## If you want to keep going, these are the live directions

1. **Attack cost, not signal.** Re-run the best candidate assuming limit-order entry at
   the opening-range level instead of market entry. If effective cost drops to 0.10 pts,
   a 0.12 pt edge becomes marginally positive. This is the only lever in the study that
   can flip a result.
2. **Fewer, bigger trades.** The same gross edge over 400 trades instead of 9,776 survives
   costs trivially. Test daily-horizon versions of the surviving conditions.
3. **Go where the mechanism is.** Index breakouts have no reason to be systematically
   wrong. Crowded positioning does — retail broker sentiment feeds, futures COT, crypto
   perp funding rates and liquidation levels. Your inversion idea has a genuine home
   there, and this pipeline tests it with one function swapped.
4. **Cross-sectional, not time-series.** Single-instrument timing is the most competed
   corner of the market. Ranking 500 stocks against each other is far less so, and the
   costs are shared across many small positions.

The code runs unchanged on any of these. Replace the signal function; the statistical
guards stay.

---

*This is research on historical data, not financial advice. Backtested results — even
carefully corrected ones — are not predictions.*
