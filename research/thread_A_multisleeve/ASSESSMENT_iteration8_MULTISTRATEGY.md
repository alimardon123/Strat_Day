# ASSESSMENT — iteration 8: diversify the rule. This one works.

Seven iterations of trying to find a better *rule* produced nulls. Iteration 7
showed why, and pointed at the fix: spreading one rule across 23 asset classes
gave 1.78 effective bets because a long-only dip-buying rule manufactures its own
common factor. Spreading four *structurally different* rules across the same
assets gives **2.77**. This iteration builds that system.

**It is the best result in the programme, and it is not what you asked for.**
Read §5 before deciding anything.

---

## 1. The four sleeves, and why each one

Each is a documented, mechanism-backed regularity. None was mined from this data.

| Sleeve | Mechanism | Behaves how |
|---|---|---|
| **S1 MEANREV** | DipScore: buy dips in confirmed uptrends | Earns in grinding bull markets, flat-to-negative in sustained declines |
| **S2 TSMOM** | Hold each asset only while its own 12-month return is positive | **Exits falling markets by construction** — this is the crisis-alpha sleeve |
| **S3 XSMOM** | Long strongest third / short weakest third of the universe | **Market-neutral by construction** — return doesn't depend on direction |
| **S4 TURNMONTH** | Hold equity across the month boundary only | Payroll and pension inflows — a flow effect, not a price pattern |

Sizing: inverse-volatility weights within sleeves (risk parity), each sleeve
volatility-targeted to 10% using a trailing 60-day estimate lagged one day.
Combination is **equal weight**. Costs 4 bp round trip. Everything uses trailing
data only.

**No parameter search was run.** 252-day lookback, terciles, 10% target, equal
weights — all standard, all specified before seeing results. So unlike
iterations 1–7, there is no multiple-testing deflation to apply here.

## 2. Results, 2006–2017

| | CAGR | vol | Sharpe | Sortino | max DD | Calmar |
|---|---|---|---|---|---|---|
| **Combined (equal weight)** | 4.54% | 6.9% | **0.68** | **0.80** | **−11.2%** | **0.41** |
| Combined, levered 2.83× to SPY's vol | **11.98%** | 19.6% | 0.68 | 0.80 | −29.0% | 0.41 |
| Buy & hold SPY | 7.37% | 19.6% | 0.46 | 0.56 | **−56.5%** | 0.13 |

At matched volatility the system returns **12.0% versus 7.4%**, with a drawdown
of **−29% versus −56%**. That is a genuine improvement on buy-and-hold, on both
axes at once.

**Held-out period 2012–2017**, sleeves and combination:

| | Sharpe | max DD |
|---|---|---|
| S1 MEANREV | 0.87 | −15.3% |
| S2 TSMOM | 0.58 | −14.9% |
| S3 XSMOM | 0.75 | −19.5% |
| S4 TURNMONTH | 0.42 | −20.5% |
| **COMBINED** | **1.05** | **−9.1%** |

In the test window the combination beat **every** sleeve on Sharpe while having
a smaller drawdown than any of them. That is diversification working, and it is
the only time in eight iterations that combining things made them better.

**One correction to my own framing:** over the *full* sample the combined Sharpe
(0.68) is slightly *below* the best single sleeve (S1 at 0.74). Diversification
did not beat the best sleeve everywhere — it beat it out-of-sample, and it beat
it decisively on drawdown and year-to-year stability. Since you cannot know in
advance which sleeve will be best, that is still the right way to hold it, but I
shouldn't overstate it.

## 3. Behaviour by market condition — your actual question

| Window | Combined | SPY | Combined maxDD | SPY maxDD |
|---|---|---|---|---|
| GFC crash 2007-10 → 2009-03 | **−3.1%** | −55.4% | −8.4% | −56.5% |
| GFC recovery 2009-03 → 2011-04 | +19.0% | +101.2% | −8.8% | −16.1% |
| EU crisis 2011-05 → 2011-10 | −9.7% | −18.6% | −9.2% | −18.5% |
| Grind higher 2012–2014 | +31.7% | +74.2% | −7.6% | −9.7% |
| Vol shock 2015-08 → 2016-02 | −6.7% | −12.2% | −8.1% | −12.8% |
| Melt-up 2016-03 → 2017-11 | +13.7% | +38.1% | −5.5% | −5.5% |

Year by year, the worst year is **−4.0% (2008) against SPY's −38.3%**. Nine of
twelve years positive.

This is as close to "works in any market condition" as the evidence supports: it
loses far less when equities fall, and it participates partially when they rise.
The mechanism is not clever — S2 mechanically exits anything below its 12-month
average, and S3 has no directional exposure at all.

## 4. The honest price of that

**It lags badly in strong bull markets.** 2013: +16.6% against SPY's +32.3%.
2016: −1.0% against +12.0%. 2009: +3.0% against +23.5%. Averaged over a
bull-dominated sample it earns less in absolute terms unless you lever it, and
levering means borrowing costs I have not modelled.

Other limits, stated plainly:

- **11.6 years only** (2006–2017), constrained by ETF inception dates in this
  dataset. One major crisis, not several.
- **Three of the four sleeves have not been through the scrutiny S1 received.**
  S2, S3 and S4 got standard parameters and one train/test split. They have not
  had the control tests, clustering corrections, or lookahead audits that
  iterations 4–6 applied to S1.
- **S4 is the weakest sleeve by a distance** — Sharpe 0.10 over the full sample,
  and *negative* in the training half. It is also the sleeve closest to the
  "human behaviour creates exploitable rules" hypothesis. The flow effect is
  real and documented; as a standalone trade it is close to worthless after
  costs. That is worth sitting with.
- **No borrowing cost, no shorting cost, no tax.** The levered figure and S3's
  short leg both understate real-world friction.

## 5. What I think you should take from eight iterations

Your premise was that markets, being made of human behaviour, must contain
rules. **That premise is correct, and this iteration is the evidence.** TSMOM,
cross-sectional momentum, mean reversion and turn-of-month flows are all real,
all mechanistically explicable, all measurable here.

Where the premise breaks is the word *undiscovered*. Every one of these is
decades old and published. They are known precisely because they are robust, and
they are modest precisely because they are known — each is worth a Sharpe of
0.4–0.9, not a 70% win rate at 1:2. The reason this iteration succeeded where
seven others failed is that it stopped hunting for a hidden loophole and started
combining small known effects, which is what the number 2.77 buys you.

That is the actual trade in this business: you don't find one large edge, you
combine several small ones and let the correlation matrix do the work. Sharpe
0.68 unlevered with a −11% worst drawdown is not exciting, and it is a genuinely
good system.

**Recommendation:** take the four-sleeve portfolio, give S2/S3/S4 the same
audit treatment S1 received, extend the data past 2017, and paper-trade it. If
you want more, add a fifth *uncorrelated rule* — carry, volatility risk premium,
or a rates-specific trend — not a fifth instrument and not a 411th parameter.
