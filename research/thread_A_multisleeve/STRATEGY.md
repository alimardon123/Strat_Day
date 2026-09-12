# THE STRATEGY — where we've landed, in plain language

You asked what the system actually looks like now. Here it is without the
statistics.

---

## The one-sentence version

**Eight independent strategies, each doing a different job, each sized to the
same risk, all held at once in equal weight — and nothing else.** No filters, no
regime switching, no clever weighting. Twelve attempts to add cleverness on top
all made it worse.

## Why it's built this way

The first seven iterations looked for one great trading rule. That failed
completely — the best single rule found was worth about 1.3% a year and couldn't
be proven better than random after correcting for how many things I'd tested.

What worked instead was combining several small, honest edges. The key number is
**effective independent bets**. If you hold five strategies that all make money
the same way, you have one bet. If you hold five that make money differently, you
have five, and your risk-adjusted return improves roughly with the square root of
that count. Every improvement since iteration 8 came from raising that number,
never from finding a better rule.

## The eight sleeves

| # | Sleeve | What it does | When it earns |
|---|---|---|---|
| 1 | **DipScore** | Buys SPY dips inside a confirmed uptrend (RSI oversold, closed on the low, new 10-day low, calm tape). ~10 trades/yr, 5-day holds | Grinding bull markets |
| 2 | **Time-series momentum** | Holds each of 25 ETFs only while its own 12-month return is positive, else cash. Monthly | Sustained trends; exits falling markets automatically |
| 3 | **Cross-sectional momentum** | Long the strongest third of those ETFs, short the weakest third. Market-neutral | Dispersion between assets, regardless of direction |
| 4 | **Volatility-managed equity** | Scales SPY exposure inversely to recent volatility — big when calm, small when wild | Calm uptrends; cuts risk before drawdowns deepen |
| 5 | **Short-term reversal** | Buys the past week's losing assets, sells its winners | Choppy, high-volatility tape |
| 6 | **Betting against beta** | Long low-beta stocks, short high-beta stocks, beta-balanced. From a 626-stock universe. Monthly | Steadily; the strongest single sleeve |
| 7 | **Gap-up afternoon** | On days that gap up, buys the S&P around 13:00 ET and holds to the close. ~138 trades/yr | Small but frequent; your daily-trading sleeve |
| 8 | **Volatility term structure** | Trades VXX long or short depending on whether the VIX futures curve is in backwardation or contango | Crises and volatility spikes |

Sleeves 1–6 are daily-to-monthly. Sleeve 7 trades most days. Sleeve 8 flips with
the volatility curve.

## How they combine

Each sleeve is scaled to the **same 10% annualised volatility** using a trailing
60-day estimate, then all eight are held at **equal weight**. That's it. Three
different weighting schemes were tested against equal weight and all landed
within 0.03 Sharpe of each other, so the simplest wins.

## What it produces

| | Value | SPY for comparison |
|---|---|---|
| Sharpe ratio | **1.12** (1.35 out-of-sample) | 0.46 |
| CAGR, unlevered | 5.68% (at 6% volatility) | 7.37% (at 20%) |
| **Max drawdown** | **−6.10%** | −56.5% |
| Winning quarters | ~72% | 74.5% (at 1:0.68 payoff) |
| Worst year | −4.0% (2008) | −38.3% |

Because it runs at 6% volatility, it's designed to be levered. With futures —
where leverage is margin, not borrowing — running it at SPY's 20% volatility
gives roughly **17% a year with a −22% worst drawdown**, against SPY's 7.4% and
−56%.

## The thing it now does that it couldn't before

Until this iteration the system lost money in bad regimes — it just lost far less
than the market. With the volatility sleeve added, it's positive in all three:

| Regime | Before | Now |
|---|---|---|
| Uptrend | +8.85%/yr | +7.76%/yr |
| Downtrend | −0.36%/yr | **+0.63%/yr** |
| High volatility | −1.87%/yr | **+1.93%/yr** |

That's the first version of this system that genuinely earns in every market
condition rather than merely surviving two of them.

## What it is not

- **It is not a high win rate at a big payoff.** It wins ~72% of quarters at
  about 1:1.4. A 60% *daily* win rate would require Sharpe 4.0; the best fund in
  history ran 2–3.
- **It is not a loophole.** Every component is documented in public literature,
  most for decades. The edge is in combining them, not in any one of them.
- **It lags badly in strong bull markets.** 2013: +16.6% against SPY's +32.3%.
- **It is measured on 2006–2017 only.** Sharpe 1.12 has a 95% confidence
  interval of roughly [0.4, 1.8]. That interval, not the strategy, is the
  binding constraint on every decision.

## The one risk that should worry you most

Sleeve 8 is short volatility most of the time, and the data ends **November
2017 — three months before 5 February 2018**, when short-volatility products lost
most of their value in a single session. That event is not in this backtest.

It is sized by volatility target, so its notional is small (about a sixth of
capital at a 10% target against VXX's 61% volatility), and a one-day 33% move
against it costs roughly 5% of the portfolio rather than everything. But
volatility-targeting protects against normal days, not gap days. If you trade
this sleeve, cap its weight explicitly and never scale it up on the strength of
its backtest Sharpe.
