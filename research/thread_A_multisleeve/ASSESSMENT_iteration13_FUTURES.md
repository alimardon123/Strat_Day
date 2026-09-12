# ASSESSMENT — iteration 13: intraday at futures cost, and the full horizon table

Three things this iteration: an intraday sleeve tested at futures friction, the
weekly/monthly statistics you asked for, and an honest accounting of what
futures and options do and do not change.

---

## 1. The intraday sleeve — failed, in an interesting way

**S11 INTRADAY MOMENTUM.** The published result (Gao, Han, Li & Zhou, 2018) is
that the first half-hour return predicts the last half-hour return, driven by
infrequent-rebalancing traders and late-day informed flow. It holds a position
30 minutes a day, so it should be nearly uncorrelated with everything in the
daily portfolio. Tested on SPX 1-minute data, 2005–2020, at **0.35 bp per side**
(one ES tick plus commission on ~$200k notional).

**The correlation came out negative, not positive:**

| | first-30min vs last-30min correlation |
|---|---|
| Full 2005–2020 | **−0.069** |
| Train (<2013) | −0.051 |
| Test (2013+) | **−0.106** |

Consistently negative in both halves. So I tested the reversal version with the
sign chosen on train data only. **It also loses:** train Sharpe −0.43, test −0.07.

Both directions losing is not a contradiction — it is the diagnosis. Momentum
and reversal returns sum to exactly −2 × cost, so when both are negative the
gross effect is smaller than the friction. At |correlation| ≈ 0.07, it is. Even
at 0.35 bp per side, the cheapest execution available to a retail futures trader,
there is nothing there.

I also found a quartile of opening-move sizes where reversal shows Sharpe 0.77 —
on the test set, after the fact, in one of four buckets. That is noise-mining and
I am not pursuing it.

Correlation of the intraday sleeve to every daily sleeve ran between −0.035 and
+0.036 — genuinely uncorrelated, which is exactly why I wanted it to work. It
just has no edge to contribute.

## 2. What futures actually change (and it is one real thing)

In iteration 8 I flagged that the levered variant "assumes free leverage, which
does not exist." **With futures it essentially does** — margin, not borrowing. So
that caveat is now removed, and the levered system is a real instrument rather
than a hypothetical:

| | CAGR | vol | Sharpe | max DD |
|---|---|---|---|---|
| **6-sleeve, levered 3.18× to SPY's vol** | **16.80%** | 19.6% | **0.89** | **−22.3%** |
| SPY buy & hold | 7.37% | 19.6% | 0.46 | −56.5% |

**Same volatility, 2.3× the return, 40% of the drawdown.** That is the single
most useful consequence of trading futures rather than ETFs, and it is worth more
than any sleeve I have added since iteration 8.

What futures do *not* change: friction on the sleeves themselves. ES round-trip
is ~0.6–0.8 bp against the 2 bp I charged the ETF sleeves, so cheaper — but the
sleeves rebalance monthly and weekly, not daily, so the saving is small in
absolute terms. It does not resurrect anything that failed on cost grounds.

## 3. Options — what I can and cannot tell you

No options data is reachable from this environment, so I cannot backtest an
options overlay and will not pretend to. What the measured properties of the
system do imply:

- The system runs at **6.1% annualised volatility** with a −7.6% worst drawdown.
  Selling premium against it (covered calls, put spreads) would add **negative
  skew** to a portfolio whose quarterly skew is currently −0.07, i.e. neutral.
  That trades a metric you can measure (drawdown) for one you cannot (payoff
  ratio, per iteration 12). I would not.
- Buying options is the reverse trade and is the one thing that would genuinely
  add positive skew, which iteration 12 showed the portfolio lacks and which the
  Donchian attempt failed to supply. But long premium bleeds, and whether it nets
  positive depends entirely on implied-vs-realised volatility — which is precisely
  the data I do not have.
- **Futures are the better fit for this system.** It is a volatility-targeted,
  leverage-hungry, low-drawdown portfolio. Futures give it leverage cheaply and
  linearly. Options would change its shape in ways I cannot measure here.

## 4. The full horizon table

**6-sleeve system, unlevered (6.1% vol):**

| Horizon | n | hit % | payoff | mean % | best % | worst % | hit 95% CI |
|---|---|---|---|---|---|---|---|
| Daily | 2,924 | 54.7 | 1:0.98 | 0.02 | 2.18 | −3.92 | [53, 56] |
| Weekly | 606 | 60.9 | 1:0.92 | 0.10 | 3.05 | −4.74 | [57, 65] |
| Monthly | 140 | 64.3 | 1:1.14 | 0.45 | 4.43 | −3.92 | [56, 72] |
| Quarterly | 47 | 72.3 | 1:1.44 | 1.35 | 7.59 | −5.08 | [60, 85] |
| Annual | 12 | 83.3 | 1:5.33 | 5.41 | 17.43 | −2.44 | [58, 100] |

**Levered 3.18× (19.6% vol, futures-implementable):**

| Horizon | hit % | payoff | mean % | best % | worst % |
|---|---|---|---|---|---|
| Daily | 54.7 | 1:0.98 | 0.07 | 6.94 | −12.46 |
| Weekly | 60.6 | 1:0.93 | 0.33 | 9.91 | −14.86 |
| Monthly | 63.6 | 1:1.16 | 1.42 | 14.62 | −12.53 |
| Quarterly | 72.3 | 1:1.41 | 4.28 | 25.85 | −15.83 |
| Annual | 75.0 | 1:6.95 | 17.92 | 63.81 | −8.13 |

**And the benchmark, which is the most instructive row in this report:**

| Horizon | SPY hit % | SPY payoff | SPY worst % |
|---|---|---|---|
| Weekly | 57.1 | 1:0.92 | −19.80 |
| Monthly | **65.7** | 1:0.81 | −16.52 |
| Quarterly | **74.5** | **1:0.68** | **−22.20** |
| Annual | **91.7** | **1:0.34** | **−38.28** |

**SPY buy-and-hold has a higher hit rate than the system at every horizon from
monthly out — and a worse payoff ratio at every one, with three to five times the
worst-period loss.** At the annual horizon SPY wins 91.7% of years at 1:0.34.
This is the clearest possible demonstration that a high win rate, on its own,
tells you almost nothing. It is the metric buy-and-hold optimises for free.

## 5. A note on trading it daily

This system does not produce daily decisions. Its sleeves rebalance monthly
(BAB, TSMOM, XSMOM, overnight tilt) or weekly, and the DipScore sleeve fires
about ten times a year. The 54.7% daily hit rate is what you would **observe**
each day, not a decision you would **make**. If you want a system that gives you
a trade every day, that is a different specification — and thirteen iterations
say the daily-decision versions are exactly the ones where costs win.

## 6. Where things stand

**Recommended: the 6-sleeve system, levered with futures to your risk
tolerance.** 16.8% CAGR at SPY-matched volatility, −22.3% max drawdown, Sharpe
0.89 (95% CI [0.21, 1.57]), 72.3% winning quarters at 1:1.44, worst quarter
−15.8% levered / −5.1% unlevered.

Unchanged priorities: more data first (the CI is still the binding constraint),
then uncorrelated sleeves, never more conditioning. The intraday branch is now
closed — tested at daily, minute, and 30-minute granularity, at ETF and futures
cost, and it has failed at every one.
