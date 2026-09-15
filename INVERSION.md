# INVERSION.md — what traders do wrong, and what the inverse of each mistake means for this account

Synthesis of three evidence files: `notes/inversion/u1_retail_failures.md` (U1, retail failure
modes), `notes/inversion/u2_0dte_prop.md` (U2, 0DTE/prop-firm failure modes), and
`notes/inversion/u3_self_audit.md` (U3, this programme's own record). Every external number below
carries its source id in the form `U1-Sxx` or `U2-Sxx`; every internal number carries a `file:line`
or `out/` path exactly as U3 gives it. Where U1 and U2 disagree on a number for the same
underlying source, both values are reported (see §1 row 3). No trading advice; "candidate,"
"hypothesis," and "effect" are used throughout in place of "edge exists."

## 0. The constraint that governs everything

Verbatim, `ACCEPTANCE.md:9-12`:

> The prop account permits ONLY 0DTE options, long-only, naked calls or puts. No selling,
> no spreads, no futures, no shares, no overnight holds. Daily loss limit 3–5% (base case
> 4%), evaluated on marked intraday P&L. Every deliverable must be tradeable under it. The
> own-account track (stock account with options approval) is secondary.

Inversion, in this document, means one specific move: for every documented way a retail trader or
day trader loses money, identify the role that is *losing* (almost always: long-only option buyer,
overtrading retail account, aggressive/marketable order sender, attention-chaser, disposition-effect
holder), name who structurally takes the other side of that loss (market maker/wholesaler,
premium seller, patient liquidity provider, informed counterparty, or the prop firm itself), and
then ask a single question of the constraint quoted above: can this account occupy that other,
winning side without selling, without holding overnight, without holding shares, and without being
the market-making intermediary? Section 1 answers that question for every failure mode the two
research units found. The honest answer, counted at the end of §1, is that it can occupy that side
almost nowhere by construction — which is itself the finding this document exists to state plainly
rather than paper over.

## 1. The taxonomy: failure modes, who profits, and what the inverse is

Duplicates merged across the two files (named so nothing is silently double-counted):
- Disposition effect: `U1-S3`, `U1-S19` + `U2-S25` (row 8).
- Overconfidence / overtrading / turnover: `U1-S1`, `U1-S2`, `U1-S4`, `U1-S12` + `U2-S26` (row 9).
- Attention-driven buying: `U1-S12`, `U1-S13` + `U2-S23`, `U2-S24` — `U1-S13` and `U2-S24` are the
  *same paper* (Barber, Huang, Odean & Schwarz 2022) cited under different ids in the two files (row 10).
- Excess leverage / leveraged-product design: `U1-S10`, `U1-S15`, `U1-S16` + `U2-S19`, `U2-S20` —
  `U1-S10`/`U2-S19` (Heimer & Simsek) and `U1-S15`/`U2-S20` (ESMA) are each the same source under
  different ids in the two files (row 13).
- Trading concentrated at the market open: U2's own Mode 8 and its §2b item 9 are the same finding,
  restated once inside U2 itself ("this mode duplicates Section 2's Mode 8 by design") (row 6).
- Cost/spread drag and adverse selection on marketable orders: `U1-S5`, `U1-S21` + `U2-S01`,
  `U2-S07`, `U2-S31` (row 1).
- No-overnight mandate discarding the overnight return component: U2's §2b item 3 and its §3 Rule 6
  both cite `U2-S18` for the same overnight/intraday split (row 21).
- Retail option-trade anatomy: `U1-S21` and `U2-S08` are the *same paper* (Bogousslavsky & Muravyev
  2024, "An Anatomy of Retail Option Trading," SSRN id 4682388) cited under different ids in the two
  files (rows 1, 3, 4, 18, cited together below). The two files disagree on the dataset's headline
  size — U1 states "~$20 billion," U2 states "$15bn" — reported here as a disagreement, per the
  introduction's promise above that where U1 and U2 disagree on a number for the same underlying
  source, both values are reported.

| # | Failure mode | Class | Strongest quantified evidence | Who profits and through what channel | The inverse, mechanism-shaped | Reachable under the constraint? | Already tested here? | Testable on branch data? |
|---|---|---|---|---|---|---|---|---|
| 1 | Bid-ask spread captured by market makers/wholesalers when retail crosses the spread; adverse selection on marketable orders | structural-cost | avg. 12.6% bid-ask spread on retail-preferred cheap/short-dated options (`U2-S01`); "virtually all" Taiwanese retail losses traced to aggressive orders, 3.8pp/yr aggregate penalty (`U1-S5`); avg. option trade −0.93% vs 3.7% typical spread (`U1-S21`/`U2-S08`) | Wholesalers (~90% of options PFOF to 3 firms, `U2-S01`) and brokers via PFOF rebates (28–42.7¢/100 shares, `U2-S31`); execution timing recovers only ~25% of the naive cost (`U2-S07`) | Continuously quote both sides and warehouse/hedge the resulting inventory | AVOID-ONLY — full capture requires being the intermediary/market maker (SELLING); resting limit orders at the mid can reduce, not capture, the cost | no — this programme has never tested being a liquidity provider | no data — option shards (`data/ext/spy_0dte_1min_2024/2025/2026.csv.gz`) are trade prints only, no bid/ask quotes (U3 §C) |
| 2 | Retail overpays implied volatility ahead of scheduled events that don't fully materialize | behavioural + statistical-method | retail options losses of 5–9% (10–14% for high-expected-volatility announcements) around single-stock earnings (`U2-S02`) | Pre-event vega/theta sellers (option writers, often market makers laying off risk) who collect the gap between elevated IV and realized vol | Be short vega into the event and hold through the event window | NO — requires SELLING and typically OVERNIGHT | A42 E1/E3, killed: daily straddle loses 7.0% of premium, non-FOMC 13:30 straddle loses 17.2% — same direction as `U2-S02`'s overpaying story, from the buyer's side (`SCORECARD.md:78-79`; `ASSESSMENT.md:124-129`) | yes — `data/ext/spy_0dte_1min_2024/2025/2026.csv.gz` (already used, A42) |
| 3 | Aggregate 0DTE retail losses are large and persistent (headline dollar figures disagree between the two files) | product-design | "$358,000 a day" since May 2022, >$125M cumulative, via Bloomberg coverage of Beckmeyer/Branger/Gayda (`U1-S20`) and "$241,000 on an average day," Feb 2021–Sept 2023, same SSRN working paper 4404704 (`U2-S03`) — both real numbers, but different statistics, not a draft-version guess: per the independent citation audit (`notes/inversion/u5_citation_audit.md`), $358,000/day is the post-16-May-2022 subsample, present in both the paper's March-2023 original and its Dec-2023 revision; $241,000/day is the whole-sample figure of the Dec-2023 revision (Feb 2021–Sept 2023); the March-2023 original's own whole-sample figure was $184,000/day. Each figure is tagged to its own window/version here; none is picked as more authoritative. Also: 0DTE trades underperform non-0DTE by 4.7pp, t=−10 (`U1-S21`/`U2-S08`) | The premium seller/wholesaler on the other side of the buy flow | Sell/write the 0DTE contracts retail is documented buying | NO — requires SELLING | consistent direction with A42 (buyer loses 7.0–17.2% of premium, `SCORECARD.md:78-79`) and A43 (seller side FAILS on cost, `SCORECARD.md:85-89`) | yes — `data/ext/spy_0dte_1min_2024/2025/2026.csv.gz` |
| 4 | Long-only 0DTE buying is the minority pattern; documented "sophisticated" SPX 0DTE retail flow is dominated by short-premium, defined-risk structures | product-design + behavioural | 95% of SPX 0DTE retail trades use capped-risk strategies, >50% of notional is multi-leg, dominant strategies are short verticals/iron condors "rather than long-call lottery bets" (`U2-S11`); typical retail trade is a one-day S&P 500 index call held ~1 hour with no evidence of compensating positive skew (`U1-S21`/`U2-S08`) | Whoever is short when the option expires worthless — the premium seller, market maker, or another retail trader running the opposite structure | Sell/write defined-risk multi-leg spreads (short verticals, iron condors/butterflies) | NO — requires SELLING and SPREADS | YES, directly — A43 (Track C) tests exactly this structure; S1/S2/S3 all FAIL at $0.10/leg (`SCORECARD.md:85-89`; `TRACK_C.md:55-67`) | yes — already tested (`data/ext/spy_0dte_1min` shards) |
| 5 | Theta/time-decay acceleration compressed into the final session hours | structural-cost + risk-management | $241,000/day aggregate 0DTE loss (whole-sample, Feb 2021–Sept 2023, `U2-S03`; see row 3 and `notes/inversion/u5_citation_audit.md` for the window/version tagging of this figure) in an instrument whose full remaining time value decays within one session; a purpose-built ultra-short-tenor pricing model is needed because off-the-shelf models misstate the decay path (`U2-S05`) | The option writer, who collects the full decay whenever the underlying fails to move enough, fast enough | Be short the option (the writer), collecting decay | NO — requires SELLING | YES on both sides — A42 (buyer, confirms decay drag) and A43 (seller, FAILS on cost) (`SCORECARD.md:78-79`, `85-89`) | yes — already run, on `data/ext/spy_0dte_1min_2024/2025/2026.csv.gz` (A42/A43) |
| 6 | Trading concentrated at the market open, the session's widest effective spreads | behavioural + structural | retail options trades "cluster near market opens," with worse performance and more negative overnight returns than institutions (`U2-S27`; mini-options data, u2's own caveat at u2:99); 58–77% of SPX 0DTE retail notional is complex orders (`U2-S11`) — U2 §5 (u2:228) attributes the near-the-open timing claim to S27, not S11; S11 supports only the complex-order-share statistic | Liquidity providers quoting their widest effective spreads at the open, capturing more spread on open-clustered orders | Be the compensated liquidity provider (quote/be short optionality) at the open | AVOID-ONLY — capturing the spread requires SELLING/being the intermediary; the account can avoid entering at the open | indirectly — A39 T2 (09:31 entry, +0.12 pts, `SCORECARD.md:54`) underperforms T1 (10:00 entry, +2.20 pts, `SCORECARD.md:53`); but "never fires at the open" is false — A42 E1 (`SCORECARD.md:78`), A43 S1/S3 (`SCORECARD.md:85,87`) and A39 T2 itself all enter at 09:31; only A39 T1 and A44 avoid the open by design | partially — entry-timing effect testable on branch minute+option data; effective-spread widening itself needs quote data (no data) |
| 7 | Lottery/skewness preference in security selection (buying positively-skewed, lottery-like payoffs) | behavioural | investors overweighting lottery-type stocks "typically earned 2 to 3 percent less than other investors" (`U1-S11`) | Deadweight loss from overpaying for skewness, plus whoever sells/issues the overpriced lottery-like security | Sell/short the overpriced skew | AVOID-ONLY — capturing the premium requires SELLING; the account can avoid instruments chosen for skew/lottery appeal | YES — the programme committed and then killed exactly this mistake: ATM 0DTE 17% win rate at −53%/trade; OTM median −50.6% vs ITM median −20.9%; killed, codified as a permanent non-goal (`research/CLAUDE.md:59,210`; `ACCEPTANCE.md:118`) | yes — already run, on `data/raw/oanda_SPX500_USD.parquet` (pre-2020 Oanda feed; Thread A it22, Thread B step15) |
| 8 | Disposition effect: selling winners early, holding losers too long | behavioural | investors "1.5 to 2 times more likely to sell winning stocks than losers" (`U2-S25`); strong preference for realizing winners over losers, costly after tax (`U1-S3`); resulting underreaction yields "monthly alphas of over 200 basis points" to those trading against it (`U1-S19`) | Momentum-style traders who exploit the predictable underreaction (`U1-S19`); the tax authority in the taxable-account version | Hold through the multi-week/month drift window and take the other side of the underreaction | NO — requires OVERNIGHT (multi-week hold) and SELLING (short leg); the account's same-day-exit mandate also makes it structurally unable to commit this mistake | no | no data — needs per-position unrealized-gain tracking across a multi-day hold and event/news flags not held on the branch |
| 9 | Overconfidence-driven overtrading; turnover erodes returns | behavioural | most-active-trading households earned 11.4%/yr vs 17.9% market return (`U1-S1`); 93% of >1 crore Indian equity F&O traders lost money FY22–FY24, aggregate losses >₹1.8 lakh crore (`U2-S26`); bought stocks underperform sold stocks by ~3.3pp (`U1-S4`) | Brokers (commissions/fees) and market makers/liquidity providers capturing spread on every extra round-trip | Be the fee-collecting intermediary or standing liquidity provider on someone else's round-trips | AVOID-ONLY — the winning role is structurally an intermediary, not a peer trader; the account's own 0DTE/no-overnight mandate forces a full round-trip every trading day regardless (`U2` §2b item 1 caveat) | no — not tested as a hypothesis; the round-trip cost is unavoidable by design | no data — no counterparty-identification data on the branch's trade-only shards |
| 10 | Attention-/sentiment-driven buying (chasing high-attention names) | behavioural | intense Robinhood buying forecasts −4.7% average 20-day abnormal returns for the day's most-bought names (`U1-S13` / `U2-S24`); sensation-seeking/overconfident investors trade more with no performance gain (`U1-S12`) | Sellers into the attention-driven spike (informed holders, market makers unwinding inventory) | Short into the attention spike and hold ~20 trading days | NO — structurally inapplicable: single index underlying / equities-shares finding (no per-name selection is possible on a single-index 0DTE account, and capturing the reversal would in any case require SELLING and OVERNIGHT) | no | no data — no per-name attention/volume-spike flags on the branch; also an equities/SHARES finding, not options |
| 11 | Correlated ("herding") retail order flow | behavioural | 37,000 German retail investors tend to be "on the same side of the market" over the same day/week/month/quarter; correlated flow predicts subsequent returns (`U1-S17`) | Institutional/informed counterparties who anticipate or trade against the correlated flow | Trade against a cohort's correlated flow, holding up to a quarter | NO — structurally inapplicable: single index underlying / equities-shares finding (a single account has no cohort to trade against or independently of, and capturing the profit would in any case require OVERNIGHT, multi-day to multi-month) | no | no data — no retail order-imbalance data on the branch |
| 12 | Wealth transfer from small to large/informed households in bubble-crash cycles | behavioural | in China's 2014–15 bubble-crash, the top 0.5% of households gained while the bottom 85% lost 250B RMB, 30% of either group's initial equity wealth (`U1-S18`) | Large, well-capitalized households selling into the peak and/or buying the trough | Be a large household holding equity positions through weeks/months of the cycle | NO — requires SHARES and OVERNIGHT | no | no data — single-country administrative account data, not held on the branch |
| 13 | Excess leverage / leveraged-product (CFD, retail FX) design amplifies losses | structural + risk-management + product-design | 2010 US FX leverage cap alleviated high-leverage traders' losses by 40% (`U1-S10` / `U2-S19`); EU CFD leverage cut 30:1→2:1; 74–89% of retail CFD accounts lose, avg loss €1,600–€29,000 (`U1-S15` / `U2-S20`); UK FCA: 82% of CFD clients lose, avg £2,200 (`U1-S16`) | Brokers/CFD dealers, often acting as principal counterparty, whose economics scale with client leverage and volume | Be the dealer/broker acting as principal counterparty to leveraged clients | AVOID-ONLY — capturing this requires being the intermediary/dealer; the account's own daily loss limit (3–5%, `ACCEPTANCE.md:9-12`) already targets the same over-leverage mechanism without selling, overnight holds, or shares | structural — the programme's numeric budget already sizes positions by "daily loss limit ÷ worst-trade loss" (`ACCEPTANCE.md:108`); not a separate trial | no data — design constraint, not an empirical trial |
| 14 | Persistent day-trading unprofitability; only a tiny minority is skilled | statistical-method | 97% of Brazilian futures day traders who persisted >300 days lost money, only 1.1% beat minimum wage (`U1-S8`); <1% of Taiwanese day traders predictably profitable, 80% quit within 2 years (`U1-S7`); top 500 ranked Taiwanese day traders earn +37.9bps/day after fees vs bottom −28.9bps/day (`U1-S6`); ~2x as many US day traders lose as win, ~20% "more than marginally profitable" (`U1-S9`) | The small, persistent skilled minority, at the expense of the much larger unprofitable population | Be in the <1%–20% with a genuine, persistent forecasting edge | YES in principle — a property of the strategy's own forecasting ability, not of selling/overnight/shares; base-rate evidence says such capability is rare | this programme's entire 42-trial ledger (family-wide FDR 0/42 pass, `SCORECARD.md:89`; family count established at `ACCEPTANCE.md:409`) is itself evidence against finding one easily here | already run — across every branch dataset in U3 §C (e.g. `data/ext/spx_1min_2020-05_2026-09.csv.gz`); no distinct new test needed |
| 15 | Belief in a harvestable dealer short-gamma edge that index-level evidence does not support (myth-correction) | statistical-method + risk-management | "high open interest gamma in 0DTEs does not propagate past volatility"; 0DTE volume shocks "do not amplify recent past index returns" (`U2-S04`); "no uptick in intraday gap moves," "market maker net exposure is fairly negligible" (`U2-S12`, Cboe-authored — flagged with a commercial conflict-of-interest caveat) | No one systematically — a myth-correction, not a wealth transfer, at the SPX index level | Not applicable — no reachable winning side is demonstrated at the index level | NO — no reachable side shown to exist | no — codified as a non-goal: "No GEX / dealer-positioning filters — no positioning data obtainable" (`ACCEPTANCE.md:119`) | no data — no GEX/dealer-positioning data obtainable; explicit non-goal |
| 16 | Prop-firm daily loss limit mechanically caps the number of full-loss 0DTE attempts per day | risk-management + structural (DERIVED) | N = floor(D/x); at D=4% daily limit and x=1%/trade, N=4 consecutive full-loss buys ends the day regardless of a later setup's quality (U2 §3 Rule 1 arithmetic); daily drawdown "typically 4–5%" across firms (`U2-S30`) | No specific counterparty — the "winner" is whoever is not subject to the constraint | None required beyond arithmetic; the actionable response is disciplined per-trade sizing | AVOID-ONLY — the constraint cannot be occupied or captured, only managed around | no — informs the proposed §4 rule, not yet an adopted account rule | no data needed — arithmetic (N=floor(D/x)), not an empirical trial |
| 17 | Trailing drawdown ratchets the risk budget tighter after every intraday gain | structural (DERIVED) | $100,000 account, 5% trailing max drawdown on intraday equity: a $3,000 intraday gain raises the floor to $98,000, so a reversal to $97,800 breaches the rule though the day's loss vs. the $100,000 starting balance is only 2.2% (U2 §3 Rule 2 arithmetic; `U2-S30`) | No specific counterparty — a mechanical consequence of the floor definition | None required — purely mechanical | AVOID-ONLY — no counterparty position to capture, only a mechanical rule to manage around | no | no data needed — arithmetic illustration only |
| 18 | Prop-firm consistency rules mechanically mismatch a convex, fat-tailed 0DTE payoff | structural (DERIVED) | example: 10 days, +$1,000 total profit, $700 from one large-move day → Consistency% = 70%, breaching even a lenient 50% cap (U2 §3 Rule 3 arithmetic; caps "usually 15–50%" per `U2-S30`); built on the capped-risk/multi-leg composition of "sophisticated" 0DTE flow (`U2-S11`) and the largely single-leg, short-duration shape of the typical retail trade (`U1-S21`/`U2-S08`) | The firm, which gates the payout on the ratio | None required — a structural mismatch between payoff shape and rule design | AVOID-ONLY — avoid manufacturing trades to satisfy the ratio | no | no data — depends on the owner's specific prop-firm rule set (not specified); arithmetic illustration only |
| 19 | Evaluation ("challenge") fee economics are negative-EV for the typical entrant | structural (DERIVED) | avg. spend $800/account across ~3 challenges; 14% pass; ~7% of all entrants ever get a payout; avg payout 4% of plan size → expected payout ≈ $70–$280 vs $800 spent, roughly −65% to −91% EV (`U2-S16`); FTMO discloses >$450M cumulative payouts but not entrant counts, so this arithmetic cannot be replicated for FTMO specifically (`U2-S17`) | The firm collecting challenge-fee revenue from the ~93% of accounts that never earn a payout | Be the firm collecting the fees | AVOID-ONLY — avoid paying into a negative-EV challenge product and avoid treating its pass-rate statistics as evidence | no | no data — single non-audited vendor dataset (`U2-S16`); treated as non-evidence, see §4 Rule 8 |
| 20 | Minimum-trading-days / inactivity rules force trades that satisfy a day-count, not an opportunity | structural | "most firms require 5–10 trading days" to pass; some funded accounts void with no trade in a rolling 30-day window (`U2-S30`) | The firm (more qualifying days/fee cycles) | None required — a self-imposed activity requirement | AVOID-ONLY — no counterparty position to capture, only a self-imposed rule to avoid triggering by not trading purely to satisfy a day-count | no | no data — depends on a specific firm's rules, not specified |
| 21 | No-overnight / 0DTE-only mandate discards the overnight return component of documented strategies entirely | structural | across 14 equity strategies, returns are earned "either entirely overnight... or entirely intraday," typically with opposite signs (`U2-S18`) | Whoever holds the exposure through the specific period (overnight or intraday) carrying the compensated component | Hold through the close-to-open gap | NO — requires OVERNIGHT, explicitly forbidden (`ACCEPTANCE.md:9-12`) | structural — every trial on this branch is same-day by construction; this is the account's own defining rule, not a separate test | no data needed / moot — testing would require holding overnight, forbidden by the mandate itself |
| 22 | Loss-chasing / revenge trading after a losing streak (bigger size, more frequency) | behavioural | after a losing streak, traders "increase position size" and "increase how frequently they trade" (`U2-S29`, SURVEY-grade, not peer-reviewed) | Whoever is counterparty on the incremental, lower-quality trades — the writer/wholesaler collecting extra spread and decay | Be "the house" on the extra flow generated by someone else's tilt | AVOID-ONLY — capturing it requires SELLING/market-making; the account can simply not increase size or frequency after losses | no — but A43's registered sizing (fixed 4% of a FIXED $100,000 account, recomputed fresh each day, never compounded) already structurally prevents size escalation (`TRACK_C.md:71`) | no data — behavioural sequences not held; the programme's own sizing rule already avoids this by construction |
| 23 | Position sizing without a ruin constraint (Kelly criterion / variance drag): oversizing destroys compounded growth despite positive per-trade expectancy | statistical-method + risk-management | DERIVED example: a +25%/trade average-expectancy bet (50% win 1.5x, 50% lose 1.0x) sized at a fixed 75% of capital per trade has expected geometric growth ≈ −31.6% per trade — capital shrinks toward zero despite positive simple expectancy (`U2-S28`, theory) | No specific counterparty — capital is destroyed by compounding volatility itself; in a prop context it transfers to the firm via forfeited fees | None required — a mathematical property of geometric compounding, not a someone-must-sell mechanism | YES — pure position-sizing discipline, no forbidden mechanism | consistent with — A43's sizing rule already recomputes contracts fresh each day at a fixed % of a fixed account base, never compounded (`TRACK_C.md:71`) | no data needed — arithmetic/theory, already reflected in the programme's own sizing convention |
| 24 | Strategy-hopping / indicator overfitting after losing stretches (data-snooping) | statistical-method | of 95 "modern" technical-trading studies, 56 positive / 20 negative / 19 mixed, with data-snooping flagged as pervasive (`U2-S21`); the best of ~7,846 DJIA trading rules fails out-of-sample once data-snooping is corrected for (`U2-S22`) | Brokers/exchanges (extra fees/spread from extra volume) and indicator/signal vendors | None required — a pure statistical-inference failure, not a counterparty mechanism | YES — avoidable via pre-registration discipline; already practiced here | YES, directly — A37 measures PBO of the D1 selection itself: 0.73 (`SCORECARD.md:39`; `ACCEPTANCE.md:200-209`); fixed pre-registration and family-wide BH-FDR guards exist specifically for this (U3 §B rows 1–3) | already run — `data/raw/oanda_SPX500_USD.parquet` (A37's PBO diagnostic on the D1 ranking, `out/pbo.csv`); U3 §B rows 1–3 |

Of the 24 merged failure modes: **3 are YES** (rows 14, 23, 24), **11 are AVOID-ONLY** (rows 1, 6,
7, 9, 13, 16, 17, 18, 19, 20, 22), and **10 are NO** (rows 2, 3, 4, 5, 8, 10, 11, 12, 15, 21). None of
the three YES rows describes an exploitable market-side effect: two of them (position sizing and
avoiding overfitting) are internal risk-management/statistical disciplines this programme already
follows, and the third (a genuine forecasting capability) is a property this account has not
demonstrated across 42 trials. The plain conclusion: the documented ways to profit from the
mistakes catalogued in U1/U2 belong almost entirely to sellers, overnight holders, share owners, or
market-making intermediaries — every one of which this account's mandate forecloses by design.
Inversion in the strong sense — take the other side of the losing trade — is not available here;
what remains is discipline (the AVOID-ONLY and YES rows) plus one narrow, unconfirmed
mechanism-based candidate explored in §5.

## 2. What the evidence says about the winners

How small the persistently profitable minority is: `U1-S8` found 97% of Brazilian futures day
traders who persisted more than 300 days lost money, and only 1.1% earned more than the Brazilian
minimum wage. `U1-S7` found fewer than 1% of Taiwanese day traders are predictably profitable
after fees, and 80% quit within two years. `U1-S6` ranked the same Taiwanese population and found
the top 500 earn +37.9 bps/day after fees while the bottom-ranked lose −28.9 bps/day after fees.
`U1-S9` found roughly twice as many US day traders lose as win, with about 20% "more than
marginally profitable." These four sources agree on the shape (a thin, persistent right tail against
a much larger loss-making population) but not on a single number for its size.

Where that minority's profit comes from is, for the general day-trading population, not
decomposed by the sources retrieved: `U1-S6` and `U1-S7` rank traders by outcome and do not
attribute the top performers' edge to a specific channel. For 0DTE options specifically, U2 does
name two documented winning channels — wholesaler/market-maker spread capture (`U2-S01`: ~90%
of options PFOF flows to three wholesalers, average 12.6% spread on retail-preferred contracts)
and premium sellers (`U2-S11`: >50% of "sophisticated" SPX 0DTE retail notional is itself
short-premium) — but U2 states plainly that it "could not find a clean, published decomposition of
aggregate retail 0DTE losses into these three channels" (spread vs. decay vs. direction; `U2-S02`,
`U2-S03`). No percentage split is asserted anywhere in this document either; the sources retrieved
do not decompose this.

The one documented episode of option *buyers* winning as a class is GameStop, January 2021: as
GME's price rose through successive call strikes, dealers short those calls were forced to buy the
underlying shares to stay delta-hedged, and that hedging-driven buying pushed the stock (and the
calls) higher, so long call holders profited as the feedback loop ran (U2 §4). It is not repeatable
at index level for two reasons the sources give directly: (1) the transmission mechanism runs
through dealers' SHARE hedging in a single, thinly-optioned name, not through an index-level
option buyer's own position; and (2) the two most directly relevant, more recent studies of the
actual SPX 0DTE market find no equivalent feedback loop exists there — `U2-S04` (Dim, Eraker &
Vilkov) reports "high open interest gamma in 0DTEs does not propagate past volatility" and that
0DTE volume shocks "do not amplify recent past index returns," and `U2-S12` (Cboe) reports "no
uptick in intraday gap moves" and "market maker net exposure is fairly negligible" — with the
explicit caveat that `U2-S12` is Cboe's own research and "should be weighed against the possibility
of house-view bias... since Cboe has a commercial interest in 0DTE volume being seen as
non-destabilizing." Combined with `U2-S03`'s aggregate-loss finding and `U2-S02`'s earnings-specific
loss finding, U2 concludes: "no source retrieved documents a repeatable, systematic situation in
which long-only 0DTE buyers earn money as a class."

## 3. Our own record through the same lens

This programme has already committed, and caught, several of the *research*-level failure modes
that mirror the trader-level ones above:
- **Look-ahead / non-causal construction defects** (U3 §B row 8): two sold-before-bought
  re-pricings (`CRITIQUE.md:187`), 43 of 409 trades choosing a strike not yet printed
  (`CRITIQUE.md:194`), and a dividend series contaminating the in-sample window and flipping the
  D1 winner (`CRITIQUE.md:122`). Guard: entry-must-precede-exit and causal-strike-availability rules
  (`ACCEPTANCE.md:392-397`); every later judge round re-ran a lookahead audit that came back clean
  (`CRITIQUE.md:163,183,203`).
- **Doc lag** (U3 §B row 9): close-out claims recorded ADOPTED with no change behind them
  (`RETRO.md:40`); a step appended to the wrong list, hidden by a stale `git status`
  (`RETRO.md:42`; `CRITIQUE.md:216`). Guard: any edit to `run_all`'s STEPS/EXPECTED is followed by
  one execution of the touched step before commit (`CRITIQUE.md:218`).
- **Synthetic stand-ins that don't exercise the real data format** (U3 §B row 10): recurred four
  times — tz-aware dividend crash (`CRITIQUE.md:118`), a DST probe failing on sparse pre-market
  prints (`CRITIQUE.md:119`), the dividend leak above (`CRITIQUE.md:122`), and a silently-discarded
  ETF panel splice (`CRITIQUE.md:132`). Guard: a stand-in must be built from a real sample of the
  supplied format, with a byte-identity gate against the native era (`RETRO.md:38`).
- **A Sharpe convention that inflates the annualised figure** (U3 §B row 12): Thread B's per-trade
  Sharpe × √252 overstated its headline by ≈2.6×; the 2.50 discovery Sharpe is ≈0.96 in calendar-day
  terms (`ASSESSMENT.md:175-177`; `SCORECARD.md:47`). Guard: every ranking and reported Sharpe in
  this programme is calendar-day, not per-trade annualised (`SCORECARD.md:47`).
- **DST / timestamp misalignment inflating a result** (U3 §B row 11): Thread B's own published
  holdout (n=85, Sharpe 1.67) mis-timed one open minute on naive UTC stamps and carried almost all
  its reported edge in winter sessions; the DST-correct row is n=90, Sharpe 1.28/2.05
  (`CRITIQUE.md:11`; `ASSESSMENT.md:169-174`). Guard: the sustained-step DST probe (47/47 months)
  and a tz-aware America/New_York session convention (`ACCEPTANCE.md:133-134`).

Against the trader-level failure modes catalogued in §1, this programme stands on the more careful
side of several of them, though largely by design constraint rather than demonstrated skill:
- **It never bought OTM lottery contracts.** The ATM/OTM 0DTE family was tested and killed (ATM 17%
  win rate at −53%/trade; OTM median −50.6% vs ITM median −20.9%) and is now a codified,
  permanent non-goal (`research/CLAUDE.md:59,210`; `ACCEPTANCE.md:118`) — directly the inverse
  action of §1 row 7.
- **It sized by worst day.** The programme's own numeric budget fixes position size as the daily
  loss limit divided by the worst-trade loss in % of premium, denominated on the worst day of the
  combined book (`ACCEPTANCE.md:108`) — the same discipline §1 rows 13/16/23 describe as the
  reachable inverse of leverage-amplified and unconstrained-sizing losses.
- **A39 T1 and A44 enter at 10:00, not 09:31 — but that is not a programme-wide rule.** A39's own
  timing fingerprint shows T2 (09:31 entry, +0.12 pts, `SCORECARD.md:54`) underperforming T1
  (10:00 entry, +2.20 pts, `SCORECARD.md:53`) — a deliberate fingerprint test, not evidence the
  programme avoids the open generally: A42 E1 (`SCORECARD.md:78`) and A43 S1/S3 (`SCORECARD.md:85,87`),
  both sell-side/own-account tests, entered at 09:31 on purpose. The T1/T2 contrast is consistent in
  direction with U2's open-cluster spread evidence (`U2-S27`, §1 row 6) that the market's widest
  effective spreads sit at the open — though this programme never tested the spread-widening
  mechanism itself, only the resulting timing fingerprint.

It is also worth stating plainly, with U3 references, where the largest measured effect in this
programme actually sits: the single largest number in the whole ledger is on the sell side, and it
is forbidden here. From the killed-families list (U3 §D), A42's E1/E3 baseline shows a long
straddle bought at 09:31 loses 7.0% of premium per day on average, and the same structure bought at
13:30 on non-FOMC days loses 17.2% (`ASSESSMENT.md:124-129`; `SCORECARD.md:78-79`) — this is the
variance risk premium documented across U1/U2 (§1 rows 2, 3, 5), and it lives on the sell side,
which the prop account's constraint (§0) forbids outright. The positive-but-unpromoted results (U3
§E) confirm the same premium exists on the short side pre-cost — the A43 short legs alone earn
+0.26/+0.24/+0.14 per share gross before wings and spread (`SCORECARD.md:89`;
`ASSESSMENT.md:137-145`) — but Track C shows that even the *defined-risk* version of selling that
premium fails once the wings and four legs of $0.10/leg cost are added: S1/S2/S3 all FAIL the
promotion rule (`SCORECARD.md:85-89`; `TRACK_C.md:55-67`). The account this programme serves cannot
sell premium at all; the own-account track that could is the one place this programme found the
premium was real and still could not clear its own cost.

## 4. Rules we adopt (the "stop doing" list)

Rules 1, 4, 5 and 7 below govern the owner's own discretionary trading, not a mechanical pipeline
signal. None of the four is measurable inside A44 as registered: A44 takes at most one mechanical
trade per day, at a fixed size, with no live or paper fills (`ACCEPTANCE.md:434-439`), so it cannot
observe a discretionary sizing fraction, a frequency-after-loss pattern, a resting-order fill, or a
manufactured consistency-rule trade. Compliance with these four can only be measured in an
owner-kept forward trade journal outside the pipeline. Rule 5 additionally requires the codified
"no live or paper execution" non-goal (`ACCEPTANCE.md:118-119`) to be relaxed by its own amendment
before any mid-quote/fill-price/slippage number could be recorded at all. Rules 2, 3, 6 and 8 remain
measurable as stated below (entry time, moneyness, family inclusion, source tags) because A44 and
the pipeline can check each of those directly.

1. **Size each trade as a small, fixed fraction of the daily loss limit, and cap the number of
   full-loss attempts per day — a PROPOSED AMENDMENT to the account's existing sizing rule.**
   Inverts §1 rows 16, 23 (and discourages row 9/22 overtrading and loss-chasing). Evidence: U2 §3
   Rule 1 arithmetic (`N = floor(D/x)`), `U2-S28` (Kelly, variance drag). Status: the prop account
   already has a sizing rule (`ACCEPTANCE.md:108-112`): position size = daily loss limit ÷
   worst-trade loss in % of premium, floor 100%; at the base case D=4% this implies x=4% per trade
   and N=1 full-loss attempt per day. **Proposal, not fact, for the owner:** override that base
   case with a smaller per-trade fraction — x=1% of account equity per trade (≤25% of the daily
   limit), giving N=4 maximum full-loss attempts per day; or x=0.5%, N=8. This names exactly what
   it overrides (the existing 4%/N=1 base case) and needs the owner's decision plus its own
   `ACCEPTANCE.md` amendment before it takes effect. Measurement: see the preamble above.
2. **No entries in the first 30 minutes of the session.** Inverts §1 row 6. Evidence: `U2-S27`.
   Status: NEW for the prop account, not already followed — A39 T1 and A44, the prop-account-relevant
   candidates, enter at 10:00, but A42 E1 and A43 S1/S3 (sell-side/own-account tests, not prop-account
   trades) entered at 09:31, and A39 T2 was a deliberate 09:31 timing fingerprint, not an accidental
   early entry; no cross-programme rule has actually been adopted yet, only the practice of two
   candidates. The T2-vs-T1 fingerprint (T2 +0.12 pts, `SCORECARD.md:54`, vs T1 +2.20 pts,
   `SCORECARD.md:53`) is the programme's own evidence for adopting it. A44 measurement: log
   `entry_time`; audit that every trade's `entry_time` is ≥ 10:00 ET.
3. **ITM-only strikes; no ATM or OTM "lottery" contracts.** Inverts §1 rows 4, 7. Evidence:
   `U1-S11`, `U2-S11`, `U1-S21`/`U2-S08`; this programme's own numbers, ATM −53%/trade at 17% win
   rate and OTM median −50.6% vs ITM median −20.9% (`research/CLAUDE.md:59,210`; `ACCEPTANCE.md:118`).
   Status: already followed — codified as a permanent non-goal after the ATM/OTM family was
   killed. A44 measurement: log strike moneyness (% ITM) per trade; reject/flag any trade at or
   beyond at-the-money.
4. **No increase in size or trade frequency after a loss.** Inverts §1 rows 22, 9. Evidence:
   `U2-S29` (SURVEY-grade, flagged as such — not peer-reviewed). Status: new for the prop account —
   the account's existing sizing rule (`ACCEPTANCE.md:108-112`) fixes position size to the daily
   loss limit divided by the worst-trade loss (floor 100%) but places no explicit cap on trade
   frequency or on increasing size specifically after a loss; no such rule exists yet for the prop
   account. Measurement: see the preamble above.
5. **Rest limit orders at the mid rather than sending marketable orders.** Inverts §1 row 1.
   Evidence: `U1-S5` (passive orders profitable at short horizons vs. aggressive ones), `U2-S01`,
   `U2-S07` (execution timing recovers ~25% of the naive spread cost). Status: new — and it cannot
   be backtested here: the branch's option shards (`data/ext/spy_0dte_1min_2024/2025/2026.csv.gz`)
   contain trade prints only, no bid/ask quotes (U3 §C). Measurement: see the preamble above — this
   rule additionally requires the "no live or paper execution" non-goal (`ACCEPTANCE.md:118-119`)
   to be relaxed by its own amendment before any mid-quote/fill-price/slippage number could be
   recorded at all; until then it is a forward-journal discipline, not a measured one.
6. **Every rule and candidate is pre-registered and counted in the trial family before any run.**
   Inverts §1 row 24 (and is the cross-cutting guard behind U3 §B rows 1–3). Evidence: U3 §B rows
   1, 2, 3. Status: already followed — the six-condition survival rule's condition 3 requires
   passing BH-FDR at 10% across every trial in the run (`ACCEPTANCE.md:58`), with the trial
   definition fixed by A31 (`ACCEPTANCE.md:162`). Family count: any new candidate joins a Track-A
   family of 42 already-run trials (43 counting A44, pre-designated `ACCEPTANCE.md:439`;
   `ACCEPTANCE.md:409`); family-wide BH-FDR 0/42 pass (`SCORECARD.md:89`). A44 measurement: confirm
   inclusion in `out/trials.csv` and the family-wide BH-FDR pass before any promotion claim.
7. **Do not trade to satisfy a consistency or minimum-days rule.** Inverts §1 rows 18, 20.
   Evidence: U2 §3 Rules 3 and 5, `U2-S30`, `U2-S11`, `U1-S21`/`U2-S08`. Status: new — no explicit
   rule yet for the prop account. Measurement: see the preamble above.
8. **Treat unaudited prop-firm statistics as non-evidence — for example, the generic "5–10% pass" /
   "95% fail" prop-firm figures and FTMO's "99.8%" payout claim (u2 §5).** Inverts nothing in §1
   directly — it is a source-hygiene rule guarding against the sources §1 rows 16–20 (the prop-firm
   rows) lean on. Evidence: U2 §5 flags these figures, and 5 others, as UNVERIFIED and not used as
   facts; U1 §4 found no peer-reviewed prop-firm outcome study and marked industry-aggregator
   statistics UNVERIFIED. `U2-S16`/`U2-S17` are themselves labelled single-vendor/non-audited even
   where used. Status: already followed — this synthesis uses no UNVERIFIED number as a fact
   anywhere above. A44 measurement: any future citation of a prop-firm statistic in A44
   documentation must carry a VERIFIED/UNVERIFIED tag; an UNVERIFIED number is never used to size
   or gate a trade.

## 5. Candidates that survive the screen

Screen applied to every YES/AVOID-ONLY row and every mechanism named in U1/U2: (a) names who must
trade and when; (b) reachable under the constraint (YES in §1); (c) not a duplicate of a killed
family or codified non-goal (U3 §D); (d) testable on branch data, or states exactly what is
missing; (e) an honest n estimate against the ≥200 holdout floor (`ACCEPTANCE.md:66`). Applying
this screen to the three YES rows (14, 23, 24) eliminates them as *candidates*: row 23 (sizing
discipline) and row 24 (pre-registration discipline) are process rules already codified in §4, not
market-side mechanisms that name a counterparty who must trade; row 14 (a genuine forecasting
capability) names no specific "who trades when" — it is a property a candidate would need to have,
not a candidate itself. No other row in §1 clears screen condition (b). The result is a single
surviving candidate.

### Rank 1 (and only survivor) — intraday forced-flattening rebound

**Mechanism (hypothesis).** Accounts subject to daily loss limits and margin calls are forced to
sell after a large morning decline, mechanically pushing price down further into that forced
selling and creating a rebound once the forced selling exhausts — the intraday analogue of the
overnight-gap forced-liquidation mechanism already tested here as A39 (Reg T margin calls,
Brunnermeier & Pedersen 2009, `SCORECARD.md:53-55`), and of the same daily-loss-limit-forces-an-exit
logic derived in §1 row 16 (U2 §3 Rule 1).

**Entry, direction, gate, exit.**
- Gate: open→11:00 SPY move at or below the expanding 10th percentile of all prior sessions'
  open→11:00 moves (requiring ≥20 prior sessions before the percentile is well-defined — the
  registered expanding-threshold floor A29/A39/A44 use, `ACCEPTANCE.md:160`; an expanding-percentile
  gate, no fitted threshold). The 11:00 entry time itself has no cited evidence behind it in U1 or
  U2; the 09:45 fingerprint below is the only test of the timing, and exactly one entry time
  (11:00) is registered.
- Entry: long call at 11:00.
- Exit: 15:59 close.
- Mirror trial (tests the predicted asymmetry): after an open→11:00 move at or above the expanding
  90th percentile, buy a put at 11:00 — the mechanism predicts the call side shows the effect and
  the put mirror does not (an overnight-gain forced-liquidation story is not the mechanism claimed
  here).
- Timing fingerprint: an otherwise-identical 09:45 entry, to check whether the effect requires the
  liquidation to have largely completed by 11:00 (as A39's T1/T2 fingerprint tested for the
  overnight version, `SCORECARD.md:53`).

**Controls.** Day-selection (random-day) control per `ACCEPTANCE.md:46-66` condition 4; the timing
fingerprint above; the mirror trial above (both the day-selection and mirror controls follow the
same convention A39 used).

**Distinctness from what is already tested (U3 §D check).** This is not D1 momentum: D1 enters in
the afternoon (15:00/15:30) in the direction of a VIX-gated or magnitude-gated move
(`ASSESSMENT.md:14`; `PLAYBOOK_0DTE.md:124`), whereas this candidate enters at 11:00 on a morning
gate, in the *reversal* direction, not the continuation direction. This is not A39: A39 is triggered
by the prior session's overnight (close-to-open) return and enters at 10:00 (`SCORECARD.md:53-55`),
whereas this candidate is triggered by the current session's intraday open→11:00 move. It is also
not a disguised "flow-with-a-deadline": that killed family (month-end, opex, Russell reconstitution,
and the screened FOMC/pension/Treasury-auction/ETF-creation variants, `SCORECARD.md:36`;
`BLOCKED.md:89,125`) is triggered by the calendar, not by realized price action, and this candidate
is triggered only by a data-dependent percentile threshold with no fixed date.

**Data file.** Two pricing routes, named explicitly because they give different n (see below).
PRIMARY: `data/ext/spx_1min_2020-05_2026-09.csv.gz` (actual content SPY, Alpaca IEX) for the gate,
signal, AND modelled option pricing (Black-Scholes at k×VIX, `ACCEPTANCE.md:136` A7 — the same
route A39 used), over the full window it covers (U3 §C). SECONDARY: `data/ext/spy_0dte_1min_2024/
2025/2026.csv.gz` shards for real-priced option entry/exit pricing, as a sub-window check, the
convention A41 established (`ACCEPTANCE.md` Amendment A41).

**Honest n estimate.** PRIMARY route: the full window `data/ext/spx_1min_2020-05_2026-09.csv.gz`
covers 2020-07-27→2026-09-11, 1,526 sessions (`DATA.md:68`). With the registered ≥20-prior-session
expanding-threshold floor (A29, `ACCEPTANCE.md:160`), 1,526 − 20 = 1,506 sessions are eligible; a
10th-percentile gate should trigger on roughly 10% of eligible sessions by construction, giving an
*estimated* n ≈ 151. SECONDARY route: the option shards cover 2024-02-01→2026-09-11
(`DATA.md:100-102`; u3 §C), about 675 sessions, giving an estimated n ≈ 65–68 real-priced. Both
figures are an expectation from the gate's own definition, not a measured historical trigger count;
counting signals without observing outcomes is not a "second selection" (U3 §B row 3 is about
re-tuning after seeing outcomes, not about counting how often a fixed rule would have fired) — the
actual trigger count will be reported at registration time. PRIMARY's n ≈ 151 is below the ≥200
floor (`ACCEPTANCE.md:66`), so this candidate would register as UNDERPOWERED on the existing
holdout, the same outcome A39 T1 had at n=158. Reaching n≥200 on the PRIMARY route would need
roughly 2,000 eligible sessions (200 ÷ 10%), i.e. about 494 more sessions beyond the current 1,506 —
on the order of 2 more years of forward data, comparable to A44's own ≈2-year forward horizon
(`ACCEPTANCE.md:438`). Sensitivity only, not a registered gate: at a 250-session warm-up instead of
the registered 20-session floor, 1,276 sessions would be eligible, giving n ≈ 128 — reported only to
show the estimate is not sensitive to the choice of warm-up length.

**Honest prior: LOW.** No source retrieved in U1 or U2 quantifies prop-firm or margin-call-driven
forced-selling flow at the SPX/SPY index level; the mechanism is analogical (from the general
leverage/margin-call literature, `U1-S10`, `U2-S19`, and the daily-loss-limit arithmetic of §1 row
16) rather than directly measured for this specific intraday phenomenon, and A39's own mirror test
of the closely related overnight version found the predicted asymmetry absent (T3 mirror also
positive, `ASSESSMENT.md:74-83`) — a reason for caution, not confidence, about this candidate.

**Kill criterion.** Any failure of the six-condition survival rule (`ACCEPTANCE.md:46-66`), or a
fingerprint failure analogous to A39's (the mirror put trial showing the same sign/magnitude as the
call, or the 09:45 fingerprint entry performing as well as or better than 11:00) — either would mean
"pattern without its mechanism," as A39's own mirror result was read (`SCORECARD.md:53-55`).

**Family count after registration.** Per the A39 precedent — three trials (main, mirror, timing
fingerprint) join the family together, not one (`ACCEPTANCE.md:255-261`, "33 + 3 = 36") — this
candidate registers as three trials: the main gate, the mirror trial, and the 09:45 timing
fingerprint. Joins the Track-A family currently at 42 run trials (43 counting A44 once it runs;
`ACCEPTANCE.md:409`; family-wide BH-FDR 0/42 pass, `SCORECARD.md:89`); pre-registering these three
trials would move the family from 42 → 45 if registered before A44 first runs, or from 43 → 46 if
registered after, tightening the BH-FDR bar for every trial already in the family; DSR at N = 45 or
46 accordingly.

### Considered and rejected

- **Post-macro-release intraday drift** (e.g., CPI/NFP/FOMC). Not assessed — neither U1 nor U2
  quantifies how quickly SPX/SPY completes its post-macro-release move; the one closely related
  test already run here, A42's FOMC-afternoon trial, is underpowered by calendar (n=20 at ~8 FOMC
  meetings/year; reaching n≥200 would take roughly 25 years, `notes/inversion/u3_self_audit.md` §E
  (A42 item); `ASSESSMENT.md:124-129`), and any
  macro-release variant inherits the same calendar-driven underpowering. Fails screen (e).
- **Option-quote limit-order capture** (be the resting counterparty at the mid). Fails screen
  (d): the branch's option shards are trade prints only, with no bid/ask quotes (U3 §C); it also
  fails screen (b) for full capture, since being a genuine two-sided quote provider is SELLING/being
  the intermediary (§1 row 1).
- **Any overnight component** (e.g., capturing `U2-S18`'s overnight/intraday split, or `U1-S19`'s
  multi-week disposition-effect drift). Fails screen (b): every version requires holding OVERNIGHT,
  explicitly forbidden by the constraint (`ACCEPTANCE.md:9-12`).
- **Quarterly index-reconstitution / triple-witching pin drift.** Fails screen (c): this is a
  disguised repeat of the already-killed "flow-with-a-deadline" family (month-end, opex, Russell
  reconstitution all negative and killed, `SCORECARD.md:36`; `BLOCKED.md:89`), which already
  screened and rejected the FOMC/pension/Treasury-auction/ETF-creation variants of exactly this idea
  as duplicates (`BLOCKED.md:125`).

## 6. What this changes and what it does not

The inversion lens confirms this programme's existing negative result rather than overturning it.
Nothing in U1 or U2 identifies a documented winning role this account can occupy without selling,
holding overnight, holding shares, or being the market-making/firm intermediary — the same
conclusion the 42-trial ledger's family-wide 0-of-42 FDR pass rate already implies
(`SCORECARD.md:89`; family count established at `ACCEPTANCE.md:409`). What the lens adds is threefold: (1) the "stop doing" list
in §4, an explicit, pre-registered rulebook for the forward log rather than an implicit set of
habits; (2) exactly one new, LOW-prior, mechanism-based candidate (§5) that is distinct from every
family already run or killed here, ready to pre-register if the owner chooses; and (3) a concrete
measurement plan tying every §4 rule to a specific A44 forward-log column, so compliance is audited
rather than assumed. What it cannot do is create expectancy under a long-only 0DTE mandate: §1's
count (3 YES, 11 AVOID-ONLY, 10 NO out of 24 merged failure modes) shows the documented profitable
roles are almost all foreclosed by construction, and the one YES row that names an actual market
mechanism (a genuine forecasting capability, row 14) is a property this account has not
demonstrated, not one the inversion exercise can supply. The owner's decision points from here:
whether to adopt the eight rules in §4 (several are already followed; three — resting-order
measurement, the per-trade/attempt-count cap, and the consistency/min-days flag — are new and cost
nothing to start logging); whether to pre-register the §5 candidate, given its LOW prior and its
~2-year path (on the PRIMARY modelled-pricing route) to an unambiguous n≥200 verdict; and that
A38 (leveraged-ETF data) and A44 (the overnight-gap forward test) remain pending on the owner's
own data supply, independent of anything in this document (`BLOCKED.md:142`; `ACCEPTANCE.md:434-439`).

## 7. Sources

- `notes/inversion/u1_retail_failures.md` — 21 sources (`S1`–`S21`), all tabled status VERIFIED
  (with inline caveats on 4 of them: `S7`, `S12`, `S14`, `S17`); a separate "what I could not
  verify" section lists 5 additional claims explicitly excluded from use as facts (prop-firm pass
  rates, a Grinblatt-Keloharju coefficient, a Dorn-Huberman-Sengmueller magnitude, S7's exact
  publication venue, and the FCA sample's date range).
- `notes/inversion/u2_0dte_prop.md` — 31 sources (`S01`–`S31`): 29 tabled VERIFIED, 1 tabled SURVEY
  / practitioner-data (`S29`, not peer-reviewed), and 1 tabled INDUSTRY-DOC (`S30`, mechanism
  corroborated across independent sites but not one audited primary source); a separate "what I
  could not verify" section lists 7 additional claims explicitly excluded from use (generic
  prop-firm pass-rate figures, an unsourced FTMO payout-rate figure, a spread/decay/direction loss
  decomposition, trading-journal improvement statistics, an industry-wide consistency-rule
  standard, an unpinned intraday volume-clustering claim, and the exact sample dates for de
  Silva/Smith/So, `S02`).
- `notes/inversion/u3_self_audit.md` — does not use a VERIFIED/UNVERIFIED tagging scheme; instead
  every claim carries a `file:line` or `out/` path reference by design, per its own header
  ("Every claim below carries a `file:line` reference or an `out/` path").
- `notes/inversion/u5_citation_audit.md` — independent, fresh-search citation audit of 12 claims
  drawn from U1/U2 plus 1 negative claim: 11 CONFIRMED, 1 PARTIAL (the Beckmeyer/Branger/Gayda
  0DTE daily-loss figure — real numbers, but two different statistics/versions of the same paper,
  resolved in §1 rows 3 and 5 above), 0 NOT FOUND; the negative claim (CFTC v. My Forex Funds
  dismissal, `U2-S15`) also CONFIRMED.
