# Part 9 — I Searched It Myself. Here Is What I Found.

## The plan I made

Sixteen studies had concluded the same thing: price history alone does not produce
direction. So I planned around that rather than repeating it — go find information
**outside** SPX price history.

I found it. The repository holds a cross-asset universe I hadn't touched: gold, WTI
crude, US 2-year and 10-year bonds, Nikkei, Nasdaq, FTSE — 25 instruments at 1-minute
resolution, 2005–2020. I pulled **8.3 million bars** across gold, oil, both bond
tenors, the Nikkei and SPX.

## Why this was the right thing to test

These assets trade overnight while US equities are shut. Overnight risk sentiment gets
expressed in them first. If the US open does not fully price that information, the
residual should appear as intraday drift.

That is a **mechanism**, not a pattern — the distinction I said mattered throughout.

And the observability trap from Part 4 was handled explicitly: the signal window ends
**15 minutes before** the US open, the target begins **at** the open. No overlap. This
is the exact bug from step 9, deliberately inverted.

## The result

1,375 aligned sessions (929 train / 446 test), 2013–2018.

| overnight asset | corr (train) | corr (test) | test mean %/day | test t | bootstrap p |
|---|---|---|---|---|---|
| Gold | 0.0604 | 0.0290 | +0.0309 | +0.99 | 0.157 |
| Gold \|z\|>1 | 0.0604 | 0.0290 | +0.0321 | +0.50 | 0.314 |
| Crude | 0.0192 | **−0.0756** | +0.0209 | +0.67 | 0.258 |
| Crude \|z\|>1 | 0.0192 | −0.0756 | −0.0629 | −0.92 | 1.000 |
| **US 10y** | 0.0215 | 0.0517 | +0.0484 | **+1.56** | **0.059** |
| US 10y \|z\|>1 | 0.0215 | 0.0517 | +0.0563 | +0.82 | 0.201 |
| Nikkei | −0.0294 | 0.0409 | −0.0268 | −0.86 | 1.000 |
| Nikkei \|z\|>1 | −0.0294 | 0.0409 | −0.0453 | −0.64 | 1.000 |

Bonferroni floor for 8 tests: p < 0.00625.
**Survivors: 0.**

Every correlation sits between 0.02 and 0.06 — indistinguishable from zero. The best
candidate (10-year bonds, p = 0.059) is ten times short of the bar, and its train mean
was *negative* while its test mean was positive. That's a sign flip, which is what noise
looks like.

---

## My honest assessment

I planned this myself, found data outside everything I'd used before, tested it with a
real mechanism and correct time ordering. It produced nothing. That's seventeen studies.

**I don't think I can find you a directional edge in this data, and I no longer think
more searching will change that.** Not "haven't yet" — the pattern across seventeen
independent attempts is itself the finding. Effects were real repeatedly; none was ever
larger than the cost of harvesting it, and none of the ones with real mechanisms
survived out-of-sample.

What would genuinely change the picture is data I cannot reach from here: live order
flow and market depth, options chains and dealer gamma positioning, or crowded-positioning
feeds. Those aren't excuses — they are the specific inputs where being wrong is
*structural* rather than random, which is the property everything I tested lacked.

## What this project did produce, which is real

| finding | status |
|---|---|
| VIX → today's range, out-of-sample R² **0.54** | robust, actionable |
| cost drag = cost × frequency ÷ vol | explains all 17 studies |
| VIX-scaled sizing: vol-of-vol −39% | real risk improvement |
| variance risk premium: Sharpe 2.10, positive 9/9 years | real, needs 21-day hold |
| 0DTE: your TP intuition was correct (99.5%) | verified against my doubt |
| ITM strikes: median −20.9% vs OTM −50.6% | real execution improvement |
| a Sharpe of 7.2 that was a 4-hour look-ahead | the most valuable thing here |

Six of seven system components are measured and specified. That is a genuinely good
piece of infrastructure. It is not a strategy, because the seventh component is the one
that decides whether money is made.

## What I'd say if you asked me directly

Don't fund a prop account against this. The infrastructure is sound and the signal slot
is empty, and running an empty signal through good infrastructure returns **−6.10% per
trade** — that number is measured, not cautionary.

The two things I'd actually pursue:

1. **Get options chain data.** Dealer gamma positioning is the one directional mechanism
   with a real structural story that retail can reach. This framework takes it directly.
2. **Reconsider the day-only mandate.** The single edge found in seventeen studies —
   Sharpe 2.10, positive in every year — requires a 21-day hold and is structurally
   unavailable under prop-firm rules. That constraint is costing you the only thing that
   worked.

---

*Historical research, not financial advice.*
