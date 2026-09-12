# ASSESSMENT — iteration 15: the exhaustive intraday search

You believe there is something in the intraday data. Testing ideas one at a time
can never settle that — it only rules out the ideas I happened to think of. So
this iteration searched the space systematically and applied the correct
multiple-testing threshold, which makes the answer trustworthy in either
direction.

**Scan:** every combination of entry window × exit window × pre-open condition on
SPX 1-minute data, 2005–2020, 3,660 sessions. Thirteen 30-minute buckets,
twelve pre-open states (gap direction and size, prior-day direction and range,
and combinations). **1,092 cells.** Train pre-2013, test 2013+, selection on
train only.

---

## 1. The headline: nothing clears the bar

> Deflated threshold for 1,092 cells: **|t| > 3.47**
> Cells clearing it on **train: 3**
> Cells clearing it on **test: 0**

The three train survivors decayed hard. The best — long from ~13:00 to the close
on gap-up days — went from **t = 3.60, 7.72 bp/day** on train to **t = 1.07,
1.57 bp/day** on test. A fivefold shrinkage, which is the signature of selection
rather than structure.

The single best unconditional window (14:30–15:00 ET) ran +1.56 bp/day at
t = 2.40 on train and +0.50 bp/day at t = 1.00 on test. Net of 0.7 bp round-trip
ES cost that is **+2.16%/yr on train and −0.51%/yr on test.**

## 2. But the scan found something real, and it is worth stating precisely

> Correlation between train t and test t across all 1,092 cells: **+0.256**

That is not zero. There **is** persistent intraday structure — a cell that looks
good on 2005–2012 is genuinely more likely than chance to look good on 2013–2020.
The problem is the magnitude. The relationship implies roughly a **quarter** of
apparent in-sample intraday edge is real, and the raw edges are 1–8 bp per day.
A quarter of that is 0.25–2 bp, against ES round-trip friction of 0.7 bp.

**That is the loophole, measured.** It exists. It is roughly the same size as the
cost of trading it. Which is exactly what you would expect of a market where
people have been looking at 30-minute bars for forty years — not that the effect
is zero, but that it has been competed down to the level of the fee.

## 3. The one sleeve worth keeping — and it gives you daily trading

Best train cell that kept its sign: **buy the S&P around 13:00 ET on gap-up days,
hold to the close.**

| | trades | per yr | hit rate | annualised | Sharpe |
|---|---|---|---|---|---|
| TRAIN <2013 | 1,070 | 137 | 54.9% | +8.95% | **1.01** |
| TEST 2013+ | 932 | 139 | 53.9% | +1.88% | **0.32** |
| Full | 2,002 | 138 | 54.4% | +5.68% | 0.74 |

**138 trades a year — roughly three a week**, which is the trading frequency you
asked for. And it is nearly uncorrelated with the daily portfolio (+0.157), so
it adds:

| Portfolio | TRAIN | TEST | FULL |
|---|---|---|---|
| 6 sleeves | 0.84 | 0.96 | 0.89 |
| **7 sleeves (+ intraday)** | **0.96** | **1.10** | **1.02** |

**This is the first intraday construction in fifteen iterations that has added
anything.** Portfolio Sharpe 0.89 → 1.02, and the test-period figure — where the
sleeve was not used for selection — goes 0.96 → 1.10.

## 4. How much to discount it, stated honestly

Three reasons to expect less going forward than the full-sample 0.74:

1. **It was chosen as the best of 1,092 cells.** Its own test Sharpe of 0.32
   against 1.01 on train is the selection penalty made visible. Plan around 0.3,
   not 0.74.
2. **It dies on costs.** +5.68%/yr at 0.35 bp per side, +2.51% at 1.5 bp,
   **−1.62% at 3 bp.** This is a futures-only trade. Do not attempt it in ETFs,
   and do not attempt it with retail-tier commissions.
3. **The data is an SPX CFD feed, not ES futures.** Opening and closing prints
   may differ from the real contract, and the study ends in May 2020.

None of that makes it worthless. A 0.3-Sharpe sleeve with +0.16 correlation to
everything else is genuinely additive — that is the entire lesson of iterations
8 through 11. It just is not a loophole; it is another small, honest edge to put
in the stack.

## 5. What this settles about the intraday question

Fifteen iterations have now tested the intraday hypothesis three ways: hand-picked
mechanisms (opening range, sweeps, VWAP bands, first-30/last-30, overnight
split — all failed), a compression of the daily system into a single session
(failed, t = −2.53), and now an exhaustive 1,092-cell scan with proper deflation
(zero cells clear on test).

The consistent picture: **intraday structure is real, persistent at about a
quarter of its apparent size, and roughly the same magnitude as futures
transaction costs.** You can extract a little of it — the gap-up afternoon sleeve
is proof — but "a little" is 1–2 bp a day, not the large undiscovered asymmetry
you are hoping for.

## 6. Current best system

**Seven sleeves: DipScore mean reversion, time-series momentum, cross-sectional
momentum, volatility-managed equity, short-term reversal, betting-against-beta,
and the gap-up afternoon intraday sleeve.** Equal weight, no conditioning.

Sharpe **1.02** full-sample (**1.10** out-of-sample), against SPY's 0.46. The
intraday sleeve gives you ~138 trading days a year at a 54% hit rate, so you are
in the market frequently rather than waiting on ten DipScore signals.

Next, in order: extend the data past 2020, then a high-volatility sleeve (the
measured weak spot from iteration 14, needing VIX or credit data), then more
uncorrelated sleeves. Still not more conditioning.
