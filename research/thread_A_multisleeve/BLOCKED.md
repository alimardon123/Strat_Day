# BLOCKED.md — iterations 2 and 3

**Status: the plateau rule fired. Two consecutive iterations produced no
improvement in the metric that gates the loop, so I stopped rather than grind a
fourth pass on the same strategy line.**

---

## What iteration 2 did

Took the one instruction ASSESSMENT §6 left open: keep the multi-day hold that
works, use minute data only for entry timing. Extended the harness so a 5-day
trade is resolved **minute by minute across sessions** instead of once per day.

Four entry timings tested against the DipScore signal day, three geometries each:

| Entry | Geometry | TRAIN win / R:R / meanR | TEST win / R:R / meanR |
|---|---|---|---|
| 09:30 open (baseline) | 2.0 / 1.0 | 72.8% · 1:0.52 · +0.095 | 70.0% · 1:0.49 · +0.042 |
| 09:30 open | 1.0 / 2.0 | 43.3% · 1:1.75 · +0.191 | 40.5% · 1:1.53 · +0.027 |
| first VWAP reclaim | 1.0 / 2.0 | 41.8% · 1:1.79 · +0.161 | 41.2% · 1:1.47 · +0.019 |
| VWAP + session-high push | 1.0 / 2.0 | 44.1% · 1:1.60 · +0.145 | 38.8% · 1:1.57 · −0.004 |
| **15:30 entry** | **1.0 / 2.0** | **46.9% · 1:1.60 · +0.220** | **44.2% · 1:1.62 · +0.154** |

**The good news, and it is real:** restoring the multi-day hold restored the
edge that iteration 1 destroyed. 72.8% train / 70.0% test at the wide-stop
geometry reproduces the original daily study on a different instrument, a
different source and a different period. The mechanism diagnosis in ASSESSMENT
§3.3 — *the edge is a horizon effect, not a resolution effect* — is now
confirmed twice.

**The bad news:** no minute-timed entry beat the 09:30 open by more than noise.

## What iteration 3 did — the ablation that settles it

Same signal, same geometry, only the stop-versus-target sequencing changed:

| Resolution | 2.0/1.0 | 1.0/2.0 | 0.75/1.5 |
|---|---|---|---|
| **Daily bars** (stop wins ties) | 71.9% · 1:0.54 · +0.094 | 44.5% · 1:1.65 · +0.177 | 43.5% · 1:1.83 · +0.233 |
| **Minute path** (real sequencing) | 72.8% · 1:0.52 · +0.095 | 46.9% · 1:1.60 · +0.220 | 44.9% · 1:1.82 · +0.270 |

**Minute resolution bought approximately nothing.** Every pair is within noise.
The pessimistic same-bar tie rule I worried about in the daily study was not
costing anything material — the daily numbers were already honest. This closes
the last open hypothesis from ASSESSMENT §6 and it closes it negatively.

One caveat worth stating: this 1:2 geometry shows **+0.177R on SPX 2005–2020**
where the same geometry showed a *negative* out-of-sample result on SPY
2016–2026. That is not a resolution difference — it is period and instrument
variance, and it means neither number is stable enough to trade on.

Sample-size test — does the 1:2 result hold when loosened to reach n ≥ 200?

| Tier | signal days | TRAIN 1.0/2.0 | TEST 1.0/2.0 |
|---|---|---|---|
| A (≥0.55) | 154 | n=74 · +0.234 · t=1.49 | n=45 · +0.286 · t=1.36 |
| B (≥0.35) | 277 | n=113 · +0.220 · t=1.71 | n=77 · +0.154 · t=1.01 |
| C (≥0.20) | 701 | n=227 · +0.178 · t=2.02 | n=147 · +0.045 · t=0.43 |

Loosening buys trades and spends edge, exactly as the daily study found. There
is no threshold that delivers both n ≥ 200 and significance.

## Root cause — why every iteration lands at t between 1 and 2

Not a signal problem. A **statistical power** problem, and it is arithmetic:

Per-trade standard deviation at 1:2 geometry is consistently **~1.35–1.41 R**
across every configuration measured. For t = 2.5 you therefore need:

| True edge | Trades required | Years at Tier B rate | Years at Tier C rate |
|---|---|---|---|
| +0.05R | 5,256 | 465 | 232 |
| +0.10R | 1,314 | 116 | 58 |
| +0.15R | 584 | 52 | 26 |
| +0.20R | 329 | 29 | 14 |
| +0.25R | 210 | 19 | 9 |

The out-of-sample window holds 1,222 sessions — 4.8 years, at most ~166 trades.
**The smallest edge detectable at t = 2.5 with n = 166 is +0.28R.** Any true
edge below that is invisible here no matter how the strategy is built. Every
iteration has landed at t ≈ 1–2 because that is what this sample size does to
an edge of this size. Continuing to iterate on rules cannot fix it — I would be
tuning against noise, which is the specific failure the loop exists to prevent.

## Scoring against the definition of done

| # | Requirement | Result |
|---|---|---|
| 1 | ≥200 OOS trades, ≥1:2 net R:R, ≥55% win | **FAIL** — at 1:2 the win rate is 38–47% across every tier and entry |
| 2 | ≥+0.15R over control, CI excluding 0 | **FAIL** — best OOS t = 1.36, CI includes 0 |
| 3 | <35% degradation, parameter plateau | **FAIL** — Tier B degraded 30% (acceptable) but Tier A 0.75/1.5 flipped sign |
| 4 | Survives 2× cost stress | Not reached |
| 5 | Reproducible, config count stated | **PASS** — ~140 configs now |
| 6 | Split reporting | **PASS** |

## Options, ranked

1. **Accept the wide-stop, high-win-rate version and stop chasing 1:2.** It now
   replicates across two instruments, two data sources and two periods — the
   strongest evidence in the whole study. It is ~1.3R/year. That is a real but
   small edge, and it is the honest product of this work.
2. **Get the sample size the question requires.** Run the identical harness
   across 15–20 uncorrelated instruments rather than 15 more years of one. Twenty
   liquid ETFs at Tier B is ~2,200 trades per decade, which crosses the detection
   threshold in the table above. This is the only route that makes the 1:2
   question answerable, and the code takes a CSV, so it is a loop over files.
3. **Change the payoff engine, not the rules.** A +0.28R detection floor is
   punitive because per-trade variance is high. Reducing variance — scaling into
   the position, or a trailing rather than fixed target — lowers the bar more
   cheaply than raising the edge does.
4. **Stop.** Two independent studies have now put the same win-rate/R:R frontier
   in front of you, and a third has shown the horizon, not the resolution, is
   what carries the edge. That is a settled result, not a failed one.

**Recommendation: option 2.** It is the only one that turns "we can't tell" into
an answer, and it is a mechanical extension of code that already exists.
