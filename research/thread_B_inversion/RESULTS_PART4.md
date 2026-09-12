# Part 4 — Changing the Axis, and the Sharpe 7.2 That Wasn't

Rather than search for another intraday signal, this part changes the dimension:
**holding period**, **time zone**, and **cross-section**.

## A. Holding period — overnight vs intraday

The documented anomaly: equity returns accrue overnight; the intraday session
contributes little. It replicates cleanly here, in all four markets:

| market | overnight %/day | intraday %/day | gross SR (overnight) | **net SR after daily cost** |
|---|---|---|---|---|
| SPX | +0.0244 | +0.0147 | +0.77 | **+0.27** |
| DAX | +0.0184 | +0.0111 | +0.31 | +0.15 |
| EuroStoxx | +0.0980 | +0.0039 | +0.36 | +0.25 |
| Nikkei | +0.0523 | +0.0035 | +0.63 | **+0.03** |

**The effect is real — overnight beats intraday in 4 of 4 markets.** And it is still not
a strategy. Buy-and-hold (`total`) delivers Sharpe +0.77 on SPX with *no daily trading*;
the overnight-only version delivers +0.27 after paying a round trip every single day.
You'd trade 252 times a year to underperform doing nothing. Nikkei's +0.63 collapses to
+0.03.

Even the "fewer, bigger trades" lever — one round trip per day instead of 9,776 total —
isn't fewer enough.

## B. Time zone — and the most instructive failure in the study

Initial result: sign of the prior US session applied to the DAX overnight gap.

**Sharpe +7.20. p = 0.00000. Net +0.34%/day.**

That is not a discovery. That is a bug, and the size of the number is what gives it away.

**The bug:** to capture the DAX gap for day D you must be positioned at the DAX close on
D−1, which is **08:32 ET on D−1**. The US session on D−1 does not open until **09:32 ET**.
The DAX overnight window (08:32 ET D−1 → 02:02 ET D) *entirely contains* the US session
being used to predict it. I was measuring the same hours twice and calling one of them a
forecast.

Rerun with an explicit clock check on every signal:

| market | target | lag | executable? | net %/day | net SR | boot p |
|---|---|---|---|---|---|---|
| DAX | overnight | 1 | **LOOKAHEAD** | +0.3428 | **+7.17** | 0.00000 |
| DAX | overnight | 2 | OK | −0.0203 | −0.39 | 0.607 |
| DAX | intraday | 1 | OK | −0.0157 | −0.35 | 0.716 |
| DAX | intraday | 2 | OK | +0.0051 | +0.11 | 0.428 |
| EuroStoxx | overnight | 1 | **LOOKAHEAD** | +0.1969 | +0.63 | 0.077 |
| EuroStoxx | overnight | 2 | OK | −0.1631 | −0.52 | 0.323 |
| EuroStoxx | intraday | 1 | OK | −0.0477 | −1.04 | 0.376 |
| EuroStoxx | intraday | 2 | OK | −0.0353 | −0.77 | 0.838 |

**Sharpe +7.17 → −0.39.** Executable and significant after correction: **0 of 8.**

This is worth more than any positive result in the study. A look-ahead of a few hours,
in a window nobody would think to check, manufactured a Sharpe of 7. If a backtest ever
shows you a number like that, the number is the evidence of the error.

## C. Cross-section — DAX vs EuroStoxx relative value

Daily return correlation: **0.911**. Fade yesterday's divergence in the spread:

| filter | n | gross %/day | net %/day | net SR | boot p |
|---|---|---|---|---|---|
| all days | 1,992 | −0.0116 | −0.0519 | −2.36 | 0.140 |
| \|z\| > 1.0 | 516 | −0.0173 | −0.0576 | −2.99 | 0.201 |
| \|z\| > 1.5 | 213 | −0.0399 | −0.0802 | −3.98 | 0.072 |

Negative at every threshold, and *more* negative as the filter tightens — the spread
trends rather than reverts. Two legs also means paying the toll twice.

---

## Where nine approaches have landed

| # | approach | result |
|---|---|---|
| 1 | invert a losing strategy | zero → zero |
| 2 | stop-cascade continuation | real (t=+9.4), below cost |
| 3 | regime-conditional polarity | only time-of-day, below cost |
| 4 | 282-hypothesis behavioural sweep | 35 beat chance, **0 survived FDR** |
| 5 | cross-market validation | 72% shrinkage, 0 of 3 confirmed |
| 6 | limit-order execution | biggest gain, adverse selection ate half |
| 7 | overnight/intraday split | real in 4/4 markets, loses to buy-and-hold |
| 8 | time-zone spillover | **Sharpe 7.2 was a look-ahead bug** |
| 9 | cross-sectional spread reversion | negative at every threshold |

Nine independent routes. Every one ended at the same wall, and the wall was cost — never
signal quality. That consistency is not failure to find the trick. It is the measurement
of an equilibrium.

## What I'd say honestly

Effects here were real more often than not. Overnight drift: real. Stop cascades: real.
Gap-plus-breakout momentum: probably real. Behavioural structure in general: real, at
five times chance.

**Every single one was smaller than the cost of harvesting it.** That is not a
coincidence — an anomaly persists precisely until it becomes cheap enough to arbitrage,
so the survivors cluster just under the cost wall by construction.

The lever that would change any of this is not another signal. It is being cheaper,
having data others lack, or trading somewhere less crowded than one liquid index on
price history alone. Everything reachable by anyone with a chart has been reached.

---

*Historical research, not financial advice.*
