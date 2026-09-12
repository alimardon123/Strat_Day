# Part 3 — Attacking Cost Instead of Signal

The one lever identified as capable of flipping a negative result: enter with a resting
limit order instead of crossing the spread. Market cost 0.33 pts → limit cost 0.10 pts,
a saving of 0.23 points ≈ **0.16 ATR**.

The catch nobody models: you only get filled when price comes *back* to you. The trades
that run away immediately are exactly the good ones, and they are the ones you miss.
That is adverse selection. Metric below is **per signal**, so missed trades count as
zero rather than being quietly deleted from the sample.

## Results (returns in ATR units)

| dataset | entry | fill % | E[r] per signal | boot p |
|---|---|---|---|---|
| **SPX 2013-18 (discovery)** | market | 100% | −0.0102 | 1.00 |
| | limit −0.25 ATR | 82.3% | **+0.1523** | **0.012** |
| | limit −0.50 ATR | 68.2% | +0.1172 | 0.024 |
| | limit −1.00 ATR | 44.7% | +0.0532 | 0.138 |
| **SPX 2010-12 (holdout)** | market | 100% | −0.2633 | 1.00 |
| | limit −0.25 ATR | 80.8% | −0.1100 | 1.00 |
| **DAX 2010-18** | market | 100% | +0.0464 | 0.234 |
| | limit −0.25 ATR | 82.3% | +0.0300 | 0.288 |
| **EuroStoxx 2010-18** | market | 100% | −0.1458 | 1.00 |
| | limit −0.25 ATR | 83.2% | −0.1093 | 1.00 |

## What this shows

**1. Execution improvement is real.** On the discovery set, limit entry moved the result
from −0.010 to +0.152 per signal — from dead to significant at p = 0.012. That is the
single largest improvement produced anywhere in this entire study, and it came from
changing *how* the trade is entered, not *what* is traded.

**2. But adverse selection eats about half of it.** The arithmetic promises more than it
delivers:

| component | expected |
|---|---|
| better entry price (0.25 ATR lower) × 82.3% fill | +0.206 |
| cost saving | +0.159 |
| **theoretical total** | **+0.365** |
| **actually observed** | **+0.195** |
| **adverse selection cost** | **−0.170** |

Roughly half the paper benefit is consumed by never being filled on the trades that
worked. Any backtest assuming limit fills without modelling this is overstating results
by about 2×.

**3. It doesn't rescue the signal out-of-sample.** Limit entry improved 3 of 4 datasets,
made DAX worse, and **never turned a negative into a positive** outside the discovery
set. Improvement averaged ~+0.06 ATR out-of-sample, well under the 0.16 ATR the cost
saving alone should deliver.

The reason is arithmetic. True out-of-sample signal edge ≈ **+0.08 ATR**. Limit-entry
cost ≈ 0.07 ATR. That is break-even *before* the 0.17 ATR of adverse selection.

## Where this leaves the whole study

| approach tested | outcome |
|---|---|
| invert a losing strategy | zero → zero; win rate 34%→63% changed nothing |
| trade the stop cascade | real effect (t = +9.4), still below cost |
| condition on regime | only time-of-day survived; below cost |
| search 282 behavioural hypotheses | 35 beat chance; **0 survived FDR** |
| validate best candidate cross-market | 72% shrinkage, 0 of 3 confirmations |
| **improve execution** | **biggest single gain — and still not enough** |

Every route ended at the same wall, and the wall was always cost rather than signal
quality. That consistency is itself the finding: it is what an equilibrium looks like
from the inside.

## The realistic path, stated plainly

Nothing here says markets are unbeatable. It says **this class of approach** — timing a
single liquid index intraday, using only price history, at retail cost — is a corner of
the market where the edge available is reliably smaller than the toll. That corner is
the most competed one that exists, because it is the one everybody can reach.

What actually moves the needle, in rough order of leverage:

1. **Cost structure.** Everything in this study was decided by it. A trader paying 0.10
   pts round-trip lives in a different market than one paying 0.50.
2. **Data others don't have.** Order flow, options positioning, funding rates, COT,
   alternative data. Price history is the one input every competitor already has.
3. **Cross-sectional over time-series.** Ranking many instruments against each other is
   far less competed than timing one, and cost is spread across many small positions.
4. **Longer horizons.** 9,776 trades × 0.23 ATR of cost is a mountain. 400 trades is not.
5. **Capacity-limited niches.** Edges too small to interest a fund can still pay a
   small trader — but only after 1 above is solved.

---

*Historical research, not financial advice. Carefully corrected backtests are still not
predictions.*
