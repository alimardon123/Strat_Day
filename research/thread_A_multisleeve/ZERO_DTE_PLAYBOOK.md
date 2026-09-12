# 0DTE, LONG-ONLY — the complete picture

Your constraint is **same-day-expiry options, buying calls or puts only.** This
is the tightest constraint in the study and it eliminates nearly everything.

---

## 1. What 0DTE removes

The DipScore sleeve — the one that survived under the long-options constraint,
with a 72.3% win rate over 26 years — **holds for five days.** It cannot be
expressed in an instrument that expires this afternoon. It is gone.

Of everything built across twenty-one iterations, exactly one thing remains
tradeable: **the intraday gap-up afternoon sleeve**, buy around 13:00 ET and
exit at the close.

## 2. Strike selection is not a preference — it is the entire trade

Buying at 13:00, holding to the 16:00 close, gap-up days, 2,001 trades:

| Strike | Spread | Win rate | Mean per trade |
|---|---|---|---|
| **ATM** | 0.5 pts | **17.4%** | **−52.6%** |
| ATM | 2.0 pts | 14.4% | −63.2% |
| 1% ITM | 1.0 pts | 47.3% | −2.4% |
| **2% ITM** | 0.5 pts | 52.4% | **+1.05%** |
| 2% ITM | 1.0 pts | 50.9% | +0.55% |
| 2% ITM | 2.0 pts | 48.6% | −0.44% |

**At-the-money 0DTE loses 53% per trade and wins 17% of the time.** With three
hours left, an ATM option is pure time value and it expires worthless unless the
index makes a large move. Break-even on an ATM 0DTE at VIX 16 requires a
**0.28%** afternoon move; the median afternoon move is **0.21%**. You are
structurally on the wrong side of that distribution.

**Deep in-the-money is the only viable structure.** A 2% ITM 0DTE call has delta
≈ 1.00 and almost no time value — break-even is 0.03% instead of 0.28%. It is,
functionally, a synthetic futures position with a defined maximum loss.

## 3. And that is the problem

| Spread | Index move needed just to break even |
|---|---|
| 0.5 pts | 0.010% |
| 1.0 pts | 0.020% |
| 1.5 pts | 0.030% |
| 2.0 pts | 0.040% |

Against that, the gross edge available:

- Afternoon edge on gap-up days: **0.0486%**
- Afternoon edge, all days: 0.0118%

**Your entire edge is 4.9 basis points and your spread is 1–4 basis points.**
The trade works or fails entirely on fill quality. There is no strategy
refinement that changes this — it is arithmetic.

## 4. Out-of-sample results

At a realistic 1-point spread:

| Condition | n | Win rate | TRAIN | TEST |
|---|---|---|---|---|
| Gap up (base) | 2,001 | 50.9% | +1.28% | **−0.29%** |
| **Gap up + VIX above median** | 910 | 53.1% | +3.06% | **+0.87%** |
| **Gap up > 0.3%** | 1,030 | 53.1% | +3.90% | **+1.14%** |
| Gap up + VIX below median | 946 | 48.3% | −1.79% | −0.72% |
| Gap down (buy the dip) | 1,637 | 48.1% | −4.00% | −1.55% |
| All days | 3,659 | 49.6% | −1.11% | −0.88% |

**Two conditions survive out of sample**, and they are the same idea: trade only
when the day is big enough for a 5 bp edge to fit inside it — a gap larger than
0.3%, or elevated VIX. The base gap-up version does not survive; the unconditional
version loses; buying dips loses badly.

## 5. The configuration, if you trade this

- **Signal:** SPY/SPX gaps **up more than 0.3%** at the open (or gaps up at all
  with VIX above its running median).
- **Entry:** ~13:00 ET.
- **Instrument:** 0DTE call, **2% in the money**. Never at-the-money. Never
  out-of-the-money.
- **Exit:** at the close, or let it settle.
- **Frequency:** roughly 65–70 days a year — about 1–2 a week.
- **Expected:** ~53% win rate, ~+1% per trade on premium out of sample.

**Position sizing, which decides everything:**

| % of account per trade | Annual return | Worst year | Worst trade |
|---|---|---|---|
| 2% | +1.5% | −14.1% | −2.0% |
| 5% | +4.4% | −32.2% | −5.0% |
| 10% | +10.5% | −55.3% | −10.1% |
| 20% | +23.6% | −82.2% | −20.2% |

Those worst-year figures use the *full-sample* mean, which is roughly double the
out-of-sample mean — so treat them as optimistic on return and accurate on risk.
A prop firm with a 10% drawdown limit constrains you to roughly **2% per trade**,
which is about **1–2% a year**.

## 6. My honest assessment

Under 0DTE long-only, the edge available to you is about **5 basis points per
trade**, and your transaction cost is **1–4 basis points**. That leaves 1–4 bp.
It is real — two conditioned versions survive out of sample — but it is thin
enough that your broker's fill quality, not your strategy, determines whether
you make money.

Three things follow:

1. **Measure your actual fills before trading size.** Place ten 2%-ITM 0DTE
   orders at the mid and record the round-trip cost in index points. If it is
   consistently above 1.5 points, this does not work and no refinement will fix
   it.
2. **Never trade ATM or OTM 0DTE on a directional signal.** −53% per trade at a
   17% hit rate is not a variance problem, it is a structural one.
3. **The constraint is costing you most of the opportunity.** The same signal in
   ES futures costs ~0.5 points round trip instead of 1–2, and the five-day
   DipScore signal — 72% win rate over 26 years — becomes available again with
   any instrument that lasts more than a day. If the prop firm ever offers a
   futures or longer-dated product, that is worth far more than any further
   optimisation of the 0DTE version.
