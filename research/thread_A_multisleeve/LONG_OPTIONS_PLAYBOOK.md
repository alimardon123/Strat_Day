# THE LONG-OPTIONS PLAYBOOK — what you can actually trade

Your account can only **buy calls and buy puts**. That constraint is more
important than anything else you have told me, and it invalidates most of the
system I built. Here is what survives, tested properly.

---

## 1. What dies immediately

| Sleeve | Why it can't be done |
|---|---|
| Betting-against-beta | Needs a short leg in high-beta stocks |
| Cross-sectional momentum | Long/short by construction |
| Short-term reversal | Long/short by construction |
| Time-series momentum | Needs positions in 25 ETFs held for months |
| Volatility-managed equity | Continuous scaled exposure, not a directional bet |
| Volatility term structure | Requires being short VXX |

**Six of the eight sleeves are gone.** What remains is directional index
exposure — which is the DipScore sleeve, expressed as long calls.

## 2. How the options were modelled

Black-Scholes, with the **VIX close as the implied-volatility input**. VIX is
30-day at-the-money implied vol on the S&P, so it is the right magnitude and it
moves correctly with regime — which is what matters here. Entry at the next
open, exit at the DipScore stop/target/time exit, round-trip bid-ask charged as
a percentage of premium.

This is an approximation. Real SPY options have volatility skew (in-the-money
calls trade slightly cheaper than the ATM implied), which would help modestly.
Treat the numbers as the right order of magnitude, not to the decimal.

## 3. Strike selection is the single biggest decision

| Strike | DTE | win rate | mean return per trade |
|---|---|---|---|
| ATM | 30 | 65.5% | **+0.34%** |
| ATM | 14 | 67.0% | +0.73% |
| 2% ITM | 14 | 70.4% | +3.66% |
| **4% ITM** | **14** | **72.3%** | **+3.93%** |
| 6% ITM | 14 | 72.3% | +2.38% |
| 2% OTM | 30 | 52.4% | **−2.36%** |

**At-the-money is roughly break-even. Out-of-the-money loses money. Four percent
in-the-money is where the edge survives.**

The reason is theta. An ATM call is nearly all time value, so you are paying full
price for decay on a trade whose edge is a 1×ATR move over five days. An ITM call
is mostly intrinsic value — you are buying delta, not optionality, which is what
a directional signal actually needs.

## 4. Bid-ask spread is the whole ballgame

4% ITM, 30 DTE:

| Round-trip spread | win rate | mean per trade |
|---|---|---|
| 0.5% | 71.9% | +3.52% |
| 1.0% | 71.9% | +3.01% |
| 2.0% | 71.5% | +1.99% |
| **4.0%** | 68.9% | **−0.05%** |

**At 4% round-trip the entire edge is gone.** Trade only the most liquid chains
(SPY, QQQ, SPX), only near-dated, and always with limit orders at the mid. If
your fills are averaging worse than 2% round-trip, this strategy does not work
for you — that is the single check that decides everything.

## 5. The recommended configuration

**Signal:** DipScore ≥ 0.35 on SPY (uptrend confirmed by rising 200-day, plus
RSI(2) oversold / closed on the low / new 10-day low / three down days / below
50-day / calm volatility).
**Instrument:** SPY calls, **4% in the money, ~14 days to expiry.**
**Entry:** next open after the signal.
**Exit:** when the underlying hits 1×ATR profit or 2×ATR stop, or after 5 days.
**Never hold into the last few days before expiry** — theta accelerates.

Result over 26 years, 267 trades: **10.2 trades a year, 72.3% win rate, +3.93%
mean per trade, worst trade −56%.**

Loosening the threshold to get more trades makes it worse: at ≥0.25 you get
17.6 trades/year but the mean falls to +1.06%. **The frequency you want and the
edge you want trade against each other, again.**

## 6. Position sizing — the number that decides your account

Everything above is **percent of premium paid, not percent of account.**

| % of account per trade | Annual return | Worst trade | Worst year | Best year |
|---|---|---|---|---|
| 5% | 2.3% | −2.8% | −7.2% | 6.2% |
| 10% | 4.5% | −5.6% | −14.2% | 12.5% |
| **15%** | **6.8%** | −8.4% | **−20.9%** | 19.1% |
| 20% | 8.9% | −11.2% | −27.3% | 25.8% |
| 33% | 14.3% | −18.4% | −42.7% | 44.1% |
| 50% | 20.6% | −28.0% | **−59.8%** | 68.9% |

**This is where your 60–100% ambition meets arithmetic.** To earn 20% a year you
must put half your account into a single option position, and accept a −60%
year. Prop firms typically fail you at a 10% drawdown, which caps you at roughly
**5–10% of account per trade** — meaning realistic returns of **2–5% a year on
this signal alone.**

## 7. The honest summary

Under a long-options-only constraint:

- Six of eight sleeves are untradeable.
- The one that survives works — **72.3% win rate over 26 years**, which is a
  genuinely good and stable number, and it is exactly the "high win rate" you
  have been asking for.
- It fires **ten times a year**, not daily.
- It is destroyed by wide fills and by out-of-the-money strikes.
- Sized to survive a prop firm's drawdown limit, it earns single digits a year.

The constraint, not the strategy, is now the binding limit. If the account ever
permits spreads, futures, or short stock, the eight-sleeve portfolio becomes
available and roughly doubles the risk-adjusted return. Until then, this is the
honest version: one signal, ten trades a year, high hit rate, modest returns,
and strike selection and fill quality mattering more than anything else.
