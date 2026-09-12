# HANDOFF — complete context for the trading-system research programme

**Purpose:** paste this into Claude Code so it has full context. Everything
below was established through 22 iterations of a Crucible-framework research
loop. Each claim traces to a numbered ASSESSMENT file in this bundle and to a
runnable script. Nothing here is asserted without a measurement behind it.

**Date of handoff:** 12 September 2026.

---

## 0. The user, the goal, and the constraint that governs everything

**Original goal:** a high-probability trading system on SPY — 60–70% win rate
at 1:2 or better risk-reward, ideally daily, ideally "works in any market."

**Current binding constraint (learned late, iteration 21–22):** the user trades
through a **prop firm that permits only 0DTE options, long-only, naked calls or
puts.** No selling, no spreads, no futures, no shares, no multi-day holds. This
invalidates most of what was built and is the first thing any future work must
respect.

**The user's belief:** markets are human behaviour, so undiscovered rules and
loopholes must exist. Twenty-two iterations partly confirmed this (real
regularities exist and were measured) and partly refuted it (none are large,
undiscovered, or bigger than transaction costs).

## 1. The arc in one table

| It. | What was tried | Result | Key number |
|---|---|---|---|
| 1 | Daily SPY dip-buying system (DipScore) | **Works** | 73.4% win, +0.13R/trade, 267 trades 2000–26 |
| 1 | Same at 1:2 geometry | Fails OOS | 38.3% win, negative vs control |
| 1–3 | Minute-level SPX, 5 setup families + compressed DipScore | All fail | best OOS t = 1.01; edge is multi-day, not intraday |
| 3 | Ablation: daily vs minute resolution, same signal | No difference | +0.177R vs +0.220R, within noise |
| 4 | Frozen rules across 652 single stocks | **Zero edge** | excess vs control −0.0008R, t = −0.07 (date-clustered) |
| 4 | Volatility-bucket gradient that looked real | **Lookahead artifact** | vanished when buckets fixed pre-2015 |
| 5 | Synthetic indices, k=1..626 (diversification test) | Flat | no dose-response |
| 5 | Deflated significance across 406 configs | SPY barely clears | expected max t = 2.99; SPY t = 3.54; adjusted p ≈ 0.08 |
| 6 | 26 real index ETFs, independent data | **Replicates** but | +0.077R mean excess; **n_eff = 1.28** (corr 0.775) |
| 7 | One rule across 23 asset classes | **Fails OOS** | strategy-return corr 0.529 vs price corr 0.198 |
| 8 | **Diversify the RULE: 4 sleeves** | **Works** | Sharpe 0.68 vs SPY 0.46; 2008: −4.0% vs −38.3% |
| 9 | +2 sleeves; win/payoff = f(Sharpe, horizon) | Target reframed | 68.1% qtrly win at 1:1.45; Sharpe CI [0.05, 1.33] |
| 10 | 4 creative ideas (overnight split, corr-scaling, strat-momentum) | All fail | overnight effect = crisis opening-print artifact |
| 11 | **Betting-against-beta sleeve** from 626 stocks | **Works** | Sharpe 0.81 standalone; portfolio 0.77 → 0.89 |
| 12 | Donchian breakout for positive skew | Fails; and | payoff ratio CI [0.84, 3.15] — needs 249 yrs to resolve |
| 13 | Intraday momentum (first-30 → last-30) at futures cost | Fails both directions | corr −0.069; gross < friction |
| 14 | Daily hit-rate arithmetic; concentrated variant | 60% daily needs Sharpe 4.0 | 60.5% on trading days possible, calendar stats collapse |
| 15 | **Exhaustive 1,092-cell intraday scan, deflated** | 0 cells clear on test; but | train/test t corr **+0.256** — real, ~¼ size |
| 15 | Gap-up afternoon sleeve (best cell) | Survives, thin | 138/yr, 54.4% win, Sharpe 0.32 OOS |
| 16 | Combine 349 patterns instead of picking one | Same as single cell | ~80% of survivors are false positives; n_eff 9.6 |
| 17 | **Volatility term-structure sleeve** (VXX/VXZ) | **Works**; fixes weak regime | portfolio 1.00 → 1.12; high-vol −1.87% → +1.93% |
| 18 | Leverage math; two-bucket consolidation | 60%/yr = 91% chance of >50% DD | **two buckets 50/50: Sharpe 1.20 / 1.40 OOS** |
| 19 | Real CBOE VIX 1990–2026; pre-open prediction | Predicts SIZE not direction | corr +0.574 with \|move\|, +0.060 with sign |
| 20 | Volatility risk premium sleeve | 79.6% daily hit rate, but | skew −34, dies at 2 bp/day cost; capped version = free-lunch artifact |
| 21 | System under long-options-only | 6 of 8 sleeves die; DipScore as **4% ITM calls** | 72.3% win, +3.93%/trade; killed at 4% spread |
| 22 | System under **0DTE long-only** | DipScore dies; two intraday trades survive | see §4 |

## 2. Principles that emerged (each backed by repeated measurement)

1. **Win rate and payoff are locked at the trade level by expectancy.** 60%
   at 1:2 = +0.80R/trade; nothing in 410+ configs across six universes came
   within an order of magnitude. The frontier was measured five ways and is the
   same curve every time: ~61–73% at ~1:0.6–1:1.0, or ~36–44% at ~1:1.8.
2. **At the portfolio level they are not locked** — win rate at horizon T =
   Φ(Sharpe × √T). A "60% win at 1:1.5" target is a Sharpe ≈ 0.94 target
   measured quarterly, or 1.50 monthly. A 60% *daily* hit rate requires Sharpe
   ≈ 4.0 (Medallion ran 2–3).
3. **Raw win rate is nearly worthless as a metric.** Random long entries in an
   uptrend with a wide stop win ~65%. SPY buy-and-hold wins 74.5% of quarters at
   1:0.68 with a −38% worst year. High hit rate is what selling insurance and
   holding beta give you for free.
4. **Every conditioning / filtering / clever-weighting attempt lost to equal
   weight.** Twelve failures. At ~12 years of data, estimation error in any
   trailing-window rule exceeds the effect being estimated. Equal weight
   estimates nothing and therefore has no estimation error to lose.
5. **The only lever that ever raised Sharpe was adding an uncorrelated return
   driver.** Programme arc: 0.46 → 0.68 → 0.77 → 0.89 → 1.00 → 1.12 → 1.20,
   every step from a new sleeve, never from a better rule.
6. **Diversify the RULE, not the instrument.** One long-only dip-buying rule
   across 23 asset classes produced strategy-return correlation of 0.529 against
   price correlation of 0.198 — it manufactures its own common factor. Four
   structurally different rules on the same assets gave n_eff 2.77 vs 1.78.
7. **Correlated instruments are one bet.** 26 index ETFs → n_eff 1.28. Naive
   t of 4.16 collapsed to 0.92 after correlation adjustment. Always date-cluster
   and correlation-adjust; naive pooled t-stats produced false discoveries three
   separate times (14.8 → 6.58 → −0.07 in iteration 4).
8. **Count configurations and deflate.** Expected max |t| under the null across
   N trials ≈ (1−γ)Φ⁻¹(1−1/N) + γΦ⁻¹(1−1/(Ne)). At N=406 that is 2.99.
9. **Intraday structure is real at ~¼ of its apparent size** (train/test t
   corr +0.256 across 1,092 cells) and that quarter is the same magnitude as
   ES round-trip friction (0.7 bp). The survivors are named, decades-old effects:
   Monday, gap continuation, 14:30–15:30 drift.
10. **Things that looked like loopholes and dissolved under one boring check:**
    a monotonic vol gradient (lookahead), a 34-pt overnight/intraday gap (crisis
    opening prints, largest in illiquid ETFs), a Sharpe-3.2 capped short-vol
    strategy (the cap is a free option that isn't free), a +6.6% FOMC straddle
    (0DTE IV on Fed days is bid above VIX).
11. **Edges that survive under 0DTE are tied to flows with a deadline** —
    leveraged-ETF rebalancing into the close, gap-driven repositioning. Bets on
    information the market already has die.
12. **The confidence interval, not the strategy, is the binding constraint.**
    Sharpe 1.12 over 11.6 years has a 95% CI of roughly [0.4, 1.8]. The payoff
    ratio CI is [0.84, 3.15] and would take 249 years to narrow to ±0.25.
    Leverage decisions must be made against the low end of the CI.

## 3. The unconstrained system (if the account ever allows it)

**Two execution buckets, 50/50, each sleeve vol-targeted to 10% (60-day
trailing, lagged), equal weight within bucket, no conditioning.**

**Bucket A — fast (futures, ~140 decision-days/yr):**
- S1 DipScore: SPY dips in confirmed uptrend (close > SMA200 rising; score from
  RSI2<10/<5, IBS<0.2, new 10-day low, 3 down days, below SMA50, calm vol,
  crisis-vol penalty; trade when score ≥ 0.35). Entry next open, stop 2×ATR14,
  target 1×ATR14, 5-day time stop. ~10 trades/yr, 73% win.
- S12 Gap-up afternoon: buy S&P ~13:00 ET on gap-up days, hold to close.
  ~138/yr, 54% win, Sharpe 0.32 OOS. Futures only — dies above 3 bp/side.
- S13 Vol term structure: long VXX when VXX outperforms VXZ over 5 days
  (backwardation), short otherwise. Sharpe 0.48. **Data ends Nov 2017 — the
  Feb 2018 volmageddon is NOT in the backtest. Cap this sleeve's weight.**

**Bucket B — slow (monthly rebalance, ETFs + stocks):**
- S2 Time-series momentum: hold each of 25 ETFs only while 12m return > 0,
  inverse-vol weighted.
- S3 Cross-sectional momentum: long top third / short bottom third by 12m
  return, inverse-vol, market-neutral.
- S5 Volatility-managed equity: SPY exposure ∝ 1/trailing-21d-variance,
  target 12%, cap 2.5×.
- S6 Short-term reversal: long past-week losers / short winners across the ETF
  universe. Standalone Sharpe 0.07 but the only sleeve positive in high-vol.
- S8 Betting-against-beta: long lowest-beta 30% / short highest-beta 30% of
  626 stocks, beta-balanced, monthly. Sharpe 0.81 standalone (1.30 in 2000–07
  decaying to 0.51 in 2016–26 — post-publication crowding).

**Results (2006–2017):** Sharpe **1.20 full / 1.40 OOS**, CAGR 5.7% at 6% vol,
max DD **−5.26%**, positive in uptrend/downtrend/high-vol regimes. Levered
3.18× to SPY vol (futures): ~17%/yr, −22% max DD, vs SPY 7.4% / −56%. 72%
winning quarters at ~1:1.4.

**Leverage table (iteration 18):** 20%/yr target → 3.5×, 0.3% chance of >50%
DD. 60%/yr → 10.6×, **91% chance of >50% DD**. 100%/yr → 17.6×, 100% chance,
8.7% ruin. Recommended 2–3.5×.

## 4. The constrained system — what the user can actually trade NOW

**Account: 0DTE options, long-only, naked calls or puts.** Under this:
- DipScore (5-day hold) is impossible. All Bucket B is impossible.
- ATM 0DTE loses **−53% per trade at 17% win rate** (three hours of pure time
  value; break-even needs 0.28% move, median afternoon move is 0.21%). **Never
  ATM or OTM on a directional signal.**
- **2% in-the-money** is the only viable structure: delta ≈ 1.0, break-even
  ≈ 0.03%. It is a synthetic futures position with capped loss.
- Gross edge available is ~5 bp/trade; spread is 1–4 bp (0.5–2.0 index points).
  **Fill quality decides everything.** Above 1.5 pts round-trip, nothing works.

**The 0DTE book — two signals surviving out of sample (train <2013, test 2013+):**

| Signal | Instrument | Entry | Trades/yr | Win | TRAIN | **TEST** |
|---|---|---|---|---|---|---|
| SPX gaps **up > 0.3%** at open | 2% ITM **call** | ~13:00 ET | ~65 | 53.1% | +3.90% | **+1.14%** |
| Day is **down > 70th-pct magnitude by 15:00** (expanding-window threshold) | 2% ITM **put** | 15:00 ET | ~34 | 52.7% | +3.42% | **+2.77%** |

Both hold to the close / expiry. Mechanisms: gap-continuation (documented);
end-of-day forced selling on down days (leveraged-ETF rebalancing, margin,
closing-auction imbalances). **Buying the dip into the close on down days loses
−3.81% OOS.** Gap-up + VIX above running median also survives (+0.87% OOS).

**Sizing:** at 2% of account per trade (prop-firm drawdown limit) ≈ 3–4%/yr; at
5% ≈ 8–10%/yr with worst year ~−30%. Returns quoted are % of premium.

**Tested and rejected under 0DTE:** FOMC straddle (real 1.8× move, priced away
above ~1.1× VIX IV); last-hour continuation on up days; both reversals;
unconditional afternoon trade; buy-the-dip.

## 5. Pre-open VIX use (iteration 19)

Prior-day VIX close predicts the day's **size** (corr +0.574 with |open→close|),
not direction (+0.060). Table for planning:

| Prior VIX | Expected \|open→close\| | 20th–80th pct range |
|---|---|---|
| 9–13 | 0.35% | 0.10–0.55% |
| 15–18 | 0.49% | 0.14–0.81% |
| 18–23 | 0.66% | 0.20–1.03% |
| 23+ | 1.26% | 0.32–1.98% |

Use for stop/target scaling and position sizing. Filtering the intraday sleeve
by VIX raised hit rate (54.4 → 56.9%) but not Sharpe and cut trades 138 → 38.
**Size by VIX, don't filter by it.**

## 6. Data sources (all reachable from GitHub; none need a vendor)

| Data | Source | Span | Notes |
|---|---|---|---|
| SPY daily OHLCV | willhjw/big_movers "SPY Historical Data.csv" | 2000-01 → 2026-03 | unadjusted; cross-checked vs hackingthemarkets (ret corr 0.982) |
| SPX 1-minute | FutureSharks/financial-data, oanda/SPX500_USD | 2005-01 → 2020-05 | CFD feed, UTC timestamps (resolved via volume U-shape), tick-count volume only; 2017 has a gap |
| 928 single stocks daily | willhjw/big_movers/collected_stocks | 2000 → 2026 | selection-biased ("big movers"), includes delisted; 30 symbols dropped for reverse-split artifacts |
| 1,344 ETFs daily | neo-zhao/CMSC320_Final_Tutorial_Huge_Stock_Market_Dataset (Kaggle mirror) | → 2017-11-10 | split/div adjusted; includes VXX, VXZ, SVXY, UVXY, sector SPDRs, bonds, commodities, FX |
| **CBOE VIX daily OHLC** | datasets/finance-vix | **1990-01 → 2026-09-04** | the longest and most current series in the study |
| FOMC dates | Fed press releases | 2005 → 2020 | 121 of 124 matched |

**Biggest data gaps:** ETF panel and VXX end Nov 2017 (Feb 2018 volmageddon
missing); SPX minute ends May 2020. Extending these is the highest-value next
step — the CI is the binding constraint.

## 7. Methodology standards (apply to any future work)

- Signals from data through bar t's close; entry at bar t+1's open.
- Same-bar stop/target ties → book the stop.
- Matched random-entry control for every strategy; report excess over control.
- Train/test split fixed before any strategy runs; select on train only.
- Date-cluster pooled inference; correlation-adjust cross-instrument inference
  (n_eff = n / (1 + (n−1)ρ)).
- Count every configuration tested; deflate against expected max |t|.
- Costs: SPY 1 bp/side; single stocks 2.5–5 bp/side; ETFs 2 bp; ES 0.35 bp;
  0DTE options 0.5–2.0 index points round-trip.
- Vol targeting uses trailing 60-day estimate lagged one day.
- Any bucketing/ranking variable must be computed from pre-test data only.
- Harness sanity-tested on a zero-drift random walk before use.

## 8. Current thinking and open questions

**Where the user is:** wants high-frequency, high-win-rate, high-return trading;
constrained to 0DTE long-only; believes undiscovered loopholes exist.

**Where the evidence is:** the constrained book earns single digits a year at
prop-firm sizing. The unconstrained system earns 12–20%/yr at survivable
leverage. The gap between them is the account constraint, not the research.

**Principle for finding more 0DTE edges:** look for flows with a deadline (who
*must* trade and when), not for chart patterns. Candidates not yet tested:
index rebalance days (Russell reconstitution, S&P quarterly), options expiry
pin/unpin in the last hour, month-end pension rebalancing into the close, and
the 15:50 closing-imbalance publication.

**Open methodological questions:** actual 0DTE fill quality (the single check
that decides the book); actual FOMC-day 0DTE implied vol (would settle the
straddle); whether the last-hour put effect strengthened post-2020 as leveraged
ETF AUM grew (data needed).

**Iteration budget note:** 22 iterations, ~420 configurations, ~15 distinct
economic hypotheses. Every successful step came from a new return driver or a
new data source. No successful step came from re-slicing existing data.

## 9. File inventory

ASSESSMENT files (read in order for the full narrative):
`ASSESSMENT.md` (it1–3), `BLOCKED.md`, `ASSESSMENT_iteration4.md`,
`_iteration5_FINAL`, `_iteration6_ETF_TEST`, `_iteration7_MULTIASSET`,
`_iteration8_MULTISTRATEGY`, `_iteration9_TARGET`, `_iteration10_CREATIVE`,
`_iteration11_BAB`, `_iteration12_MEASURABILITY`, `_iteration13_FUTURES`,
`_iteration14_DAILY`, `_iteration15_INTRADAY_SCAN`, `_iteration16_PATTERN_BASKET`,
`_iteration17_VOL`, `_iteration18_LEVERAGE_AND_CONSOLIDATION`,
`_iteration19_VIX_PREOPEN`, `_iteration20_VRP`, `_iteration22_0DTE_NATIVE`.

Playbooks: `STRATEGY.md` (plain-language 8-sleeve), `LONG_OPTIONS_PLAYBOOK.md`,
`ZERO_DTE_PLAYBOOK.md`, `FLEET.md` (parallel worker contract).

Code: `mh.py` (minute harness), `md.py` (multi-day minute backtester),
`strat.py` (intraday families), `audit.py`, `fleet_worker.py`/`fleet_run.py`
(cross-section), `etf_test.py`, `it5.py`/`it5b.py`/`it5c.py` (synthetic indices),
`it7.py`–`it13.py`, `it15.py`/`it16.py` (intraday scans), `it21.py`
(Black-Scholes option pricer). `README.md` maps each to its iteration.
