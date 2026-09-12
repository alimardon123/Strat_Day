# CLAUDE.md — Trading Strategy Research: Full Project Context

> Handoff document. Everything discussed, tested, decided and concluded so far.
> Written so a fresh Claude session has complete context without the original conversation.

---

## 1. Who and what

**User:** retail trader. Has a prop-firm account (day-trading-only mandate, daily loss
limits ~3–5%), plus forex and stock accounts at own brokers. Wants to trade **SPY 0DTE
options** intraday. Max 5× Claude plan. Prefers code that is short, simple, readable.

**Original question:** "Many strategies lose. If I invert their signals, do I win?"

**Where it ended:** seventeen studies, one directional edge found, a complete system spec
with every parameter measured. Documented below.

**Current date:** September 2026. All data used ends 2020. The single most important next
step is extending the surviving signal to 2021–2026.

---

## 2. User's constraints (all decisions must respect these)

| constraint | implication |
|---|---|
| day trading only, flat at close | 21-day-hold strategies are unavailable; VRP harvest is structurally blocked |
| prop firm daily loss limit ~4% | sizing is set by worst single day, not by Sharpe |
| wants 0DTE options on SPY | verified: TP on underlying → option profitable 99.5%; ITM strikes best |
| VIX for daily preparation | VIX forecasts range (R²=0.54), not direction (R²=0.00002) |
| forex + stock accounts also available | stock account w/ options approval could hold VRP; forex cannot |

---

## 3. Data sources (all public, all on GitHub raw)

```
BASE=https://raw.githubusercontent.com/FutureSharks/financial-data/master/pyfinancialdata/data

# Histdata 1-min CFDs (used for SPX 2010-2018, DAX, EuroStoxx, Nikkei)
$BASE/stocks/histdata/SPXUSD/DAT_ASCII_SPXUSD_M1_{YEAR}.csv     # 2010-2018
$BASE/stocks/histdata/GRXEUR/...   ETXEUR/...   JPXJPY/...        # 2010-2018
# format: YYYYMMDD HHMMSS;open;high;low;close;vol  (Eastern time, no DST adjust)

# Oanda 1-min, 25 instruments, 2005-2020 (used for cross-asset + 2019-2020 holdout)
$BASE/currencies/oanda/{SYMBOL}/{YEAR}/oanda-{SYMBOL}-{YEAR}-{MONTH}.csv
# symbols: SPX500_USD XAU_USD WTICO_USD USB10Y_USD USB02Y_USD JP225_USD NAS100_USD ...
# format: time,close,high,low,open,volume

# VIX daily 1990-present
https://raw.githubusercontent.com/datasets/finance-vix/main/data/vix-daily.csv
```

Detected sessions (Eastern): SPX 09:32–16:02 · DAX 02:02–08:32 · US open detected by
volume spike in oanda data. **Sessions must be auto-detected per instrument** — Nikkei
detection failed and its results were discarded.

---

## 4. Methodology — the statistical guards (non-negotiable)

Every result in this project passed through `stats_engine.py`. These are the reasons the
findings can be trusted, and the reason most retail backtests can't.

1. **Train/test split.** Thresholds and directions locked on train, applied untouched to test.
2. **Day-block (or week/month-block) bootstrap** for p-values. Overlapping intraday
   returns are massively autocorrelated; naive t-stats are inflated by orders of magnitude.
   *Measured: a naive t=8.51 (p≈1e-17) became bootstrap p=0.003.*
3. **Benjamini-Hochberg FDR** across every test run, not just the winners.
4. **Cost subtracted before anything is called positive.** ES futures round trip = 0.33
   index pts ≈ 0.0157% of price. CFD = 0.50 pts. Tight retail = 0.15 pts.
5. **Observability enforced by clock check**, not by `shift()`. A four-hour look-ahead
   manufactured Sharpe 7.2 once (step 9); fixed in step 10.
6. **Opposite-condition sanity check.** If a mechanism predicts X, the anti-X bucket must
   be dead or negative.
7. **Cross-market and post-publication holdouts** on a different data feed.

**Rule of thumb established:** any Sharpe above ~3 on price-only data is evidence of a
bug, not a discovery. Go find the bug.

---

## 5. Every study, in order

### Part 1 — Inversion (steps 1–4)

**Baseline:** naive Donchian breakout, 20×5m lookback, stop 1.5 ATR, target 3.0 ATR,
1-minute path resolution. 4,383 trades, SPX 2013–2018.

| | win % | R:R | expectancy | t |
|---|---|---|---|---|
| with cost | 34.4% | 1:1.29 | −0.2554R | −12.43 |
| **zero cost** | 35.6% | 1:1.81 | **+0.0005R** | **+0.02** |

→ The strategy has literally zero edge. It loses purely from cost.

**Mirror inversion** (flip direction, swap levels): win rate 34%→**63%** exactly as user
predicted, R:R collapsed 1:1.29→1:0.38, expectancy still −0.1285R. Zero-cost: −0.0006R.
**Inversion maps zero onto zero.** Breakeven cost would be 0.04 pts; real is 0.25–0.50.

**Stop-cascade test** (user's real intuition — price runs past stops): enter at stop-out
in continuation direction vs matched control. Excursion advantage **+0.85 ATR at 120 min,
t=+9.37** — the effect is REAL. But as a bracketed trade: −0.01 to −0.04R at zero cost.
MFE is not capturable. Sweep beats random entry by +0.2R and is still below cost.

**Regime conditioning:** only time-of-day survived train→test (morning +, close −).
Best bucket +0.14R gross vs cost 0.25R.

### Part 2 — 282-hypothesis sweep (steps 5–7)

57 behavioural/structural conditions × 5 horizons. Time-of-day, calendar, gaps, opening
range, round-number magnetism, momentum at 4 scales, runs, vol regime, VWAP deviation.

- 35 of 282 held correct direction out-of-sample at |t|>1.96 vs ~7 by chance → **structure exists**
- Survivors of FDR 10%: **0**. Bonferroni: **0**.
- Best candidate gap_up + OR_breakout_up @60m: naive t 8.51 → bootstrap p 0.003.
- Cross-market validation: effect shrank **72%** (+0.283 → ~+0.08 ATR). 0 of 3 confirmed.
  EuroStoxx went negative. Out-of-sample effect = 0.12 pts vs 0.25–0.33 cost.

### Part 3 — Execution (step 8)

Limit entry vs market: on discovery set −0.010 → **+0.152** per signal, p=0.012. **Largest
single improvement anywhere in the study.** But adverse selection ate ~half the paper
benefit (theory +0.365, observed +0.195). Never turned a negative positive out of sample.

### Part 4 — Changing the axis (steps 9–10)

- **Overnight vs intraday:** overnight beats intraday in 4/4 markets. SPX overnight gross
  SR 0.77 → net 0.27 after daily cost; buy-and-hold gives 0.77 with no trading.
- **Time-zone spillover:** initial Sharpe **7.20** → was a look-ahead (DAX overnight
  window contained the US session). Fixed: −0.39. 0 of 8.
- **DAX/EuroStoxx spread reversion:** negative at every threshold; spread trends.

### Part 5 — Variance risk premium (step 11)

VIX vs subsequent 21-day realised vol, 2010–2018:
- mean premium **+3.25 vol pts**, positive **82.5%** of periods, **Sharpe +2.10**, p<0.001
- **positive in every year** (2010: +10.23 … 2018: +1.19)
- worst period −23.61 (Jul 2011) = **7.3× mean gain**
- Feb 2018: premium was −14 for three weeks BEFORE the spike with VIX at 11; then
  VIX 13→17→37 in three sessions; premium richest immediately after
- **Tail estimated from 5 observations. No 2008, no 2020 in sample.**
- **Daily version** (VIX vs next-day RV): +3.88 pts, 73.1% positive, but worst day
  −105.83 = **27.3× mean**. 9.6% of days lose >10 pts.
- **Laddered version** (open 1/day, hold 21, 21 open at once): cost identical (12
  full-size RT/yr), but lag-1 autocorr 0.934 → ~12 independent bets not 252. Naive
  Sharpe 10.16 is illusory. All 21 legs lose together in a spike.
- **Not a strategy:** measured VIX − RV, never backtested real option prices, spreads,
  margin, assignment. **Blocked by day-only mandate** (needs 21-day hold). Under prop
  daily limit, daily version breaches at 1%/day sizing on any −15.5pt day.

### Part 6 — Structural flow + the cost law (steps 12–13)

Expiry / month-end / quarter-end / triple witching: **0 of 32** survive. Event days are
*calmer* (0.877% range vs 0.992% normal).

**THE LAW:** `cost drag on annual Sharpe = cost_per_trade × trades_per_year ÷ annual_vol`

| style | trades/yr | required gross Sharpe (ES) |
|---|---|---|
| 1/day | 252 | 0.31 |
| 4/day | 1,008 | 1.24 |
| 10/day | 2,520 | 3.10 |
| 20/day | 5,040 | 6.20 |
| this study's breakout | 9,776 | **12.03** |

Renaissance Medallion ≈ gross 2–3. Every result in the project is explained by this one
variable. VRP survived because it pays the toll 12×/yr.

### Part 7 — What VIX predicts (step 14)

| question | test R² |
|---|---|
| today's **range** | **0.539** |
| today's **direction** | **0.00002** |
| today's **character** (trend/chop) | 0.0018 |

VIX quintile range: v.low 0.561% → v.high 1.710% (3.05×). VIX-scaled sizing: vol-of-vol
−39%, worst day −19%. **Trade budget by VIX:** v.low 1.4/day … v.high 4.2/day at 0.6 gross
Sharpe. Cost as fraction of opportunity varies 3× across regimes.

### Part 8 — 0DTE mechanics (step 15)

Black-Scholes 0DTE calls on minute data, IV=prior-close VIX, 3,958 trades:
- **User's claim "if SPY hits TP, option hits TP" is CORRECT: 99.5%**, median +63.9%
- Even >2h trades profitable 97%
- But median outcome: underlying −0.659R, option −30.3%. Flat days: underlying +0.5pts,
  option −68.4%
- Cost per unit delta: 0DTE @3.7% spread = 0.400 pts vs ES 0.330 — comparable
- **0DTE is a leverage wrapper: multiplies edge including zero edge, adds theta tax.**
  Breakeven underlying (+0.053R) → −6.1%/trade in 0DTE at realistic cost.
- **Strike selection:** ITM −10 median −20.9% / win 43.6% vs OTM +10 median −50.6% /
  win 38.9%. **ITM is correct under a drawdown mandate.**
- **Loss at stop = 53.8% of premium**, not 100%. Size on that.
- **Required signal quality:** random entries hit 2.0ATR before 1.5ATR 41.5% → −6.10%.
  Breakeven **46.8%**. 50% → +3.65%.

### Part 9 — Cross-asset overnight signals (step 16)

8.3M bars: gold, crude, US 2y/10y, Nikkei → US session direction. Observability enforced
(signal ends 15 min before open). 1,375 sessions. Correlations 0.02–0.06. **0 survivors.**

### Part 10 — THE SIGNAL (step 17) ★

**Market Intraday Momentum** — Gao, Han, Li & Zhou (JFE 2018); Baltussen, Da, Lammers &
Martens (JFE 2021). Mechanism: option market makers and leveraged ETFs are short gamma
and must hedge in the direction of the day's move before the close. Found by searching
literature, not by data mining. A 2024 study says it survives post-publication only in
high-vol regimes.

**Rules:**
1. At 15:30 ET, move = (price now / yesterday's close) − 1
2. Trade only if prior-close **VIX > 17.06** AND **|move| > 0.665%** (thresholds fixed
   on 2010–2018)
3. Move up → long; down → short
4. Exit at 16:00 close

| | n | net/trade | win % | net Sharpe | boot p |
|---|---|---|---|---|---|
| Discovery 2010–18 | 337 | +0.0645% | 58.5 | **+2.50** | **0.0003** |
| Holdout 2019–20 (oanda feed, post-pub) | 85 | +0.0975% | 54.1 | **+1.67** | 0.135 |
| Opposite condition | 299 | −0.0287% | 41.1 | −4.44 | 1.00 |

Unconditional version: R² 2.3% (matches paper) but net −0.0063 — cost kills it. Low-VIX
tercile is *negative* (−0.072 corr). Effect lives in high vol only.

**Year by year:** 7/10 positive. **2011 (+14.32%) and 2020 (+9.49%) = +23.8 of +30.0
total.** 2016/2018/2019 negative. 2017 stood aside entirely (VIX never >17.06). Worst
trades: −3.49% (2020-03-18, VIX 76), −2.34%, −1.90%, −1.12%, −1.05% — all in the best years.

**Leverage:** 1× ~+3%/yr, worst −3.5%, DD −7.0%. 3× ~+9%, DD −21%. 5× ~+15%, DD −35%.
**A 30-min hold protects from overnight gaps, not from a VIX-75 half-hour.**

**Status: real, small, regime-dependent, crisis-loaded. An edge, not a loophole.**

---

## 6. Decisions made

1. **Inversion is dead** as a strategy concept. Transforms edge, cannot create it.
2. **Cost is the binding constraint**, never signal quality. Research budget goes to
   execution/frequency/cost, not indicators.
3. **VIX is an allocator, not a signal.** Sets trade budget, size, stops. Zero direction.
4. **ITM 0DTE, limit entry, size on 53.8% loss-at-stop.**
5. **Frequency ceiling ≤4/day**, dictated by the cost law.
6. **VRP acknowledged as real but unavailable** under day-only mandate. If pursued: own
   stock account with options approval, 30–45 DTE spreads, sized for a tail 4× worse
   than observed.
7. **Intraday momentum is the signal.** Only directional edge in 17 studies to survive.
8. **Sizing under prop mandate: ~1×**, targeting ~3%/yr on notional, because March 2020
   is in-sample and 2008 isn't.
9. **Any Sharpe >3 on price data = look for the bug first.**

---

## 7. Current thinking / open questions

- **Biggest open question:** does the intraday momentum signal hold 2021–2026? The 2024
  literature says the unconditional version faded; the conditional (high-VIX) version is
  untested post-2020. **This is the first task in Claude Code.**
- Holdout p=0.135 is underpowered (85 obs). Need 2021–2026 to resolve.
- Real 0DTE prices never tested — all 0DTE work used Black-Scholes with VIX as IV, which
  is *generous* (real 0DTE IV > 30-day VIX).
- Whether a 15:30 ITM 0DTE actually captures the 15:30→16:00 move better than ES/MES
  given theta in the final 30 minutes. Untested.
- Whether the Baltussen "rest of day" predictor and Gao "first half-hour" predictor
  should be combined; r12 (15:00–15:30) flipped sign in holdout — unstable.
- Gamma-hedging mechanism suggests the effect should scale with dealer gamma exposure.
  With options chain data (SpotGamma-style GEX), the filter could be sharpened beyond VIX.

---

## 8. Next steps, prioritised

1. **Extend step17 to 2021–2026.** yfinance SPY 1-min or ES futures. Same thresholds
   (VIX>17.06, |move|>0.665%), same guards. Report by year. If it fails post-2020, the
   signal is dead and the project restarts the search.
2. If (1) holds: **replace Black-Scholes with real 0DTE quotes** for the 15:30 entry.
   Measure actual fill, spread, and 15:30→16:00 option P&L.
3. Walk-forward the thresholds instead of fixing them on 2010–2018.
4. Add GEX / dealer gamma as a filter if options positioning data is obtainable.
5. Paper trade at 1× for ≥60 qualifying days before any live capital.
6. Separately, in own stock account: backtest a real 30–45 DTE short-spread VRP
   implementation with actual option prices and margin. Do not trade daily VRP.

---

## 9. File map (`inversion_study/`)

| file | purpose |
|---|---|
| `loader.py` | histdata SPX loader, RTH filter, ATR |
| `engine2.py` | bracket-trade simulator, 1-min path resolution, numpy hot loop, `stats()`/`report()` |
| `stats_engine.py` | **block bootstrap, BH-FDR, evaluate()** — carry this forward |
| `step1_baseline.py` | Donchian breakout baseline; `build_signals()` is the swap point |
| `step2_inversion.py` | mirror + symmetric inversion |
| `step3_sweep.py` | stop-cascade excursion study with matched controls |
| `step4_regime.py` | regime buckets, train/test |
| `step5_sweep.py` | 282-hypothesis sweep |
| `step6_correct.py` | bootstrap + FDR on the sweep |
| `step7_validate.py` | cross-market validation; `detect_open()`, `to_5m_session()`, `load_symbol()` |
| `step8_execution.py` | limit vs market with adverse selection |
| `step9_axes.py` | overnight/intraday, spillover (has the look-ahead), spread; `daily_frame()` |
| `step10_fixed.py` | spillover with observability enforced |
| `step11_vrp.py` | variance risk premium |
| `step12_flow.py` | expiry/month-end events |
| `step13_law.py` | cost-drag law |
| `step14_vix_intraday.py` | VIX → range/direction/character |
| `step15_odte.py` | Black-Scholes 0DTE simulator; `bs_call()`, `bs_put()` |
| `step16_crossasset.py` | gold/oil/bonds/Nikkei → US session; `load_oanda()` |
| `step17_intramom.py` | **the signal**; `half_hours_histdata()`, `half_hours_oanda()`, `evaluate()` |
| `strategy.py` | **the system**: `prepare_day()`, `IntradayMomentumSignal`, `select_strike()`, `size_position()`, `entry_price()` |
| `RESULTS.md` … `RESULTS_PART10.md` | full write-ups per part |
| `SYSTEM_SPEC.md` | the system with sources for every number |
| `*.pkl`, `*.csv` | intermediate results (baseline_trades, odte, vrp, intramom, sweep_scored, cross_market, axis_tests, flow_tests, crossasset) |

Run order in `README.md`. Data download commands in `README.md` and §3 above.

---

## 10. Lessons that generalise (the thinking, not the numbers)

- **Effect sizes are an equilibrium.** Anomalies survive until cheap enough to
  arbitrage; survivors cluster just under the cost wall of the cheapest participant.
  Seventeen measurements of the same boundary.
- **There are five ways to make money:** direction, risk premium, liquidity provision,
  structural flow, information. Sixteen studies tested only #1. The one edge with a
  forced-flow mechanism (#4, gamma hedging) is the one that survived.
- **A win rate is not an objective.** 34%→63% changed nothing; R:R moved in exact
  proportion.
- **Excursion studies produce false positives.** MFE is not capturable. Only bracketed
  path simulation is honest.
- **Overlapping returns inflate t-stats by orders of magnitude.** Block bootstrap always.
- **Laddering diversifies entry timing, not risk factors.** 21 correlated legs = 1 bet.
- **Leverage multiplies zero.** 0DTE, futures, any wrapper — the edge must exist first.
- **Search the literature before searching the data.** The signal came from two JFE
  papers and a directed replication, not from 282 blind hypotheses.
- **The prop-firm structure conflicts with the payoff shapes that work.** Daily loss
  limits are designed to stop exactly the trades (short vol, crisis momentum) that carry
  the premium. Twice the same edge was found and twice the mandate blocked or capped it.
- **The most valuable moment was catching a Sharpe of 7.2 four hours of look-ahead.**
  Treat too-good numbers as bugs until proven otherwise.

---

*All results are historical research on 2010–2020 data, not financial advice. Nothing here
has been paper-traded or traded live.*
