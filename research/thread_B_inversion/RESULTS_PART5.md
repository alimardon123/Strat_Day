# Part 5 — The First Real Edge, and Why It Was Hiding

## The mistake in the previous nine tests

Every one asked the same question: **can I predict direction?** That is one of at least
five ways money is made in markets:

| # | quadrant | mechanism | tested? |
|---|---|---|---|
| 1 | **Direction** | predict where price goes | ✅ nine times |
| 2 | **Risk premium** | get paid to hold what others won't | ❌ |
| 3 | **Liquidity provision** | earn the spread instead of paying it | ❌ |
| 4 | **Structural flow** | forced buyers/sellers — rebalances, expiry, margin calls | ❌ |
| 5 | **Information** | know something true that isn't priced | ❌ |

Quadrant 1 is the most competed corner that exists, and it's where costs bite hardest.
Note that every failure in this study came from *paying* the spread thousands of times —
quadrant 3 is literally the other side of that trade.

## Quadrant 2 measured: the variance risk premium

VIX (implied vol) vs SPX realised vol over the following 21 trading days, 2010–2018.

| | value |
|---|---|
| mean VIX | 16.53 |
| mean subsequent realised vol | 12.62 |
| **mean premium** | **+3.25 vol points** |
| premium positive | **82.5% of periods** |
| annualised Sharpe (97 non-overlapping periods) | **+2.10** |
| bootstrap p (monthly blocks) | <0.001 |

**Positive in every single year:**

| 2010 | 2011 | 2012 | 2013 | 2014 | 2015 | 2016 | 2017 | 2018 |
|---|---|---|---|---|---|---|---|---|
| +10.23 | +2.92 | +5.05 | +3.56 | +3.10 | +1.66 | +4.71 | +4.73 | +1.19 |

Sharpe 2.10 is **three times** anything found in the previous nine studies, and unlike
those it survived every statistical guard on the first attempt.

## Why it exists — and why it won't be arbitraged away

This is not an inefficiency. Insurance buyers structurally outnumber sellers: pension
funds, corporates and asset managers must hedge, and they will pay above fair value to do
it. Someone has to take the other side, and they demand compensation.

That compensation is stable **because it is compensation.** The premium doesn't get
competed to zero for the same reason fire-insurance premiums don't — the seller is being
paid for something genuinely unpleasant, not for being clever.

## The unpleasant thing, in the same numbers

| | |
|---|---|
| mean gain per period | **+3.25** |
| worst period (Jul 2011) | **−23.61** |
| ratio | **7.3×** |

**February 2018, as it actually happened:**

| date | VIX | realised vol ahead | premium |
|---|---|---|---|
| 2018-01-26 | 11.08 | 26.01 | **−14.93** |
| 2018-02-01 | 13.47 | 26.81 | **−13.34** |
| 2018-02-02 | 17.31 | 25.74 | −8.43 |
| **2018-02-05** | **37.32** | 20.12 | +17.20 |
| 2018-02-08 | 33.46 | 14.73 | +18.73 |

Read the top rows carefully. For **three weeks before** the event, the position was
already deeply wrong — and nothing on the screen said so. VIX sat at 11, the calmest
readings in the sample, while the volatility that was actually coming was 26. Then VIX
went 13 → 17 → 37 in three sessions. That is the week XIV lost ~96% overnight and was
liquidated.

And note the final rows: the premium was **richest immediately after the crash**, when
nobody was willing to sell it. That is the shape of every risk premium — it pays most
exactly when it is hardest to hold.

## The statistical catch that matters most

| leverage target | worst observed period |
|---|---|
| 10%/yr | −6.0% |
| 20%/yr | −12.1% |
| 40%/yr | −24.2% |

Survivable — **but only against the tail this sample contains.** And:

> Periods with a loss greater than 5 vol points: **5 out of 97.**
> The entire tail risk of this strategy is estimated from **five observations.**

2010–2018 excludes 2008 and 2020. A strategy whose risk lives in the tail cannot be
validated by a nine-year window that happens to contain no true disaster. The Sharpe of
2.10 is real *and* it is measured over a period that systematically understates what it
costs to earn.

This is the same rigour applied everywhere else in the study, pointed at a result I like
rather than one I don't.

## What this actually means

**You were right.** There is a real, persistent, retail-accessible edge with a Sharpe far
above anything in quadrant 1. It was not found by searching harder for a signal. It was
found by asking a different question.

But it is not a loophole, and that distinction is the whole thing. It is a **wage for
risk** — and the risk is real, arrives without warning, and pays you most right after it
has hurt you. The traders who make money here are not the ones who found it. They're the
ones who sized it to survive the five observations they haven't seen yet.

## The three quadrants still untested

- **#3 liquidity provision** — resting limit orders, earning the spread. Step 8 already
  showed this direction produced the largest single improvement anywhere in the study.
- **#4 structural flow** — index rebalance dates, options expiry pinning, month-end
  pension flows, futures roll. Mechanical, dated, and driven by participants who *must*
  trade regardless of price.
- **#5 information** — not automatable, but the only quadrant where being small and
  specialised is a genuine advantage rather than a handicap.

Each is a real research programme. None of them is a search for a better signal.

---

*Historical research, not financial advice. Short-volatility strategies have caused total
losses for retail participants, most recently and most publicly in February 2018.*
