# The System — Every Component Measured

## Daily preparation, from yesterday's VIX close

| VIX | expected range | trade budget | stop | target | risk/trade |
|---|---|---|---|---|---|
| 11 | 0.54% | **1** | 0.9 | 1.3 | 1.00% |
| 15 | 0.79% | **1** | 1.4 | 1.8 | 1.00% |
| 18 | 0.97% | **2** | 1.7 | 2.3 | 0.50% |
| 25 | 1.41% | **3** | 2.5 | 3.3 | 0.33% |
| 35 | 2.03% | **4** | 3.6 | 4.8 | 0.25% |

*(SPY points. Range forecast out-of-sample R² = 0.54, Part 7.)*

Note what the budget does: **daily risk stays constant at 1%** regardless of regime.
More trades allowed on big days, each one smaller. On a VIX-11 morning you get one
trade and that is the correct number — not a limitation, a measurement.

## Execution parameters

| component | setting | source |
|---|---|---|
| strike | **ITM by ~1 SPY strike** | Part 8: best median (−20.9% vs −50.6% OTM), best win rate |
| entry | **limit, ~12% of stop distance against signal** | Part 3: largest single improvement measured |
| sizing | on **53.8% premium loss**, not 100% | Part 8: measured loss at stop |
| stop / target | 0.35 / 0.47 × expected range | Part 7 |
| instrument | SPY 0DTE, ITM | Part 8: cost-competitive with futures per delta |

## Why sizing on 100% premium loss is wrong

The underlying stop fires long before the option is worthless. Measured loss at a
stop-out is 53.8% of premium. Sizing for total loss halves your position for no reason
and is the most common retail sizing error in 0DTE.

## The one unspecified component

```python
class Signal:
    def evaluate(self, bar, plan):
        raise NotImplementedError("No validated directional edge exists yet.")
```

**Measured requirement:**

| TP rate (2.0 ATR before 1.5 ATR) | expectancy per trade |
|---|---|
| **41.5%** | **−6.10%** ← random entries |
| 45.0% | −2.09% |
| **46.8%** | **0.00%** ← breakeven |
| 50.0% | +3.65% |
| 55.0% | +9.40% |

You need to beat random by **5.3 percentage points** — a 12.8% relative improvement in
hit rate. That is the entire remaining problem, and sixteen studies have not solved it.

## Honest status

Six of seven components are measured and specified. The seventh decides whether the
system makes money. A perfectly engineered wrapper around a zero-edge signal returns
−6.10% per trade, and that is exactly what the top row of the table says.

**Do not run this live with a placeholder signal.** The infrastructure being correct
does not make the trade positive; it only ensures a real edge wouldn't be wasted.

## What would actually complete it

The breakeven bar — 46.8% vs 41.5% random — is not enormous. It is also not something
price history alone has produced across sixteen studies on this data. If you pursue it,
the places with a mechanism rather than a pattern are:

- order flow / market depth (not available in this dataset)
- options positioning and dealer gamma (requires options chain data)
- crowded-positioning feeds where being wrong is structural, not random

Each requires data outside price history. That is the consistent finding of this project.
