# ASSESSMENT — iteration 4, cross-sectional fan-out

This executed BLOCKED.md option 2: stop asking one instrument for more years,
ask many instruments for the same years. **The power problem is solved. The
answer is not the one we were hoping for.**

`/fleet` is not available in this environment — no such skill or command here —
so the fan-out ran as 4 OS processes over `fleet_worker.py`. Each symbol is an
INDEPENDENT concern under the ownership map, with no shared state, so the worker
is `/fleet`-ready as written: point it at a symbol list and it parallelises
without modification.

---

## Setup

- **652 symbols** passing filters (≥1,200 daily bars, median price ≥ $5, median
  dollar volume ≥ $5M), drawn from 928 candidates, 2000-11 → 2026-03.
- **236,841 trades** across three geometries, plus **90,311 matched
  random-entry control trades**, one control per symbol.
- Rule set **frozen** from the SPY study. Nothing tuned per symbol. This is a
  replication test, not a search.
- Costs raised to **5 bp round trip** (single stocks, not SPY).

**Selection caveat, stated up front:** this basket was assembled by a
"big movers" project, so it is skewed toward names that had large single-day
moves. It does contain delisted and bankrupt tickers (AAMRQ, ABK), so it is not
survivorship-biased toward winners — but it is not the liquid-ETF universe the
option-2 plan called for, because no such dataset was reachable from here. It
contains **no index ETFs at all**, which turns out to matter (§4).

## 1. The inference correction that changes everything

These names dip together. Treating 77,000 trades as independent observations
inflates significance enormously. Averaging within each calendar day first and
testing the daily series is the honest version:

| Geometry | n | win | net R:R | meanR | naive t | **clustered t** |
|---|---|---|---|---|---|---|
| stop 2.0 / target 1.0 | 77,068 | 61.3% | 1:0.66 | +0.012 | 5.4 | **0.91** |
| stop 1.0 / target 2.0 | 74,416 | 39.1% | 1:1.75 | +0.075 | 14.8 | **6.58** |
| stop 0.75 / target 1.5 | 85,357 | 36.3% | 1:1.88 | +0.045 | 9.3 | **4.22** |

A naive t of 14.8 looks like a discovery. It is not one.

## 2. And then the control eats it

The same geometries, entered at random dates in the same uptrend filter:

| Geometry | strategy meanR | control meanR | **excess** | paired clustered t |
|---|---|---|---|---|
| stop 2.0 / target 1.0 | +0.0118 | +0.0035 | **+0.0031** | 0.61 |
| stop 1.0 / target 2.0 | +0.0746 | +0.0637 | **−0.0008** | **−0.07** |
| stop 0.75 / target 1.5 | +0.0451 | +0.0412 | **−0.0048** | −0.39 |

The clustered t of 6.58 on the 1:2 geometry was **entirely** the random control.
Long exposure to uptrending names with a 1:2 bracket makes money; the DipScore
signal contributed nothing to it. Excess is zero to three decimal places.

Per-symbol consistency agrees: the share of the 652 names where DipScore beats
its own control is **50.7% / 52.0% / 51.5%** across the three geometries. A coin
flip.

## 3. A finding that looked real, and why it wasn't

Bucketing symbols by per-trade R dispersion produced a clean monotonic gradient
on the wide-stop geometry — the edge appeared in the calmest names and inverted
in the most volatile:

> Q1 +0.0442 · Q2 +0.0223 · Q3 +0.0060 · Q4 −0.0202 · Q5 −0.0409

Q1–Q2 pooled gave excess +0.0210 at clustered t = 2.64, and it held in the
2015+ half at t = 2.05. That is exactly the shape of a real effect, and the
mechanism was plausible: calm names behave more like an index, and index
mean-reversion is a documented thing that single-stock momentum is not.

**It was lookahead.** The volatility buckets were built from the full sample,
including the trades being scored. Rebuilding them from **pre-2015 data only**
and testing on 2015+ only:

| Bucket (fixed pre-2015) | n | excess | clustered t |
|---|---|---|---|
| Q1–Q2 calmest | 10,993 | −0.0012 | −0.09 |
| Q3 middle | 5,743 | −0.0003 | −0.01 |
| Q5 most volatile | 4,842 | +0.0046 | 0.21 |

The gradient is gone. Not weakened — gone, and with the sign scrambled. Three
levels of false discovery were available in this iteration (naive t, control-
uncorrected excess, lookahead bucketing) and all three would have produced a
confident wrong answer.

## 4. Scoring, and what is now settled

| # | Requirement | Result |
|---|---|---|
| 1 | ≥200 OOS trades, ≥1:2 net R:R, ≥55% win | **FAIL, decisively.** At 1:1.75 net the win rate is 39.1% on 74,416 trades |
| 2 | ≥+0.15R over control, CI excluding 0 | **FAIL.** Excess is −0.0008, t = −0.07 |
| 3 | <35% degradation, plateau | N/A — no edge to degrade |
| 4 | 2× cost stress | N/A |
| 5 | Reproducible, config count stated | **PASS** — ~160 configs total across four iterations |
| 6 | Split reporting | **PASS** — by geometry, volatility bucket, and period |

**The frontier, now measured on 74,000–85,000 trades across 652 names:**
61.3% win at 1:0.66, or 39.1% win at 1:1.75. Those are two points on one curve.
Nothing in a quarter-million trades sits at 55%+ *and* 1:2. Four iterations,
two instruments, two resolutions, and three data sources have now produced the
same curve. I would treat that as settled rather than as four failures.

## 5. The one thing this could not test

The cross-section contains **no index ETFs**. So it cannot distinguish between:

- **(a)** the SPY edge is index-specific — indices mean-revert intraday and
  multi-day in a way single stocks do not, which is well documented and would
  explain a real SPY edge coexisting with a null cross-section; and
- **(b)** the SPY edge was one instrument's good luck.

The wide-stop excess on SPY was +0.12R. On 652 single stocks it is +0.003R with
t = 0.61. That is a 40× gap, which favours (a) — but favouring is not
demonstrating.

**The decisive test is 20 index ETFs** — QQQ, IWM, DIA, EFA, EEM, MDY, RSP, the
nine sector SPDRs — run through `fleet_worker.py` unchanged. That is one data
file per symbol and about ten minutes of compute. Nothing in this environment
could reach that data; it is the single input that would close the loop.

## 6. Honest bottom line

The high-win-rate SPY system remains the only thing in this whole study that
survived its own out-of-sample gate. It is small (~1.3R/year), it is
instrument-specific until (a) is demonstrated, and it is emphatically not a 1:2
system. The 1:2-with-high-win-rate target has now been tested at daily
resolution, minute resolution, multi-day holds, four entry timings, three
geometries, and 652 instruments. It does not exist in any of them.
