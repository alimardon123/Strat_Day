# ASSESSMENT — iteration 5, and the close of the loop

Iteration 4 left one question: is the SPY edge index-specific, or was it luck?
No index-ETF OHLC is reachable from this environment, so rather than proxy an
index I tested the **mechanism** that would make an index behave differently
from a stock — diversification away of idiosyncratic risk.

---

## 1. Construction, and the gate it had to pass first

Synthetic equal-weight indices from the 626-name panel: sample *k* symbols,
equal-weight their daily returns, chain to a level series, derive OHLC from the
equal-weighted member ratios.

The first attempt produced annualised volatilities of 318%, 1146%, 741% — not
plausible, and not monotone in *k*. Root cause was not the strategy: 865
stock-days carried |return| > 50%, topping out at **+337,900%**, which are
reverse-split and delisting artifacts, not returns. Repair: drop the 30 symbols
with more than five such days, mask the remaining 474 artifact stock-days.

Gate re-run, and this time it passes:

| k | 1 | 5 | 20 | 50 | 150 | 626 |
|---|---|---|---|---|---|---|
| ann. vol | 53.5% | 35.6% | 30.2% | 28.1% | 26.1% | 24.9% |

Monotone decreasing, plausible magnitudes. Only then was any strategy run. This
is the harness-before-features rule doing its job — the first version of this
experiment would have produced a confident answer from garbage.

## 2. The dose-response: flat

81,203 trades across 246 baskets, frozen rules, matched control per basket,
date-clustered inference:

**Wide-stop geometry (2.0 / 1.0)**

| k | trades | win | net R:R | excess | t | held-out 2015+ |
|---|---|---|---|---|---|---|
| 1 | 8,139 | 61.5% | 1:0.67 | +0.0137 | 0.83 | −0.0022 (t=−0.10) |
| 5 | 7,704 | 61.8% | 1:0.80 | +0.0009 | 0.06 | +0.0043 (t=0.22) |
| 20 | 5,067 | 61.1% | 1:0.93 | −0.0081 | −0.65 | −0.0277 (t=−1.92) |
| 50 | 4,143 | 61.3% | 1:0.97 | +0.0023 | 0.18 | +0.0009 (t=0.06) |
| 150 | 3,059 | 62.2% | 1:1.00 | +0.0013 | 0.14 | −0.0011 (t=−0.09) |

**1:2 geometry** is the same story — excess between −0.032 and +0.028, no *t*
above 1.08 anywhere, no trend in *k*.

**The diversification hypothesis is rejected.** Making an instrument more
index-like does not restore the edge.

One real secondary finding worth keeping: net R:R at the wide-stop geometry
improves steadily with diversification, 1:0.67 → 1:1.00, while the win rate
holds near 61%. Diversification genuinely does bend the frontier — a smoother
series reaches a fixed target more often before a fixed stop. But the random
control gains exactly the same amount, so it buys **payoff geometry, not edge**.
That is a useful thing to know and it is not a trading signal.

## 3. The self-audit — applying iteration 4's standard retroactively

The whole programme was one search. Counted from the logs, **406 configurations**
were evaluated across five iterations. Under the null, the expected *maximum*
t-statistic across 406 trials is **2.99**. Anything below that is what a search
this wide produces from noise.

| Result | t | n | verdict |
|---|---|---|---|
| SPY daily Tier B, full sample | **3.54** | 267 | **clears, by 0.55** |
| SPY daily Tier B, test 2016-2026 | 2.92 | 117 | does not clear |
| SPX minute, best OOS | 1.01 | 77 | does not clear |
| Fleet, 652 stocks, excess vs control | −0.07 | 74,416 | does not clear |
| Fleet vol-gradient, lookahead-free | −0.09 | 10,993 | does not clear |
| Synthetic index dose-response, best | 1.08 | 3,886 | does not clear |

The SPY daily result has a raw p of 0.0002. **Adjusted for the search, it is
about 0.08** — roughly an 8% chance of seeing a *t* that large somewhere in a
programme this wide even if nothing worked at all. That is not nothing, and it
is not a discovery either. It is a result I would keep on a watchlist and paper
trade, not one I would size up on.

I should have counted configurations from iteration 1. Doing it only now means
the earlier reports overstated their own significance, and this table is the
correction.

## 4. Closing the loop

| Done-statement | Verdict |
|---|---|
| 1. ≥200 OOS trades, ≥1:2 net R:R, ≥55% win | **FAIL** across daily, minute, multi-day, 652 stocks, 246 synthetic indices |
| 2. ≥+0.15R over control, CI excluding 0 | **FAIL** — best is SPY at +0.12R, which does not clear the deflated bar |
| 3. <35% degradation, plateau | Only SPY passes, and only before deflation |
| 4. 2× cost stress | SPY survives; nothing else got that far |
| 5. Reproducible, config count stated | **PASS** — 406, now counted honestly |
| 6. Split reporting | **PASS** |

**The loop is closed.** Five iterations, three instruments classes, two
resolutions, four data sources, 406 configurations. The win-rate/payoff frontier
has been measured five separate ways and it is the same curve every time:
~61–73% at roughly 1:0.6–1:1.0, or ~36–44% at 1:1.75–1:1.9. Nothing sits at 55%+
and 1:2. That is not a limitation of the search; it is a property of the
instruments.

## 5. What is actually left

**One test, and it needs one input I cannot get here.** Real daily OHLC for
20 index ETFs — QQQ, IWM, DIA, MDY, RSP, EFA, EEM, and the nine sector SPDRs —
through `fleet_worker.py` unchanged. If the wide-stop edge shows up at +0.05R or
better across 15 of 20 genuine index ETFs with clustered inference, then SPY was
index-specific and real, and the deflated p of 0.08 stops mattering because it
becomes an out-of-sample replication rather than another draw from the same
search. If it does not, SPY was luck and the honest answer is that there is no
system here.

That is a ten-minute job with the data in hand, and it is the only thing that
would move the conclusion. Everything else I can do from here would be searching
the same noise with a 407th configuration.

**Recommendation: stop iterating and go get that data.** Continuing without it
is the anti-pattern the framework calls infinite perfectionism, and I would
rather say so than produce a sixth iteration that looks like progress.
