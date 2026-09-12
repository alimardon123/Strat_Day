# SPY DipScore v1 — what 26 years of SPY daily bars actually support

**Data:** SPY daily OHLCV, 2000-01-03 → 2026-03-20, 6,593 bars. Unadjusted for
dividends. Cross-checked against an independent dividend-adjusted source over
2010–2019: daily-return correlation 0.982, and 80% of the residual gaps above
0.2% land on ex-dividend days, which is what you would expect. Six bars in
2007–08 had `high < open` by a cent or two; those were repaired to
`high = max(o,h,c)`, `low = min(o,l,c)`.

**Split:** train 2000–2015 (16.0y), test 2016–2026 (10.2y). Every parameter was
chosen on train and the test period was scored **once**.

**Execution model, deliberately pessimistic:** signals use data through bar *t*'s
close, entry is bar *t+1*'s open. Stop and target are ATR-multiples fixed at
entry. On daily bars the intraday path is unknown, so **if a bar's range touches
both the stop and the target, the trade is booked as a stop.** Gaps through the
stop exit at that open. Costs 1 bp per side. No overlapping positions.

---

## 1. The headline finding: your two targets are mutually exclusive

You asked for 60–70% win rate *and* roughly 1:2 risk-reward. Across 239 tested
configurations on the train period, here is the best achievable edge at each
win-rate band:

| Win rate band | Best config's R:R | Avg R per trade |
|---|---|---|
| 40–50% | 1 : 1.96 | +0.36 |
| 50–55% | 1 : 1.69 | +0.42 |
| 55–60% | 1 : 1.58 | +0.42 |
| 60–65% | 1 : 1.15 | +0.29 |
| 65–70% | 1 : 0.91 | +0.21 |
| 70–75% | 1 : 0.92 | +0.20 |
| 75–80% | 1 : 0.80 | +0.23 |

Win rate and R:R sit on a frontier. Nothing in 26 years of SPY reaches 65% wins
at 1:2. That combination is +0.95R per trade; at daily frequency it compounds to
roughly +237R per year, which is not a thing that exists in a liquid index ETF.

I tested it directly anyway. The same signal run at 1:2 geometry
(stop 1.0×ATR, target 2.0×ATR): 44.1% win on train with a healthy edge, then
**38.3% win and *negative* edge versus random on test**. The high-win-rate
geometry of the same signal replicated cleanly. So the answer isn't "1:2 is
harder" — it's that on this instrument the 1:2 version of the edge did not
survive out of sample at all.

## 2. The trap you were about to walk into

A long SPY strategy with a wide stop and a near target wins **~65% of the time
with no setup logic whatsoever**. Random entry dates, uptrend filter only, same
2.0×ATR stop and 1.0×ATR target:

```
RANDOM-ENTRY CONTROL   n=3192   win = 65.1%   R:R = 1:0.60   avg = +0.024R   PF = 1.11
```

That is the single most important number in this study. If you build something
that wins 68% and declare victory, you have built a slightly worse version of
throwing darts. Every result below is reported as **excess over that control**,
because that is the only part that is actually a setup.

## 3. What did survive: DipScore Tier B

A confluence score of pullback conditions inside a confirmed uptrend
(close > SMA200 and SMA200 rising over 20 days):

| Factor | Weight |
|---|---|
| RSI(2) < 10 | +0.25 |
| RSI(2) < 5 (additional) | +0.10 |
| IBS < 0.20 (closed on the day's low) | +0.20 |
| New 10-day low | +0.20 |
| 3+ consecutive down closes | +0.15 |
| Close below SMA50 (pullback has depth) | +0.10 |
| Realised-vol percentile < 0.80 (calm tape) | +0.10 |
| Realised-vol percentile > 0.90 (crisis) | **−0.15** |

Trade when score ≥ 0.35 (Tier B). Buy next open. Stop 2.0×ATR(14),
target 1.0×ATR(14), time-stop after 5 bars.

| | Trades | Per yr | Win | R:R | Avg R | PF | Sharpe | t | Max DD |
|---|---|---|---|---|---|---|---|---|---|
| **Train 2000–2015** | 150 | 9.4 | 71.3% | 1:0.60 | +0.109 | 1.49 | 0.54 | 2.16 | −12.2% |
| **Test 2016–2026** | 117 | 11.5 | 76.1% | 1:0.58 | +0.160 | 1.83 | 0.91 | 2.92 | −5.4% |
| Random control (test) | 1427 | 9.3 | 66.5% | 1:0.58 | +0.039 | 1.15 | 0.18 | 2.23 | −23.2% |

**Excess over random on test: +0.121R per trade.** The edge got *stronger* out of
sample rather than degrading, which is unusual and is itself a reason for
caution, not celebration — see §6.

Full sample 2000–2026: 267 trades, 73.4% win, +0.131R average,
bootstrap 95% CI on mean R = **[+0.058, +0.199]**, P(edge ≤ 0) < 0.001.
Total +35.0R over 26 years. Longest losing streak: 5.

Exit mix: 182 target, 48 stop, 37 time-stop. Average stop distance 2.1% of price.

## 4. Robustness checks

**Walk-forward, year by year (threshold fixed, only the data window moves):**
18 of 21 traded years profitable. Worst year −9.3% (2010). Median +4.7%.
2008 produced **zero trades** — the trend filter kept the system out of the
crash entirely, which is where most dip-buying systems die.

**Parameter neighbourhood on test** (avg R per trade): a smooth plateau across
stop 1.5–3.0 × target 0.75–2.0, not a single hot cell. Hold period 4–10 bars all
land between +0.15 and +0.17R. Score threshold 0.35–0.40 is a flat shelf.
This is what a real effect looks like rather than a fitted one.

**Cost stress:** at 1 bp/side, +0.139R. At 5 bp, +0.099R. At 10 bp/side the edge
falls to +0.048R and t drops to 1.56 — i.e. the strategy is real but not
robust to bad execution. On SPY at a penny spread you are fine; do not port this
to anything with a wide book.

**Multiple-testing discount:** 26 of 239 train configs beat random at z > 2,
against ~5.5 expected by chance. There is signal in the pile, but roughly a
fifth of those 26 are noise. That is why the test period was scored once.

**Regime split (full sample):** the edge lives almost entirely in the *range*
regime (n=230, +0.142R, t=3.52). In the *trend* regime it is flat (n=23,
+0.001R). I tested adding a "skip trend regime" filter — it **hurt** out of
sample (+0.160 → +0.129R), so I left it out. That's an honest null result;
the train-period observation didn't generalise.

**Shorts:** short setups in confirmed downtrends looked strong on train
(z up to 3.0) — because train contains 2000–02 and 2008. They are not included.
Expect them to fail in a bull decade, and treat those train numbers as a
regime artefact.

## 5. What this does *not* deliver

- **It is not a daily setup.** ~10 trades a year at Tier B. Loosening the score
  threshold toward daily frequency destroys the edge on a clean gradient:

  | Trades/yr | Win | Avg R | Max DD |
  |---|---|---|---|
  | 6.7 | 73.3% | +0.145 | −8.1% |
  | 10.2 | 73.4% | **+0.131** | −12.2% |
  | 17.6 | 67.9% | +0.065 | −16.7% |
  | 33.2 | 65.2% | +0.048 | −20.5% |
  | 51.5 | 63.7% | +0.028 | −63.0% |

  At near-daily frequency you converge to the random-entry control. Wanting a
  setup every day and wanting a high-probability setup are the same tension as
  wanting 70% wins and 1:2 — you can have one.

- **It is not 1:2 R:R.** It is 1:0.58. You win often and win small. Position
  sizing carries this strategy, not the payoff ratio.

- **The expectancy is modest.** +0.13R per trade × ~10 trades/year = **~1.3R per
  year**. At 1% risk per trade that is ~1.3% a year before considering that your
  capital sits idle the rest of the time. This is a satellite overlay or a
  timing filter for deploying cash, not a standalone income strategy. Buy-and-hold
  beat it on raw return over the same period.

## 6. What I'd want to see before trading it

1. **Test on 5-minute or 1-minute bars.** Daily bars force the pessimistic
   same-bar assumption; intraday data would tell you the true stop/target
   sequencing and probably improves reported results. It would also let you build
   the genuinely intraday setup you originally asked about.
2. **Cross-asset check** on QQQ, IWM, EFA. ATR-normalisation should carry it. If
   the edge only exists on SPY, it's fitted.
3. **Investigate why test beat train.** 2016–2026 was an unusually strong
   dip-buying regime (persistent Fed put, fast V-recoveries). The train number
   (+0.109R) is the more conservative estimate to plan around, not +0.160R.
4. **Paper-trade 30 signals** before committing capital — roughly three years at
   this frequency, which tells you something about how slow validation is here.
5. **Re-examine the shorts on 2000–2015 only as a bear-market hedge**, sized
   small, not as a symmetric complement.

## Files

- `SPY_DipScore_v1.pine` — Pine Script v6 strategy, mirrors the Python exactly.
  Tiered A/B/C markers, regime tinting, filter-mode hidden plots, alerts.
- `spy_dipscore_research.py` — single reproducible script; run it against any
  SPY daily CSV with `date,open,high,low,close,volume` and it regenerates the
  train/test/control table above.
