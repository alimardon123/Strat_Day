# Minute-level study — code bundle

- `audit.py`   Phase 0: loads the 1-minute source, resolves timezone from the
               tick-volume U-shape, checks OHLC integrity, reports coverage.
- `mh.py`      Phase 2: the harness. Session builder (RTH 09:30-16:00 NY,
               session VWAP + bands, opening range, prior-day levels), the
               path-resolved minute backtester (entry on the NEXT bar's open,
               stop booked on same-bar ties, no overnight carry), the matched
               random-entry control, and the synthetic sanity test.
               Run `python mh.py` to re-verify the harness.
- `strat.py`   Phase 3: the five hypothesis families with their mechanisms.

Harness validation: on a zero-drift random walk the resolved win rate matches
the geometric prior stop/(stop+target) to within 3 points across five
geometries, and the residual negative meanR equals the modelled slippage
divided by the risk distance, exactly.

## Iterations 2-3 (added)

- `md.py`   Multi-session minute-path backtester: a 5-day hold resolved minute
            by minute across sessions, so stop-vs-target sequencing is measured
            rather than assumed.
- `it2.py`  Entry-timing comparison (open / VWAP reclaim / VWAP+high push /
            15:30) on the multi-day DipScore hold, train and test.
- `it3.py`  The ablation: identical signal and geometry under daily-bar
            resolution versus minute-path resolution, plus the tier sweep that
            tests whether the 1:2 result holds at n >= 200.

See BLOCKED.md for the verdict and the power analysis that ends the loop.

## Iteration 5 (added)

- `it5.py`   Panel loader, synthetic equal-weight index construction, frozen
             DipScore, and the backtester used at index level.
- `it5b.py`  The root-cause repair (reverse-split / delisting artifact removal)
             and the volatility gate that index construction must pass BEFORE
             any strategy is run. Run this first.
- `it5c.py`  The diversification dose-response across basket sizes k = 1..626.

Read `ASSESSMENT_iteration5_FINAL.md` for the close of the loop, including the
deflated-significance table that corrects the significance claims in the earlier
reports.

## Iteration 6 (added)

- `etf_test.py`  The pre-registered index-ETF test. Runs the frozen rule set
                 plus a matched control across 26 index ETFs from an independent
                 data source. This is the test ASSESSMENT_iteration4 §5 called
                 decisive.

Read `ASSESSMENT_iteration6_ETF_TEST.md` last. Headline: the system replicates,
and 26 index ETFs turn out to be 1.28 effective independent bets, which is why
it still cannot be proven.

## Iteration 7 (added)

- `it7.py` / `it7_run.py`  The multi-asset portfolio attempt: 23 ETFs across
  eleven sleeves, effective-independent-bet measurement, and the train/test
  portfolio comparison against SPY alone.

Key finding: strategy-return correlation (0.529) is far higher than underlying
price correlation (0.198), because a long-only dip-buying rule fires on
everything at once. Diversifying the instrument list does not diversify the bet.

## Iteration 8 (added) — the working system

- `it8.py`      The four sleeves: DipScore mean reversion, time-series momentum,
                cross-sectional momentum, turn-of-month. Vol targeting and
                performance metrics.
- `it8_run.py`  Raw sleeve streams and the strategy-correlation matrix.
- `it8b.py`     Risk-parity sizing, the combined portfolio, and the train/test
                comparison against buy-and-hold. This is the one to run.

Result: combined Sharpe 0.68 vs SPY 0.46 over 2006-2017; levered to matched
volatility, 12.0% CAGR against 7.4% with a -29% drawdown against -56%. Worst
year -4.0% against SPY's -38.3%. No parameter search was run, so no
multiple-testing deflation applies.

## Iteration 9 (added) — the target, translated

- `it9.py` / `it9_run.py`  Two additional sleeves (volatility-managed equity,
  short-term cross-sectional reversal), the six-sleeve combination, weighting
  comparison, and the horizon analysis that maps a win-rate/payoff target onto
  a Sharpe target.

Key identity: win rate at horizon T = Phi(Sharpe * sqrt(T)). A "60% win at
1:1.5" target is a Sharpe 0.94 target measured quarterly. The final five-sleeve
system reaches 68.1% quarterly win at 1:1.45, Sharpe 0.77 full-sample — with a
95% CI of [0.05, 1.33], which is the real constraint.

## Iterations 10-11 (added)

- `it10.py` / `it10_run.py`  Four creative ideas: overnight/intraday session
  decomposition, cost-aware overnight tilt, correlation-scaled gross exposure,
  strategy-momentum weighting. All four failed; see
  ASSESSMENT_iteration10_CREATIVE.md, especially the liquidity cross-check that
  identified the overnight effect as a crisis-era opening-print artifact.
- `it11.py`  Two market-neutral single-stock sleeves from the 626-name panel.
  S8 betting-against-beta works (Sharpe 0.81, stable train/test) and is the
  strongest sleeve found. S9 stock-level short-term reversal is dead.

CURRENT BEST SYSTEM: six sleeves, equal weight, no conditioning. Sharpe 0.89
full-sample / 1.16 out-of-sample, max drawdown -7.6%, 72.3% winning quarters at
1:1.44. Read ASSESSMENT_iteration11_BAB.md, including the BAB decay table.

## Iteration 12 (added)

- `it12.py`  Donchian 50/20 breakout sleeve, built to add positive skew.

Two self-corrections and one important result: the sleeves are NOT uniformly
negatively skewed (portfolio quarterly skew is -0.07), the payoff "shortfall"
diagnosed in iteration 11 was inside the bootstrap CI, and the payoff ratio
itself has a 95% CI of [0.84, 3.15] on 47 quarters. Narrowing that to +/-0.25
would take 249 years of data. Win rate converges; payoff ratio does not. Stop
optimising against it. See ASSESSMENT_iteration12_MEASURABILITY.md.

RECOMMENDED SYSTEM: the 6-sleeve portfolio (it11). Sharpe 0.89 full / 1.16 OOS,
max drawdown -7.6%, 72.3% winning quarters.

## Iteration 13 (added)

- `it13.py`  Intraday momentum/reversal sleeve (first 30 min -> last 30 min) on
  SPX 1-minute data at ES futures cost (0.35 bp/side). Fails in both directions:
  the measured correlation is -0.069 (published sign is positive), and the gross
  effect is smaller than futures friction either way.

What futures DO change: leverage becomes margin-based, so the levered variant is
implementable. 6-sleeve levered 3.18x = 16.80% CAGR at SPY's volatility with a
-22.3% max drawdown, against SPY's 7.37% and -56.5%.

Full horizon table (daily/weekly/monthly/quarterly/annual) is in
ASSESSMENT_iteration13_FUTURES.md, including the benchmark rows showing SPY has a
HIGHER hit rate than the system at every horizon from monthly out, with a far
worse payoff and 3-5x the worst-period loss.

## Iteration 14 (added)

Daily win-rate arithmetic: hit = Phi(Sharpe/sqrt(252)), so a 60% CALENDAR-daily
hit rate requires Sharpe ~4.0 (Medallion ran 2-3). Not reachable.

A 60% hit rate on TRADING days is reachable: hold the portfolio only on
high-conviction days (10.1% of days), sized 1.55x. Result: 26 trades/year,
60.5% winners, Sharpe 0.81 vs the always-on 0.89. The cost is that weekly,
monthly and quarterly hit rates collapse (60.9->14.5, 64.3->31.4, 72.3->46.8)
because most calendar periods contain no trades.

Correction to iteration 8: the system does NOT profit in downtrends (-0.36%/yr)
or high-volatility regimes (-1.87%/yr). It is DEFENSIVE, not all-weather
profitable. High volatility is the measured weak spot; S6 STREV is the only
sleeve positive there. See ASSESSMENT_iteration14_DAILY.md.

## Iteration 15 (added) — the exhaustive intraday scan

- `it15.py`  Systematic scan: 13 entry x 13 exit 30-min windows x 12 pre-open
  conditions = 1,092 cells on SPX 1-minute data, with the deflated
  multiple-testing threshold.

Result: deflated threshold |t| > 3.47; 3 cells clear on train, ZERO on test.
But train/test t correlation is +0.256 - intraday structure is real at roughly a
quarter of its apparent size, which puts it at the same magnitude as ES costs.

One sleeve survived and is worth keeping: buy ~13:00 ET on gap-up days, hold to
close. 138 trades/yr, 54.4% hit, Sharpe 0.74 full / 0.32 test, correlation +0.16
to the rest. Adds portfolio Sharpe 0.89 -> 1.02 (test 0.96 -> 1.10). Futures only
- it dies above 3 bp/side. Discount it to ~0.3 Sharpe forward: it was chosen as
best-of-1,092.

CURRENT BEST SYSTEM: seven sleeves, equal weight. Sharpe 1.02 full / 1.10 OOS.

## Iteration 16 (added) — combining patterns instead of selecting one

- `it16.py`  Expanded scan: 13x13 windows x 24 conditions (gap, prior day,
  vol regime, day of week, turn of month, expiry week) = 2,275 cells. Keeps
  EVERY cell passing a train threshold and holds the whole basket.

Result: 349 combined patterns give TEST Sharpe 0.34 - the same as the single
best cell (0.32). Two reasons, both measured: the survivors have 9.6 effective
independent patterns (not 132), and at |t|>2.0 roughly 103 of 132 survivors are
expected by chance, so only ~22% are plausibly real.

What the survivors cluster on: Monday, gap-up days, wide prior range, expiry
week, and the 14:30-15:30 ET block. That is a Monday effect, a gap-continuation
effect and a late-afternoon drift - all documented for decades, all worth 1-2 bp
a day against 0.7 bp of ES friction.

Three independent intraday approaches now converge on out-of-sample Sharpe ~0.3.
System unchanged from iteration 15: seven sleeves, Sharpe 1.02 full / 1.10 OOS.
