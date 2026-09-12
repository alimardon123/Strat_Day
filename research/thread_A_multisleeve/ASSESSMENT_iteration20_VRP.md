# ASSESSMENT — iteration 20: the system that wins almost every day, and why you can't have it

You have asked six times, in different words, for a system that is reliably
profitable day after day. This iteration found it. Then it measured what it
costs, and the answer is: exactly what it earns.

---

## 1. The largest edge in the entire study

Using the new 36-year VIX series against SPY, 2000–2026, 6,593 sessions:

| | |
|---|---|
| Mean VIX (implied volatility) | 19.84 |
| Mean subsequent 21-day realised volatility | 16.38 |
| **Mean premium** | **+3.44 volatility points** |
| **Share of days the premium is positive** | **81.8%** |

Implied volatility exceeds subsequent realised volatility roughly **four days out
of five, for twenty-six years.** Nothing else in twenty iterations comes close to
that reliability. It is the volatility risk premium, and it is the compensation
paid to whoever sells insurance against market crashes.

## 2. Traded naively, it does exactly what you asked for

A short-variance sleeve scaled by how rich implied is versus trailing realised:

| Version | TRAIN | TEST | FULL | **daily hit rate** | max DD |
|---|---|---|---|---|---|
| Always short variance | 1.11 | 1.13 | 1.11 | **79.6%** | −57.3% |
| Short only when implied is rich | 1.35 | 1.13 | 1.24 | 67.2% | −41.0% |

**A 79.6% daily win rate**, stable between train and test. That is the number
you have been asking for, and it is real.

## 3. And then the two reasons you can't keep it

**Reason one: the tail.** Daily return skew is **−34.4**.

| Event | Return | Worst single day |
|---|---|---|
| GFC autumn 2008 | −31.9% | **−29.4%** |
| COVID crash 2020 | −38.6% | **−25.5%** |
| Volmageddon 2018 | −1.7% | −1.8% |

Worst five days: −29.4%, −25.5%, −23.8%, −4.8%, −4.6%. **The 79.6% hit rate is
not despite the crash risk — it is the crash risk.** You are paid a small amount
almost every day precisely because occasionally you lose a third of the position
in a session. High daily reliability and catastrophic tail risk are the same
fact viewed from two angles.

**Reason two, and it is decisive: costs eat all of it.**

| Daily cost drag | Sharpe | CAGR | Daily hit |
|---|---|---|---|
| 0 bp | 0.53 | +4.84% | 67.4% |
| **2 bp** | **0.03** | −0.31% | 61.8% |
| 5 bp | −0.73 | −7.57% | 37.5% |

My model is a variance-swap approximation with **zero transaction costs**. Real
implementation means selling straddles or short VIX futures, where round-trip
friction is comfortably above 2 bp a day. **The premium is real and it is
already priced.** It is compensation for a service, and the market makers who
provide the liquidity capture most of it.

## 4. The seductive version, and why it's a mirage

Cap the daily loss — which is what selling put *spreads* instead of naked puts
does:

| Loss cap | Sharpe | CAGR | max DD | daily hit | skew |
|---|---|---|---|---|---|
| none | 0.53 | 4.84% | −39.3% | 67.4% | −34.4 |
| −3% | 1.94 | 8.59% | −19.6% | 67.4% | −4.3 |
| −2% | **2.33** | 9.37% | −15.1% | 67.4% | −2.3 |
| −1% | **3.20** | 10.99% | −9.2% | 67.4% | **+0.5** |

Sharpe 3.20 with positive skew and a 67% daily hit rate. That is a
world-beating strategy — **and it does not exist.** My model caps the loss for
free. In reality that cap is a long option you must buy, and its premium is
priced precisely to offset the tail protection it provides. That is what
no-arbitrage means. The entire apparent improvement from −39% drawdown to −9% is
the cost of the wings, and I did not charge for it.

Even ignoring that, the capped version dies at **3 bp/day** (Sharpe 0.38) — and
option spreads cost considerably more than that to trade and roll.

## 5. Portfolio test — it made things worse

Adding the capped VRP sleeve at a realistic 3 bp/day:

| | TRAIN | TEST | FULL | max DD |
|---|---|---|---|---|
| Two buckets (current) | 0.99 | **1.40** | **1.20** | **−5.26%** |
| Two buckets + VRP | 1.14 | 1.09 | 1.11 | −7.74% |

Lower out-of-sample Sharpe, worse drawdown. **Not added.**

## 6. What this settles

You have been asking for a system that wins nearly every day. It exists, I
found it, and here is its full description: **it is short volatility, it wins 68
to 80 percent of days, it loses roughly 30% of the position in a single session
several times a decade, and after realistic transaction costs it earns
approximately zero.**

That is not a failure of the search. It is the answer. Markets pay for
risk-bearing, and the specific shape "wins almost every day" is the payoff
profile of selling insurance — which is why it is available, why it feels
reliable, and why it periodically destroys the people who scale it up on the
strength of its hit rate. Every large retail volatility-selling blowup in the
last decade, from XIV in February 2018 onward, is this exact trade.

**The system that has survived twenty iterations wins 55% of days, 64% of
months and 72% of quarters, with a −5.3% worst drawdown.** That is a much less
satisfying profile than 80% of days, and it is the one you can actually keep.

## 7. Status

Unchanged and final for this line of work: **two buckets, 50/50. Sharpe 1.20
full-sample, 1.40 out-of-sample, max drawdown −5.26% unlevered.** At 2–3.5×
futures or margin leverage, roughly 12–20% a year with a −11% to −25% worst
drawdown.

The binding constraint remains the confidence interval, not the strategy. The
VIX series now runs to September 2026 — extending the ETF and stock panels past
2017 to match it would narrow that interval and is worth more than any further
search.
