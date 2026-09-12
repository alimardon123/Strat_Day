# CLAUDE.md — UNIFIED HANDOFF: two independent research threads, one trader

> **Read this file first.** It is the top-level context for a Claude Code session.
> Two separate chats ran two separate research programmes on the same problem for
> the same person. They did not know about each other. They converged on the same
> answers by different routes, which is the strongest evidence in either.
>
> Both threads are preserved intact in subfolders. Each has its own complete
> handoff document, results files, and runnable code. This file maps them.

**Handoff date:** 12 September 2026.

---

## 0. The person, the account, the goal

**Trader profile:** retail, prop-firm account with a **day-trading-only mandate,
daily loss limit ~3–5%, and — critically — only 0DTE options, long-only, naked
calls or puts.** Also has own forex and stock accounts. Prefers short, simple,
readable code. Runs a Crucible research framework and a `/fleet` multi-agent
runner.

**Original goal:** a high-probability system on SPY — 60–70% win rate at 1:2+
payoff, ideally daily, ideally "works in any market."

**Belief driving the work:** markets are human behaviour, so undiscovered rules
and loopholes exist. Both threads partly confirmed (real regularities measured)
and partly refuted (none large, undiscovered, or bigger than costs).

**The single most expensive mistake across both threads:** the 0DTE long-only
constraint was learned late (Thread A: iteration 21 of 22). **State it first in
any new session.** Most of Thread A's middle would have gone differently.

---

## 1. The two threads at a glance

| | **Thread A — multi-sleeve** (`thread_A_multisleeve/`) | **Thread B — inversion** (`thread_B_inversion/`) |
|---|---|---|
| Starting question | Build a high-win-rate SPY system | "If losing strategies are inverted, do they win?" |
| Iterations | 22 | 17 studies |
| Configurations tested | ~420 | 282-hypothesis sweep + 17 directed studies |
| Distinctive method | Random-entry controls, date-clustered inference, n_eff correlation adjustment, deflated max-t | **Block bootstrap + Benjamini-Hochberg FDR** (`stats_engine.py`), clock-based observability, opposite-condition sanity checks |
| Distinctive finding | **8-sleeve multi-strategy portfolio**, Sharpe 1.20/1.40 OOS (unconstrained) | **The cost law** and **the intraday momentum signal** (Gao/Baltussen), Sharpe 2.50/1.67 OOS |
| Data | SPY daily 2000–26; SPX 1-min 2005–20; 928 stocks; 1,344 ETFs; VIX 1990–2026 | SPX/DAX/EuroStoxx/Nikkei 1-min 2010–18; 25 Oanda instruments 2005–20; VIX |
| Entry point | `HANDOFF.md` | `CLAUDE_original.md` |
| Ends with | Two 0DTE signals (13:00 call on gap-up; 15:00 put on big-down day) | One 0DTE signal (15:30 momentum, both directions, VIX>17.06 & \|move\|>0.665%) |

---

## 2. Where they CONVERGED — treat these as settled

Independent replication by two methods on partly different data. These are the
most trustworthy conclusions in the entire body of work.

| Finding | Thread A evidence | Thread B evidence |
|---|---|---|
| **VIX predicts the day's SIZE, not its direction** | corr +0.574 with \|open→close\|, +0.060 with sign (it19) | R² 0.539 for range, 0.00002 for direction (step 14) |
| **In-the-money is the only viable 0DTE structure** | ATM: 17% win, −53%/trade; 2% ITM: 52% win, +1% (it22) | ITM −10 median −20.9% vs OTM +10 median −50.6%; loss at stop = 53.8% of premium (step 15) |
| **The variance risk premium is the largest edge available and is blocked** | +3.44 pts, 82% positive, 79.6% daily hit, skew −34, dies at 2 bp/day (it20) | +3.25 pts, 82.5% positive, Sharpe 2.10, blocked by day-only mandate, tail 7–27× mean (step 11) |
| **Cost is the binding constraint, not signal quality** | Random control at minute resolution = −0.05 to −0.09R friction (it1); edges are 1–5 bp vs 0.7–4 bp cost | **Cost law:** Sharpe drag = cost/trade × trades/yr ÷ annual vol. Breakout needed gross Sharpe 12.0 (step 13) |
| **Win-rate manipulation changes nothing** | Frontier measured 5 ways: 61–73% at 1:0.6–1.0 or 36–44% at 1:1.8 (it1–9) | Inversion took 34%→63% win, R:R 1:1.29→1:0.38, expectancy unchanged (step 2) |
| **The one surviving intraday edge is last-hour, flow-driven, high-vol-only** | 15:00 put on big-down days: +2.77% OOS; up-day continuation dies (it22) | 15:30 momentum both ways, VIX>17.06: Sharpe 2.50→1.67 OOS; low-VIX tercile negative (step 17) |
| **Structure exists in intraday data but at ~¼ apparent size** | train/test t corr +0.256 across 1,092 cells; 0 clear deflated bar (it15) | 35/282 held OOS direction vs ~7 by chance; 0 survive FDR (step 5) |
| **Any Sharpe >3 on price data is a bug** | Sharpe 3.20 capped-VRP = free option (it20); vol gradient = lookahead (it4) | Sharpe 7.20 spillover = 4-hour look-ahead (step 9) |
| **Overnight beats intraday but isn't tradeable** | 4.78% vs 0.59%/yr; crisis opening-print artifact in illiquid ETFs (it10) | Overnight wins 4/4 markets; net Sharpe 0.27 after cost vs 0.77 buy-and-hold (step 9) |
| **Event days are priced** | FOMC straddle +6.6% at VIX IV → −18% at 1.3× VIX (it22) | Expiry/month-end/witching 0 of 32; event days *calmer* (step 12) |

---

## 3. Where they DIVERGED — reconcile these first

### 3.1 The intraday momentum signal — two versions, not yet reconciled

This is the most important open item. Both threads found the same *mechanism*
(dealer gamma hedging / leveraged-ETF rebalancing into the close on high-vol
days) but specified it differently:

| | Thread A (it22) | Thread B (step 17) |
|---|---|---|
| Predictor | Open→15:00 move, magnitude > expanding 70th pct | Prior close→15:30 move, \|move\| > 0.665% |
| Regime filter | none (magnitude threshold implies it) | prior-close VIX > 17.06 |
| Direction | **put only** — up-day continuation died OOS (−0.37%) | **both** — up→long, down→short |
| Entry / exit | 15:00 / close | 15:30 / close |
| Instrument | 2% ITM 0DTE, 1-pt spread | ES futures cost (0.33 pts), then 0DTE via BS |
| OOS result | +2.77%/trade, 52.7% win, n=516 | Sharpe 1.67, p=0.135, n=85 (underpowered) |
| Data | SPX Oanda CFD 2005–20 | SPX histdata 2010–18, Oanda 2019–20 holdout |

**Also:** Thread A's it13 tested the *original* Gao predictor (first 30 min →
last 30 min) and found it **negative** (corr −0.069). Thread B used the
Baltussen *rest-of-day* predictor (prior close → 15:30) and found it positive.
These are different predictors and the discrepancy is real, not a data error.
Thread B also noted r12 (15:00–15:30) flipped sign in holdout — unstable.

**Task for Claude Code:** run both specifications on the same data with the same
stats engine (use Thread B's `stats_engine.py` — block bootstrap + FDR — it is
stricter). Resolve: does the up-day leg work under Thread B's VIX filter? Is
15:00 or 15:30 the better entry? Is the VIX>17.06 filter or the magnitude
threshold the better regime gate?

### 3.2 Predictor for the afternoon call

Thread A's gap-up afternoon call (13:00→close on gap-up >0.3% days, +1.14% OOS)
has no Thread B counterpart. Thread B's sweep tested gap_up + OR_breakout and
found it shrank 72% cross-market. **Task:** test Thread A's signal with Thread
B's cross-market validation (DAX, EuroStoxx) and its bootstrap.

### 3.3 The unconstrained portfolio

Thread A built an 8-sleeve, two-bucket portfolio (Sharpe 1.20/1.40 OOS, max DD
−5.26%) that Thread B never attempted. It is **not tradeable in the prop
account** but is tradeable in the user's own stock account. Thread B's decision
6 (VRP via 30–45 DTE spreads in the stock account) and Thread A's Bucket B are
both "own-account" ideas. **Task:** consider whether the stock account should
run Thread A's Bucket B plus a defined-risk VRP sleeve.

### 3.4 Execution

Thread B tested limit vs market entry and found it the **largest single
improvement anywhere** (+0.15/signal, p=0.012, adverse selection ate half).
Thread A never tested execution. **Apply Thread B's execution model to Thread
A's signals.**

---

## 4. Merged principles (union of both threads' lessons)

1. **Cost is an equilibrium boundary.** Surviving effects cluster just under the
   cost wall of the cheapest participant. Both threads measured this ~40 times.
2. **Five ways to make money:** direction, risk premium, liquidity provision,
   structural flow, information. Direction-only searches (most of both threads)
   found nothing durable. The edges that survived have a **forced-flow
   mechanism** — someone who must trade at a deadline.
3. **Search the literature before searching the data.** Thread B's signal came
   from two JFE papers. Thread A's exhaustive 1,092-cell scan rediscovered three
   decades-old effects. Blind sweeps find structure; directed replication finds
   tradeable structure.
4. **Win rate and payoff are locked at the trade level; unlocked only at the
   portfolio level** via win = Φ(Sharpe × √T). A 60% daily hit needs Sharpe ~4.
5. **Diversify the rule, not the instrument.** One rule across 23 assets:
   n_eff 1.78. Four rules on the same assets: 2.77. 26 index ETFs: 1.28.
6. **Equal weight beats every conditioning scheme at this sample size.** Twelve
   attempts in Thread A, regime buckets in Thread B — all lost to doing nothing.
7. **Statistical guards are non-negotiable:** train/test locked first;
   block bootstrap (naive t 8.51 → p 0.003); FDR across all tests; date-cluster
   pooled data; correlation-adjust cross-instrument; deflate against max-t;
   clock-based observability not `shift()`; opposite-condition sanity check;
   cross-market holdout; random-entry control.
8. **VIX is an allocator, not a signal.** Sets range expectation, size, stops,
   trade budget. Zero direction.
9. **Leverage multiplies zero.** 0DTE, futures, any wrapper — the edge must exist
   on the underlying first. 0DTE adds a theta tax on top.
10. **The prop mandate is designed to block the payoff shapes that carry
    premium.** Short-vol and crisis-momentum are exactly what daily loss limits
    stop. Both threads found the same edge twice and were capped twice.
11. **The confidence interval, not the strategy, is the binding constraint.**
    Thread A: Sharpe 1.12 CI [0.4, 1.8]; payoff-ratio CI [0.84, 3.15] needs 249
    years. Thread B: holdout p=0.135 on 85 obs. **All data ends 2020 (minute)
    or 2017 (ETFs). Extending to 2021–2026 is the first task.**

---

## 5. The current tradeable position — what to do in the prop account

Both threads independently arrived at: **ITM 0DTE, last-hour, high-vol days,
flow-driven direction, ~1× sizing under the drawdown mandate, single-digit
annual returns.** Not a loophole. A small, real, crisis-loaded edge.

**Candidate 0DTE book (to be reconciled per §3.1):**

| Signal | Source | Instrument | Entry | ~Trades/yr | OOS |
|---|---|---|---|---|---|
| Gap up >0.3% at open | A | 2% ITM call | ~13:00 | 65 | +1.14%/trade |
| Big down day by 15:00 | A | 2% ITM put | 15:00 | 34 | +2.77%/trade |
| \|move\|>0.665% & VIX>17.06 at 15:30 | B | ITM 0DTE, direction of move | 15:30 | ~40 | Sharpe 1.67 |

**Sizing rule (both threads):** size on worst single day, not Sharpe. Loss at
stop ≈ 54% of premium. Under a 4% daily limit, ~2–5% of account per trade.
Expect 3–10%/yr with worst years −15% to −30%.

**Before any live capital:** measure real 0DTE fills (above 1.5 index points
round-trip, nothing here works); replace Black-Scholes with real 0DTE quotes
(both threads used VIX as IV, which is generous — real 0DTE IV runs higher);
paper-trade ≥60 qualifying days.

---

## 6. Prioritised next steps for Claude Code

1. **Extend the data to 2021–2026.** SPY/ES 1-minute via yfinance or a futures
   feed; ETF panel past Nov 2017. This resolves the CI problem, tests Thread B's
   signal post-publication (2024 literature says unconditional version faded),
   and finally puts Feb 2018 and 2020–2022 into the vol sleeves.
2. **Reconcile the two intraday momentum specs** (§3.1) on identical data with
   `stats_engine.py`. Output one specification.
3. **Apply Thread B's execution model** (limit entry, adverse selection) to the
   reconciled 0DTE book.
4. **Replace Black-Scholes with real 0DTE option prices** for the surviving
   entries.
5. **Own-account track (separate):** Thread A Bucket B + a defined-risk 30–45
   DTE VRP sleeve, backtested with real option prices and margin.
6. **New 0DTE candidates per the "flows with a deadline" principle:** Russell
   reconstitution, S&P quarterly rebalance, options-expiry pin/unpin in the last
   hour, month-end pension flow into the close, 15:50 closing-imbalance
   publication. Thread B tested expiry/month-end at the *daily* level (0 of 32);
   the *last-hour* versions are untested.
7. **If options positioning data is obtainable:** GEX / dealer gamma as a
   sharper regime filter than VIX (both threads' mechanism implies this).

**Do not:** re-run pattern searches on 2005–2020 data (both threads exhausted
it); add conditioning rules (12+ failures); trust any Sharpe >3; trade ATM or
OTM 0DTE on a directional signal; attempt inversion.

---

## 7. Directory map

```
unified/
├── CLAUDE.md                      ← this file
├── thread_A_multisleeve/          ← 22 iterations, multi-strategy portfolio
│   ├── HANDOFF.md                 ← Thread A's own complete handoff (read second)
│   ├── STRATEGY.md                ← plain-language 8-sleeve spec
│   ├── ZERO_DTE_PLAYBOOK.md       ← the constrained system
│   ├── LONG_OPTIONS_PLAYBOOK.md
│   ├── ASSESSMENT*.md             ← 20 files, one per iteration
│   ├── mh.py, md.py, strat.py, it5–it21.py, fleet_*.py, etf_test.py
│   └── SPY_DipScore_v1.pine, spy_dipscore_research.py
└── thread_B_inversion/            ← 17 studies, cost law, intraday momentum
    ├── CLAUDE_original.md         ← Thread B's own complete handoff (read third)
    ├── SYSTEM_SPEC.md             ← the system with sources for every number
    ├── RESULTS.md … RESULTS_PART10.md
    ├── stats_engine.py            ← block bootstrap + BH-FDR — CARRY THIS FORWARD
    ├── strategy.py                ← the system: prepare_day, signal, strike, size, entry
    ├── step1–step17_*.py, loader.py, engine2.py
    └── *.pkl, *.csv               ← intermediate results
```

**Read order:** this file → `thread_A_multisleeve/HANDOFF.md` →
`thread_B_inversion/CLAUDE_original.md` → then the specific ASSESSMENT / RESULTS
files as needed. Use Thread B's `stats_engine.py` as the inference standard
going forward; use Thread A's random-entry control and n_eff adjustment
alongside it.

*All results are historical research on 2000–2020 data, not financial advice.
Nothing in either thread has been paper-traded or traded live.*
