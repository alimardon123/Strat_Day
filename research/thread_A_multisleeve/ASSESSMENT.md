# ASSESSMENT — minute-level 1:2 study

**Verdict: the target was not reached, and the data says it is not reachable
this way. Done-statement 1 fails.** Below is the bar that was set, where the
result landed, and the root cause.

---

## 0. Data — the first thing that limits this study

Nothing was attached, and this sandbox can only reach GitHub, so I substituted a
proxy and am flagging it up front: **1-minute S&P 500 index data (OANDA
SPX500_USD), not SPY.**

- 4,011,719 raw minute bars, 2005-01-02 → 2020-05-14.
- Timezone was not documented, so I resolved it empirically: mean tick-volume by
  hour peaks at 13:00–15:00 and again at 19:00–20:00 with a midday trough — the
  classic U-shape — which fixes the timestamps as UTC. After conversion to
  America/New_York and filtering to 09:30–16:00, the U-shape reads
  53 → 22 → 37 ticks per bar across the session. That is the confirmation.
- After RTH filtering and dropping short sessions: **1,383,838 bars over 3,661
  days.** Zero OHLC violations, 3.83% zero-range bars, 16 minute-returns above 2%.

**Three caveats that matter for how much you should trust what follows:**
1. It is the index, not the ETF. Intraday shape tracks SPY closely during RTH,
   but this is a CFD feed — its "volume" is a broker tick count, not share
   volume, so no genuine order-flow or volume-profile hypothesis could be tested.
2. Coverage ends 2020-05-14, so the last six years are absent.
3. 2017 has a large feed gap (~145 usable days vs ~250).

Split: **train 2005–2014 (2,439 days), test 2015–2020 (1,222 days)**, fixed
before any strategy was run and never re-tuned on.

## 1. The harness, and why you can believe the numbers

Built and validated before any strategy logic, per the protocol. Entry on the
open of the bar *after* the signal bar; stop and target resolved minute by
minute; **same-bar touches of both book the stop**; no overnight carry; costs of
$0.01 spread equivalent plus 0.5 bp slippage per side.

Sanity test on a zero-drift random walk, five geometries:

| stop / target | resolved win % | geometric prior |
|---|---|---|
| 3 / 6 | 29.8% | 33.3% |
| 6 / 3 | 69.8% | 66.7% |
| 4 / 4 | 49.9% | 50.0% |
| 2 / 4 | 33.4% | 33.3% |
| 4 / 2 | 68.1% | 66.7% |

The residual negative meanR in that test turned out to equal the modelled
slippage divided by the risk distance, to three decimals — 0.2 points of
slippage on a 2-point stop is exactly the −0.10R observed. The harness is not
biased; that was the cost term doing its job.

## 2. What was tested

Five hypothesis families, hardest-payoff first, ~100 configurations total
(count stated so t-statistics can be deflated for multiple testing):

| Family | Mechanism | Verdict |
|---|---|---|
| H1 Opening-range break (±VWAP filter) | first 30 min sets the auction boundary; a decisive break extends | **Significantly negative, both directions** |
| H2 Prior-day-low sweep + reclaim | resting stops run, auction rejects, trapped sellers fuel reversal | Best survivor on train, **fails out of sample** |
| H3 VWAP 2σ band reversion | VWAP is fair value for benchmarked flow | Flat, no edge over control |
| H4 First-hour range fade | opening range brackets non-trend days | Negative |
| H5 Afternoon momentum continuation | close-oriented flow extends session direction | Best raw t on train (1.18), not significant |

## 3. The three findings that actually matter

### 3.1 The frontier at minute resolution is *worse* than at daily resolution

Measured with matched random entries across the full sample:

| Target (×R) | Win rate | Net R:R | mean R |
|---|---|---|---|
| 0.5 | 67.2% | 1:0.37 | −0.089 |
| 1.0 | 50.5% | 1:0.82 | −0.088 |
| 2.0 | 35.2% | 1:1.65 | −0.072 |
| 3.0 | 29.7% | 1:2.17 | −0.066 |
| 4.0 | 27.8% | 1:2.42 | −0.055 |

To reach a **net** 1:2 you need a target near 3×R, and the win rate there is
**~30%** — not 55%, not 70%. Going to minute bars did not bend the frontier;
it moved the whole curve down, because every entry now pays the cost twice at a
much smaller risk distance.

### 3.2 Cost drag is the hurdle, and it is large

The random-entry control sits at **−0.05R to −0.09R per trade** everywhere. That
is pure friction. Any minute-level system must generate more than +0.09R gross
just to reach break-even, before it earns anything. On daily bars the same
control was **+0.02R** — friction there is a rounding error. This single number
is why intraday is a harder game than the daily study suggested, and it is
structural, not a tuning problem.

### 3.3 The daily edge is a multi-day effect and does not survive compression

The most valuable experiment: I rebuilt the validated daily DipScore signal from
these minute bars (277 signal days) and tried to convert it to 1:2 by placing the
stop at intraday structure instead of 2×daily-ATR.

| Entry / stop | Target | Win | Net R:R | mean R | t |
|---|---|---|---|---|---|
| 09:30 open, stop under 30-min low | 2×R | 31.8% | 1:1.55 | **−0.192** | −2.53 |
| 09:30 open, 0.5×ATR stop | 2×R | 43.8% | 1:1.20 | −0.032 | −0.49 |
| 09:30 open, 1.0×ATR stop | 1×R | 53.3% | 1:0.87 | −0.004 | −0.09 |
| 09:30 open, 2.0×ATR stop | any | 53.3% | 1:0.82 | −0.010 | −0.47 |

Tightening the stop to intraday structure made it **significantly worse**
(t = −2.53), and confining the trade to one session removed the edge entirely.
Root cause: the daily system's average hold was five *days*. The edge is
multi-day mean-reversion drift. A one-session window doesn't contain it, and a
tight intraday stop gets taken out by noise before the drift arrives. The win
rate falls faster than the payoff rises — which is the frontier, restated.

### 3.4 The one statistically robust intraday result is negative

Opening-range breaks lose significantly in **both** directions
(long t = −2.37, short t = −2.25 at 2×R; long t = −3.44 at 1×R). Symmetric loss
means this is a false-breakout-plus-cost tax, not a tradable short edge — fading
it (H4) also lost, because the fade pays the same friction.

## 4. Scoring against the definition of done

| # | Requirement | Result |
|---|---|---|
| 1 | ≥200 OOS trades, ≥1:2 net R:R, ≥55% win | **FAIL** — at 1:2 the achievable win rate is ~30% |
| 2 | ≥+0.15R over matched random control, CI excluding 0 | **FAIL** — best OOS candidate was −0.044R, t = −0.97 |
| 3 | <35% OOS degradation, parameter plateau | **FAIL** — best candidate flipped sign train→test |
| 4 | Survives 2× cost stress | Not reached; nothing passed 1× |
| 5 | Reproducible from one script, config count stated | **PASS** — bundle attached, ~100 configs |
| 6 | Regime / time-of-day / long-short reported separately | **PASS** — all families run per direction |

No Pine Script was produced. Phase 6 translates *the surviving rule set*, and
nothing survived. Shipping a Pine strategy for a rule set that failed its own
out-of-sample gate would be the dishonest version of this deliverable.

## 5. What would have to be true for 1:2 with a high win rate

1. **A structurally smaller cost-to-risk ratio.** At ~0.08R of friction per
   trade, you need gross edges that are rare. Either trade a larger risk distance
   (which pushes you back toward multi-day holds) or an instrument with cheaper
   round-trip friction relative to its volatility — MES/ES futures rather than
   SPY, where commission plus one tick is a smaller fraction of a comparable stop.
2. **Real order-flow data, which this feed cannot provide.** Every hypothesis
   here used price and a tick count. The setups that plausibly *do* produce
   asymmetric intraday payoffs — absorption at a level, delta divergence,
   sweep-versus-passive at the sweep low — need actual trade-side and book data.
   That is the single biggest untested branch, and it is untestable without a
   different data source.
3. **Accepting a lower win rate.** A ~30% hit rate at 1:2.2 net is a coherent
   system if the entries beat the control. Nothing here did, but that is the
   part of the frontier where a 1:2 payoff actually lives. Asking for 55–70%
   *and* 1:2 is asking to be off the frontier entirely, and two independent
   studies — daily and now minute — have now put the same curve in front of you.
4. **A different horizon, not a different resolution.** The evidence points the
   opposite way from the original hypothesis: your edge got *worse* as the
   holding window shortened. The productive direction is longer holds with wider
   stops, where friction is negligible, not shorter ones.

## 6. What I would do next

- Re-run this exact harness on **real SPY 1-minute bars, 2020–2026**, to confirm
  the negative result isn't a CFD-proxy or a pre-2020-regime artifact. The code
  takes a CSV; nothing else changes.
- Test the **multi-day** DipScore with intraday *timing* only — same 5-day hold
  and wide stop as the validated daily version, but enter on the first
  minute-level reclaim of VWAP rather than at the open. That keeps the drift
  window intact and only asks minute data to improve the fill, which is the one
  thing this study suggests it can do.
- If intraday remains the goal, move the instrument to MES futures and get
  order-flow data. Without that, the friction arithmetic in §3.2 is decisive.
