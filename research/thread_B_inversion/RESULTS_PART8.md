# Part 8 — 0DTE Mechanics, and Where the VRP Can Actually Be Traded

## Your TP claim: I was wrong, you were right

I doubted it. The simulation says otherwise. 3,958 simulated ATM 0DTE calls priced
minute-by-minute with Black-Scholes, IV from prior-close VIX, on SPX 1-minute data.

**Of the 1,643 trades where the underlying reached its target:**

| | |
|---|---|
| option still lost money | **0.5%** |
| median option return | **+63.9%** |
| worst case | −47.1% |

| time to TP | n | median option return | option lost money |
|---|---|---|---|
| <15 min | 504 | +54.7% | 0.6% |
| 15–30 min | 332 | +69.3% | 0.3% |
| 30–60 min | 377 | +73.7% | 0.0% |
| 1–2 h | 317 | +68.3% | 0.3% |
| >2 h | 113 | +49.0% | 2.7% |

Even trades taking over two hours were profitable 97% of the time. **Your intuition holds
— if SPY hits your target, the option is a winner.** Theta doesn't eat a real directional
move on the timescales day traders actually hold.

## But the winners were never the problem

Same trades, two instruments:

| | underlying | 0DTE option |
|---|---|---|
| win rate | 45.7% | 42.7% |
| mean outcome | +0.053R | −0.9% |
| **median outcome** | **−0.659R** | **−30.3%** |

And the days that go nowhere — 7% of trades:

| | |
|---|---|
| median underlying move | **+0.50 pts** (flat) |
| median option return | **−68.4%** |

The underlying did nothing. The option lost two thirds. That's the second axis: on a
chart, a flat day costs you nothing. On a 0DTE option it's near-total loss.

## The cost comparison, which surprised me

Per unit of SPX delta exposure:

| instrument | round-trip cost |
|---|---|
| 0DTE option @ 1% spread | **0.108 pts** |
| ES futures direct | 0.330 pts |
| 0DTE option @ 3.7% spread (realistic SPY ATM) | 0.400 pts |

At realistic spreads 0DTE is roughly **cost-comparable to futures** per unit of exposure —
not the disaster I implied. Your instinct to use them for leverage isn't wrong on cost
grounds.

Cost sensitivity on the same trades:

| option round-trip cost | mean return |
|---|---|
| 0.5% | +0.1% |
| 1.0% | −0.9% |
| 2.0% | −2.8% |
| **3.7% (realistic)** | **−6.1%** |
| 5.0% | −8.5% |

## What this actually means

0DTE is a **leverage-and-cost wrapper**. It faithfully amplifies whatever edge you feed
it — including a zero edge, which is what random entries have and what all thirteen
studies produced.

Underlying entries were roughly breakeven (+0.053R). Wrapped in 0DTE at realistic cost
they became **−6.1% per trade**. The wrapper didn't break the logic. It multiplied a zero
and added a theta tax.

**So the constraint is unchanged and unmoved by instrument choice: you still need a
directional edge.** 0DTE is a fine way to express one and an expensive way to express its
absence.

---

## Can you trade the VRP on your accounts?

### Forex account — **no**

Spot FX cannot express variance exposure. There is a genuine FX volatility risk premium,
but harvesting it requires FX options, not spot.

### Stock account — **only with options approval**

The standard retail implementation is selling index options or defined-risk spreads on
SPX/SPY at roughly 30–45 days to expiry. That is the instrument that corresponds to what
I measured.

Without options approval, the only stock-account route is short-vol ETPs (SVXY and
similar). Be clear that this is **not** the thing I measured: SVXY lost ~90% in a single
session in February 2018, and its sibling XIV was terminated outright that week.

### Is it "ready to trade"? — **No, and this gap matters**

What I measured was **VIX minus subsequently realised volatility.** That is a *phenomenon*,
not a strategy. I never backtested:

- actual option prices or bid-ask spreads
- margin requirements or margin expansion during stress
- assignment and early-exercise risk
- the path dependency of a real position versus a variance-swap-like payoff
- what a broker does to your position when margin spikes mid-event

The distance between "+3.25 vol points exists" and "here is a tradeable P&L curve" is
large, and I have not crossed it. Anyone presenting the first as the second is skipping
the part where the money is actually won or lost.

And the caveat from Part 5 stands and is the most important one: **the entire tail risk is
estimated from 5 observations, in a sample containing neither 2008 nor 2020.**

---

## Where the project stands

| component | status |
|---|---|
| when to trade (VIX trade budget) | ✅ measured |
| position sizing | ✅ measured |
| stop distance | ✅ measured |
| entry mechanics (limit orders) | ✅ measured |
| instrument choice | ✅ measured — 0DTE viable on cost |
| **directional edge** | ❌ **fourteen studies, still nothing** |

Everything except the signal is now specified. That is genuinely useful — it means a real
edge, if you find one, won't be wasted. It is not a strategy on its own, because a
perfectly engineered wrapper around zero is still zero.

---

*Historical research, not financial advice. 0DTE options can lose their entire value in a
single session; short-volatility positions can lose many times the premium collected.*
