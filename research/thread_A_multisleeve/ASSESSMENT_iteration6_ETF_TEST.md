# ASSESSMENT — iteration 6: the decisive test, run

I said the loop was closed pending one input. The input turned out to be
reachable after all — the Kaggle "Huge Stock Market Dataset" is mirrored on
GitHub, with 1,344 ETF files. So this iteration ran the test ASSESSMENT
iteration 4 §5 pre-registered, and it produced a clean answer to a question I
had not realised I was asking.

**Data:** 26 of the 30 pre-registered index ETFs (SPY, QQQ, IWM, DIA, MDY, RSP,
EFA, EEM, VTI, IJH, IJR, the nine sector SPDRs, EWJ/EWG/EWU/FXI, IYR, SMH),
1999–2017, split- and dividend-adjusted. **A third independent data source** —
neither the series used in iteration 1 nor the minute feed from iterations 1–3.
Rules frozen, 4 bp round trip, matched random control per ETF.

---

## 1. The system replicates. Cleanly.

**SPY on this independent source, 2005–2017:** 130 trades, **74.6% win**,
meanR **+0.120**.
**The original study, different source, 2000–2026:** 267 trades, 73.4% win,
meanR +0.131.

That is about as clean a replication as this kind of work produces. Whatever the
DipScore rules describe, they describe something stable in the data across two
independent vendors and two overlapping-but-different windows.

**Pooled across all 26 index ETFs, wide-stop geometry:** 3,239 trades,
**69.3% win, net R:R 1:0.59, meanR +0.081**, against a control of −0.006.
Excess is **positive in 21 of 26 ETFs (81%)**, median +0.065.

And the contrast with iteration 4 is stark:

| Universe | mean excess | share positive |
|---|---|---|
| 26 index ETFs | **+0.077** | 81% |
| 652 single stocks | +0.003 | 51% (coin flip) |

A 25× gap, in the direction the index-specific hypothesis predicted.

**The 1:2 geometry is negative here too**: excess −0.025, t = −0.36, 40.6% win at
1:1.82. Sixth universe, same answer.

## 2. And then the statistics, which are the real finding

The cross-ETF t on mean excess is **4.16** — if the 26 ETFs were independent
bets. They are not.

> Mean pairwise daily-return correlation across the 26: **0.775**
> Effective independent bets: **n_eff = 1.28**

Twenty-six index ETFs are, statistically, **one and a quarter bets.** Adjusting
for that:

| Test | t / result |
|---|---|
| Naive cross-ETF (assumes 26 independent) | 4.16 |
| **Correlation-adjusted (n_eff = 1.28)** | **0.92** |
| Date-clustered pooled | 0.96 |
| Day-block bootstrap of pooled excess | +0.012, 95% CI **[−0.037, +0.064]**, P(≤0) = 0.32 |
| Deflated bar from 406 configurations | must exceed **2.99** |

Three independent methods of correcting for correlation converge on t ≈ 0.9.
The apparent 4.16 was the same illusion as iteration 4's naive 14.8 — replication
across correlated instruments is not replication.

Worth noting where the disagreement sits: the five ETFs with *negative* excess
include FXI and EWJ, which are the least correlated with the US market. The
lowest-correlation members are precisely the ones that don't confirm.

## 3. What this settles, and what it cannot

**Settled.** The original SPY result was not a data artifact — it replicates on
independent data. It is also not a single-stock effect: the same rules produce
exactly zero excess across 652 stocks and +0.077 across index ETFs. Something
about index-level mean reversion is real in the descriptive sense.

**Not settled, and now provably not settleable this way.** Whether that
something is a tradable edge or a persistent feature of one long US equity bull
sample cannot be decided by adding instruments, because **there is only one US
equity market.** Every additional index ETF adds trades and adds almost no
information. This is why iteration 4's power calculation was answering the wrong
question: the constraint was never the trade count, it was the number of
independent bets, and that number is ~1.3 no matter how many ETFs you load.

That reframes the whole programme. Five iterations went looking for more data.
The binding constraint was never data volume.

## 4. Final scoring

| Done-statement | Verdict |
|---|---|
| 1. ≥200 OOS trades, ≥1:2 net R:R, ≥55% win | **FAIL** — six universes, 1:2 never pairs with a high win rate; on ETFs it is 40.6% at 1:1.82 with negative excess |
| 2. ≥+0.15R over control, CI excluding 0 | **FAIL** — best is +0.077 on ETFs, CI [−0.037, +0.064] includes zero |
| 3. <35% degradation, plateau | Descriptively yes; inferentially moot |
| 4. 2× cost stress | SPY only |
| 5. Reproducible, config count stated | **PASS** — 406 + 4 = **410** |
| 6. Split reporting | **PASS** |

## 5. What I would actually do now

Not another iteration. Three things, in order:

1. **Trade the wide-stop system small and forward.** It replicates across two
   vendors, 26 ETFs and 26 years descriptively, at ~70–75% win and roughly
   +0.10R. The statistical case is weak but the failure mode is mild — it is
   long-only, in confirmed uptrends, with a wide stop, roughly ten trades a
   year. Forward results are the only genuinely new information available, and
   at ~1.3 effective bets, that is now literally true.
2. **Drop the 1:2 target permanently.** It has now failed on daily SPY, minute
   SPX, multi-day holds, 652 single stocks, 246 synthetic indices and 26 index
   ETFs. That is not bad luck.
3. **If you want a second independent bet, leave equities.** Rates, FX, energy,
   metals — the point is decorrelation, not more symbols. Whether a dip-buying
   rule transfers there is a genuinely new question rather than the 411th
   configuration of this one.

The honest summary of six iterations: the system is real enough to describe and
too correlated with itself to prove. That is a legitimate place for research to
end, and it is where I would stop.
