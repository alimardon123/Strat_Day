# Part 10 — The Signal Slot Is Filled

## Where it came from

You asked me to search rather than re-test. I found *Market Intraday Momentum* (Gao,
Han, Li & Zhou, JFE 2018) and its extension *Hedging Demand and Market Intraday
Momentum* (Baltussen, Da, Lammers & Martens, JFE 2021). The second paper identifies the
mechanism: **options market makers and leveraged ETFs are structurally short gamma, and
must hedge in the direction of the day's move before the close.** That is a forced flow —
the exact structural story this project said was needed, and it shows up in price
without options data.

A 2024 follow-up found the unconditional version disappeared post-publication except in
high-volatility regimes. Part 7 already established that prior-close VIX forecasts the
regime. So the test was directed, not a fishing expedition.

## The rules, in plain language

1. At 15:30 ET, compute the move from **yesterday's close to now**.
2. Only trade if **yesterday's VIX close > 17.06** AND **|move| > 0.665%**.
   (Both thresholds fixed on 2010–2018, applied unchanged after.)
3. If the move is up, **go long. If down, go short.**
4. **Exit at the 16:00 close.** Flat every night.

That's it. One trade, 30 minutes, ~45–65 qualifying days a year.

## The evidence

| | n | net %/trade | win % | net Sharpe | bootstrap p |
|---|---|---|---|---|---|
| **Discovery 2010–2018** | 337 | **+0.0645** | **58.5** | **+2.50** | **0.0003** |
| **Holdout 2019–2020** (different feed, post-publication) | 85 | **+0.0975** | 54.1 | **+1.67** | 0.135 |
| *Opposite condition (low VIX, small move)* | 299 | −0.0287 | 41.1 | −4.44 | 1.00 |

The holdout p is underpowered at 85 observations, but the effect is the **same sign and
larger**. The opposite condition is dead, as the mechanism predicts. Cost is already
subtracted throughout.

Against the Part 6 law: ~50 trades/year requires gross Sharpe ~0.06 to break even.
Cleared by a factor of forty.

## Year by year — read this before the Sharpe

| year | days | net %/trade | win % | annual % | max DD % |
|---|---|---|---|---|---|
| 2010 | 5 | +0.026 | 80.0 | +0.13 | −0.02 |
| **2011** | 111 | +0.129 | 65.8 | **+14.32** | −1.68 |
| 2012 | 56 | +0.016 | 50.0 | +0.87 | −2.04 |
| 2013 | 14 | +0.115 | 71.4 | +1.61 | −0.58 |
| 2014 | 17 | +0.082 | 64.7 | +1.38 | −0.53 |
| 2015 | 45 | +0.115 | 53.3 | +5.18 | −0.68 |
| 2016 | 36 | −0.028 | 50.0 | −1.00 | −1.38 |
| *2017* | *0* | — | — | *stood aside* | — |
| 2018 | 53 | −0.015 | 50.9 | −0.77 | −4.54 |
| 2019 | 34 | −0.035 | 52.9 | −1.20 | −1.05 |
| **2020** | 51 | +0.186 | 51.0 | **+9.49** | −5.79 |

**7 of 10 years positive. Total +30.0% over 422 trades, unleveraged.**

Two things the aggregate hides:

- **2011 and 2020 are +23.8 of the +30.0.** The other eight years net about +6%. This
  is a strategy that pays mostly in crises and roughly breaks even otherwise.
- **The worst trades live inside the best years.** Five worst: −3.49% (Mar 18 2020, VIX
  76), −2.34% (Mar 25 2020), −1.90% (Dec 27 2018), −1.12% (Sep 14 2011), −1.05% (Mar 23
  2020). The regime that makes it work is the regime that makes it hurt.

## Leverage

| leverage | annual | worst trade | max drawdown |
|---|---|---|---|
| 1× | +3.0% | −3.5% | −7.0% |
| 3× | +9.0% | −10.5% | −21.0% |
| 5× | +15.0% | −17.5% | −34.9% |

Unleveraged it's a high-Sharpe, low-return strategy — a 30-minute exposure ~50 days a
year simply can't compound much. Levered, it's a real strategy with a real tail. A
30-minute hold protects you from overnight gaps. It does not protect you from a VIX-75
half-hour.

## Fit to your constraints

| constraint | verdict |
|---|---|
| day trading only | **✅ flat at 16:00 every day** |
| prop-firm daily loss limit | ⚠️ at 3×, a −10% day exists in-sample; size to the limit, not to the Sharpe |
| 0DTE expression | ✅ natural fit — ITM 0DTE bought at 15:30 expires at the exit |
| VIX preparation | ✅ the VIX filter *is* the regime detector |

For a 4% daily limit at 1× the worst observed day is −3.5% — inside the limit but with no
margin. At 2× it isn't. The honest sizing under a prop mandate is **~1×, targeting about
3% a year on notional**, and knowing that March 2020 is in the sample and 2008 is not.

## Honest status

This is the first signal in seventeen studies that:

- is peer-reviewed twice in the top finance journal
- has a forced-flow mechanism rather than a pattern
- replicates on this data at p = 0.0003 net of cost
- holds direction and size out of sample on a different feed post-publication
- is negative when the mechanism says it should be
- is day-tradeable, flat at the close, at a frequency the cost law permits

It is also small, regime-dependent, crisis-loaded, and negative in three of the last five
sample years. It is an edge, not a loophole. The difference is the whole thing.

---

*Historical research, not financial advice. Twenty-two tests were run in this step; the
discovery result clears Bonferroni, the holdout does not on its own.*
