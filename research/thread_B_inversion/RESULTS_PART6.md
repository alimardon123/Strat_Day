# Part 6 — Structural Flow, and the Law Behind All Twelve Studies

## Quadrant 4 tested: structural flow

Premise: on known calendar dates, large participants must trade regardless of price.
Options expiry, month-end pension rebalancing, quarter-end, triple witching. The dates
are known years in advance — no forecasting required.

32 tests (8 event types × 4 intraday legs), SPX 2010–2018, 1,934 sessions.

| result | |
|---|---|
| Bonferroni-significant, net-positive, sign-consistent | **0 of 32** |
| nominally p<0.05 | 1 (expected by chance: 1.6) |

And the premise fails at the source:

| day type | mean intraday range |
|---|---|
| option expiry | **0.877%** |
| triple witching | 0.907% |
| month-end | 0.909% |
| **normal day** | **0.992%** |

Event days are **calmer** than normal days, not richer in opportunity. Whatever forced
flow exists is absorbed without leaving a tradeable footprint at daily granularity.

---

## The law

Every intraday study died at the same wall. Here it is in closed form:

> **cost drag on annual Sharpe = cost per trade × trades per year ÷ annual volatility**

Cost drag scales **linearly with trade frequency**. Signal quality does not appear in the
equation. SPX annual vol ≈ 15.9%.

### Required gross Sharpe just to break even

| trading style | trades/yr | CFD (0.50) | ES (0.33) | tight retail (0.15) |
|---|---|---|---|---|
| swing, 2/week | 104 | 0.19 | 0.13 | 0.06 |
| 1 round trip/day | 252 | 0.47 | 0.31 | 0.14 |
| day trading, 4/day | 1,008 | 1.88 | 1.24 | **0.56** |
| active, 10/day | 2,520 | 4.70 | 3.10 | 1.41 |
| scalping, 20/day | 5,040 | 9.40 | 6.20 | 2.82 |
| *this study's breakout* | *9,776* | *18.23* | *12.03* | *5.47* |

For reference: **Renaissance Medallion is estimated at gross Sharpe 2–3** — with
proprietary data, co-located execution and institutional costs.

Scalping 20×/day on a CFD requires **9.4** — roughly four Medallions, spent entirely on
covering the spread.

### Every result in this study, explained by one number

| strategy | trades/yr | needed gross SR | outcome |
|---|---|---|---|
| breakout | 9,776 | **12.02** | died |
| gap+ORB | 1,600 | 1.97 | died (had ~0.3) |
| overnight hold | 252 | 0.31 | died (0.27, and buy-hold gives 0.77) |
| structural flow | 40 | 0.05 | died — no effect existed |
| **VRP** | **12** | **0.01** | **survived, net SR 2.10** |

Twelve studies, one variable. The VRP didn't win because its signal was better. It won
because it pays the toll **twelve times a year instead of ten thousand.**

---

## So: is day trading runnable?

Yes — but the equation dictates the configuration, and it is not the one most day traders
run.

**Viable spec:**

| parameter | requirement | why |
|---|---|---|
| frequency | **2–4 trades/day max** | above this the required Sharpe exceeds elite-fund territory |
| cost | **tightest available** (~0.15 pts) | this is the single highest-leverage variable in the entire study |
| entry | **limit orders** | step 8: largest single improvement measured anywhere |
| target gross Sharpe | **0.6–0.9** | achievable; 1.5+ is not, for retail on price data |
| instrument | liquid futures, not CFDs | cost difference alone moves the bar 3× |

At 4 trades/day with tight costs the bar is **gross Sharpe 0.56.** That is a real,
reachable target — unlike the 12.03 the original breakout needed.

**Non-viable spec** — and this is what most retail day trading looks like:
10–20 trades/day on a CFD requires gross Sharpe 4.7–9.4. No amount of signal research
closes that gap, because signal quality isn't the term that's failing.

## The honest summary of all thirteen studies

- Market structure is **real**: 35 of 282 hypotheses beat chance; overnight drift held in
  4 of 4 markets; stop cascades hit t = +9.4; the VRP was positive in 9 of 9 years.
- Almost none of it is **harvestable at high frequency**, because the toll scales linearly
  with frequency and the edge does not.
- The one thing that worked worked by holding for 21 days.
- The biggest single improvement available anywhere was **execution** (limit vs market),
  not signal.
- The most dangerous moment in the whole study was a Sharpe of 7.2 that turned out to be a
  four-hour look-ahead.

If you want a day-trading system, the design constraint is now explicit: **build for 2–4
trades a day at the lowest cost you can access, and target a gross Sharpe under 1.**
Everything else in the research budget should go to execution and cost, not signals.

---

*Historical research, not financial advice.*
