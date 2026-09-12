# ASSESSMENT — iteration 22: ideas native to 0DTE

You asked for creativity and different angles. Every previous 0DTE test tried
to squeeze a multi-day signal into a same-day instrument. This iteration asked
the opposite question: **what can a 0DTE long option do that nothing else can?**
Two answers, one of which survives.

---

## Idea A — the FOMC straddle

**The insight:** your constraint says "buy calls or buy puts." It does not say
"one at a time." A long call plus a long put at the same strike is a straddle —
a pure bet that the realised move exceeds the implied move. On most days that
loses, because implied volatility exceeds realised 82% of the time (iteration
20). But on days with a scheduled shock, realised can win.

Tested on **121 FOMC statement days, 2005–2020**, straddle bought 13:30 ET,
settled at the close:

| Day type | n | mean afternoon \|move\| | win rate | mean P&L (IV = VIX) |
|---|---|---|---|---|
| Non-FOMC | 3,538 | 0.38% | **15.4%** | **−45.7%** |
| **FOMC** | 121 | **0.67%** | 40.5% | **+6.6%** |

The mechanism is real: FOMC afternoons move **1.8× a normal afternoon**, and at
VIX-level implied volatility the straddle earns +6.6% with 121 observations.

**And then the market prices it.** 0DTE options on Fed days do not trade at the
VIX — implied volatility is bid up specifically because everyone knows the
announcement is coming:

| 0DTE IV relative to VIX | FOMC straddle mean | win rate |
|---|---|---|
| 1.0× | +6.6% | 40.5% |
| **1.3×** | **−18.0%** | 30.6% |
| 1.6× | −33.4% | 23.1% |
| 2.0× | −46.7% | 14.9% |

At 1.3× VIX — conservative for a Fed afternoon — the trade loses 18% and is
consistent in both halves (train −18.6%, test −17.4%). I do not have actual
FOMC-day 0DTE implied vols, so the exact break-even multiplier is uncertain, but
it sits around 1.1× and Fed-day 0DTE IV is documented well above that.

**Verdict: a genuine mechanism, fully priced.** The 1.8× move is real. The
premium you pay for it is larger. This is what an efficiently priced event looks
like, and it is worth knowing precisely rather than assuming.

## Idea B — the last hour, and this one works

**The insight:** end-of-day flows are mechanical. Leveraged ETFs must rebalance
into the close in the direction of the day's move; margin calls and stop-outs
cluster in the final hour; closing-auction imbalances are published at 15:50.
On a big down day, these all push the same way. A 0DTE option with one hour left
is the cheapest possible instrument for a one-hour directional bet.

Tested: **2% in-the-money 0DTE, bought 15:00 ET, one hour to expiry, 1-point
spread, on days that had already moved more than their 70th-percentile
magnitude by 15:00** (threshold from an expanding window — no lookahead).

| Setup | n | win rate | TRAIN | **TEST** |
|---|---|---|---|---|
| Big UP day → buy call (continuation) | 473 | 47.4% | +1.43% | −0.37% |
| **Big DOWN day → buy put (continuation)** | **516** | **52.7%** | **+3.42%** | **+2.77%** |
| Big UP day → buy put (reversal) | 473 | 46.9% | −1.88% | −1.29% |
| Big DOWN day → buy call (reversal) | 516 | 45.0% | −1.64% | −3.81% |

**One of four survives, and it is the one the mechanism predicts.** On big down
days the last hour averages **−0.038%** on the underlying, against +0.026% on
big up days — the down-day pressure is stronger and it holds in both halves of
the sample. The put version earns +3.42% on train and **+2.77% on test**, at a
52.7% hit rate, roughly 34 trades a year.

Buying the dip into the close on down days — the intuitive trade — loses
**−3.81%** out of sample. The forced sellers are not done at 15:00.

Caveat: chosen from four tested setups, so the full-sample figure is mildly
optimistic. The test-period number is clean.

## The 0DTE book, as it now stands

Two signals, both long-only naked options, both surviving out of sample:

| Signal | Instrument | Entry | Trades/yr | Win | TEST mean |
|---|---|---|---|---|---|
| Gap up > 0.3% at the open | 2% ITM **call** | ~13:00 | ~65 | 53% | +1.14% |
| Big down day by 15:00 | 2% ITM **put** | 15:00 | ~34 | 53% | +2.77% |

Roughly **100 trading days a year**, both sides of the market, and the put leg
is the stronger of the two — which matters because it is the one that earns when
everything else in your account is losing.

At 2% of account per trade (a prop-firm drawdown limit) that is roughly **3–4%
a year**. At 5% per trade, 8–10% with a worst year in the −30% range.

## Honest summary of the 0DTE search

Four distinct 0DTE constructions have now been tested: the compressed daily
signal (dead), the afternoon call (survives, thin), the event straddle (real
mechanism, priced away), and the last-hour put (survives, the best of them).
The pattern across all four: **the edges that survive are the ones tied to a
mechanical flow that must happen regardless of price** — end-of-day rebalancing,
gap-driven repositioning. The ones that die are bets on information the market
already has.

That is a usable principle for finding more: look for flows with a deadline, not
for patterns in price.
