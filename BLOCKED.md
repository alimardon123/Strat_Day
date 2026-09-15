# BLOCKED.md — the goal cannot be advanced further from inside this environment

> **Update 2026-09-13 08:54 UTC — option A taken.** The owner pushed the four `data/ext/` files (commit
> 781180b). The block is lifted; this file stays as the record. Two real-data defects surfaced at once
> (dividend stamps with DST-varying offsets crashed `load_ext`; the DST probe's statistic failed on a feed
> with pre-market bars) and are being repaired before the holdout runs; the feed begins 2020-07-27, so
> the holdout's first eight weeks have no minute data and are reported as absent (DATA.md).
>
> **Closed 2026-09-13 10:10 UTC:** the holdout ran; both pre-registered signals FAILED (ASSESSMENT.md). This file is kept as the record of the block and its resolution.

Written 2026-09-13 after judge round 3 (DONE for the data that exists) and a final data-acquisition
sweep. This file exists because the Crucible protocol forbids silent shipping: the mission's
decisive question — does the reconciled last-hour signal survive 2020-06 → 2026-09 — has not been
answered, and nothing left in scope can answer it without one action by the owner.

## The gap

| What is missing | Why it matters | Named in |
|---|---|---|
| `data/ext/spx_1min_2020-05_2026-09.csv.gz` + `data/ext/ext_manifest.json` (+ `spy_dividends.csv` if SPY) | D2 holdout verdict, D4 headline, D3 holdout execution, the 15 POST-SELECTION rows, the full-sample table | DATA.md (spec), `tools/fetch_ext_local.py` (fetch script) |
| `data/ext/etf_daily_2017-11_2026-09.csv.gz` (29 tickers incl. VXX/VXZ/VIXY/VIXM) | D5: sleeves S2/S3/S6/S13 stop at 2017-11-10; VXX/VXZ bridge to the Series B notes | DATA.md |

Everything else in the contract is done or correctly labelled: `make all` on the current tree
regenerates 66 files byte-identically; with the two files present it regenerates 126, including the
holdout verdict (proven twice on a synthetic feed by fresh-context judges).

## Root cause

The container's network policy allows only GitHub and PyPI. Every market-data vendor returns 403 at
the proxy, and yfinance cannot serve 1-minute history older than 7 days even where reachable. The
pre-2020 data all came from GitHub mirrors; no GitHub mirror of post-2020 minute bars or of this
ETF universe exists.

## What was tried (so nobody repeats it)

1. Plan mode (2026-09-12): Yahoo, Alpaca, Databento, Polygon, Kaggle, CBOE, FRED, stooq, Tiingo,
   TwelveData, HuggingFace, Dukascopy — all 403 at the proxy.
2. 2026-09-13 sweep (two Sonnet agents, web search + `git ls-remote` + shallow clones):
   - Minute bars: the only genuine 1-minute S&P series on GitHub is a broker CFD feed
     (`USA500IDXUSD_M1`, Feb–Sep 2023, capped at 200,000 bars, placeholder volume) — wrong
     instrument, wrong range. Every SPY 1-minute file found is a single yfinance day. Kaggle's
     2008–2021 SPY 1-minute set is referenced by repos but never committed. FutureSharks still ends
     2020-05.
   - ETF panel: nothing covers the 29 tickers; the best partial source is a personal automation
     repo whose README asks not to be read by AI tools — not used, clone deleted. `big_movers`
     adds only SLV (2020→2026-03, no adjusted close).
   - Local panels: SPY to 2026-03-20 and SLV; all 27 other tickers end 2017-11-10.
3. 2026-09-13 reachability probe of every host not tested in plan mode: histdata.com (the original
   source of Thread B's SPXUSD 1-minute series, still published monthly), alphavantage.co,
   financialmodelingprep.com, eodhd.com, api.marketdata.app, firstratedata.com, forexsb.com,
   barchart.com, investing.com, api.tradingview.com — all refused by the proxy
   (`CONNECT tunnel failed, response 403`) while github.com answers. The network policy, not the
   vendors, is the wall; option B below is the only in-environment fix.
4. Substitutes explicitly refused by the mission: daily bars, synthetic data, 5-minute bars, a CFD
   proxy, re-tuning on pre-2020 data, a new pattern search over 2005–2020.

## Options (owner's decision)

| # | Option | Effort | What it unlocks |
|---|---|---|---|
| A | Run `tools/fetch_ext_local.py` on a machine with internet (Alpaca free plan for SPY 1-min; or Databento / IBKR for ES / SPX) and commit the files under `data/ext/` on this branch | ~20 min + one commit | `make all` produces the holdout verdict, the headline playbook, the post-selection rows, the full-sample table, the four ETF sleeves and the VXX/VXZ bridge |
| B | Change this cloud environment's network policy to allow one data host (e.g. `data.alpaca.markets` with `APCA_API_KEY_ID` / `APCA_API_SECRET_KEY` as environment variables, or `stooq.com` for the daily panel); then ask for the fetch to run here | Settings change; docs: https://code.claude.com/docs/en/claude-code-on-the-web | Same as A, without a local run |
| D | Authorise a search the mission currently forbids: an open-to-close 0DTE study on DAILY bars 2000→2026-03 (entry at the open print, settlement at the close, both present in daily OHLC — SPY and VIX are available here through 2026). This is a NEW pattern search over data both threads already exhausted, with a 6.5-hour time-value cost that both threads measured as fatal for directional 0DTE; it would need its own pre-registration, trial count and family FDR, and cannot touch the prop-account playbook's last-hour signals. Recorded so the option is visible; NOT started, because the mission's non-goals rule it out and only the owner can change them | one sentence from the owner | A holdout-era (2020→2026) test of a different, weaker idea — not the reconciled signal |
| C | Accept the in-sample result as final | none | Nothing tradeable: the honest label is "no reconciled specification is confirmed; small, crisis-loaded in-sample edge; 0 of 23 trials pass the family FDR" |

## What the result will most likely be (so expectations are set before the data lands)

The winner fires ≈ 20 times a year; the holdout window yields ≈ 125–160 trades, below the
200-trade floor in the survival rule. The probable honest label is UNDERPOWERED even if the sign
holds. A "loophole" was never on the table: both prior threads and this run measured the last-hour
effect at a few basis points per trade, concentrated in crises, at the edge of what 0DTE spreads
allow. The playbook's section 8 (ten real fills, sixty paper days) is the only way to learn what
the model cannot.

---

## Reopened 2026-09-13 12:05 UTC — the goal condition, not the data, is now the block

The session's standing goal reads "a highly successful trading system … that can find a loophole or really
strong edge in the market". The contract (ACCEPTANCE.md) was written so that this could only be claimed
after a pre-registered signal survived the post-2020 holdout. It did not:

| Evidence | Value | File |
|---|---|---|
| Reconciled last-hour winner on the holdout | n 274, −0.14 pts/trade at 1 pt, p 1.00, FAILED | `out/holdout_pooled.csv` |
| Thread A gap-up call on the holdout | n 452, −1.90 pts/trade, p 1.00, FAILED | `out/holdout_pooled.csv` |
| Family-wide BH-FDR at 10 % | 0 of 33 trials | `out/trials.csv` |
| Owner's fair-value-gap family (A36) | 0 of 8 survive on any window | `out/fvg_candidates.csv` |
| Flow-with-a-deadline candidates (month-end, opex, Russell) | all negative, below control | `out/flow_candidates.csv` |
| Probability of backtest overfitting of the selection | 0.73 (null 0.85) | `out/pbo.csv` |
| Judge round 5 | DONE on f28b5a3; nothing promoted | CRITIQUE.md |

### Why more iterations inside this session cannot satisfy the condition

1. Every remaining positive number sits on the holdout (three magnitude-gated post-selection rows, best
   `15:00|put|mag` +1.94 pts, p 0.10). Promoting any of them is a re-tune on the holdout — the one
   thing the contract forbids ("do not manufacture a pass"). It can only be a *new* pre-registration
   judged on data after 2026-09-11 or on real fills.
2. A fresh pattern search over 2005–2020 is a recorded non-goal (both threads exhausted it; PBO 0.73
   says the selection procedure itself over-fits at this trial count).
3. The plateau rule (two iterations without improvement) has been hit on every in-scope task; the
   tribunal budget (5 rounds) is spent with a DONE verdict on a negative result.
4. The stop hook is automated; it cannot pre-register, supply data, or choose among the options below.
   Continuing to fire agents against it would spend budget on tests nobody registered.

### Options for the owner (choose one; each is a new pre-registration in its own commit)

- **A. Stop here.** The deliverable is the finding: the last-hour edge both threads found is not there
  at prop-account costs after 2020. Everything is reproducible (`make all`, byte-identical twice).
- **B. Forward test, no new backtest.** Pre-register `15:00|put|mag` (Thread A's rule, unchanged) and
  judge it only on sessions after 2026-09-11 — paper fills logged by the owner, or the next data drop.
  Survival rule unchanged (n ≥ 200 means roughly two years of signals).
- **C. One new mechanism candidate.** From the table below (drafted by a scout, to be appended), pick
  one that names who must trade and when; pre-register entry, direction, gate and every parameter in
  its own commit; test once on 2005→2020 as selection and 2020-07→2026-09 as holdout; report under the
  same six-condition survival rule; kill if it fails. No second candidate until the first is judged.
- **D. Supply the missing mechanism data.** If the chosen candidate needs a file that is not on the
  branch (e.g. leveraged-ETF AUM by day, VIX settlement dates), commit it under `data/ext/` with a
  manifest, as with the minute bars.

The run stays closed until one of these is chosen; no agent will be launched against the stop hook.

### Option C — candidate table (fleet scout, read-only, 2026-09-13; nothing here has been run)

Screened and rejected as disguised repeats or untestable here: FOMC 14:00 (an information event, tested by Thread A as a straddle: +6.6 % at VIX-as-IV, −18 % at realistic IV; two legs), opex pin at 16:00 (the dealer-gamma mechanism by another name, same family as the killed opex flow), end-of-quarter pension rebalancing (Thread B's step12 bucket, 0/32, and the killed month-end row), Treasury auction 13:00 (no bond data; would become a time-of-day pattern), ETF creation/redemption cut-offs (no AP flow data).

| Candidate | Mechanism (who must trade, when) | Pre-registration spec | Data | Evidence and honest prior | Kill |
|---|---|---|---|---|---|
| Leveraged-ETF close rebalancing, AUM-weighted | 2×/3× S&P funds (SSO, SDS, UPRO, SPXU, TQQQ, SQQQ) must trade (L²−L) × AUM × day return in the last 30–40 min to reset leverage before the 16:00 NAV; size is forced, sign follows the day | Entry 15:30 ET; direction = sign of Σ (L_i−1) × AUM_i × r_i; gate = expanding 70th percentile of \|flow\| on prior sessions only; exit at the close; no other parameter | SPY 1-min on the branch; MISSING daily AUM or shares outstanding for the six tickers → `data/ext/letf_aum_2020_2026.csv` (ticker, date, shares_outstanding or aum) | Cheng & Madhavan 2009; Tuzun 2013. Prior MEDIUM-LOW: the price-only proxy of this mechanism (the magnitude gate) already failed this holdout; the AUM weighting adds cross-time variation, nothing else | Net ≤ 0 at 1 pt, or no improvement over the on-file magnitude control |
| VIX settlement (Wednesday SOQ) morning flow | Dealers short VX futures/options must trade the SPX option basket at the 09:30 SOQ on settlement Wednesdays (CBOE rule, not discretionary) | Entry 09:31 ET on settlement Wednesdays (30 days before the third-Friday SPX expiry, derivable from the public rule); direction fixed from the overnight gap sign; exit at the close | SPY 1-min from 2020-07-27 and VIX daily on the branch; the settlement calendar is derivable, no file needed | Griffin & Shams, RFS 2018. Prior LOW: CBOE tightened the SOQ in Oct 2014 to kill this; ≈ 24–30 Wednesdays a year → n < 200 on the holdout → UNDERPOWERED by construction | Net ≤ 0, or n < 200 |
| S&P quarterly rebalance closing auction | Passive S&P funds must match the index at the third-Friday quarterly close | Entry 15:30 on the four dates a year; direction = sign of net added-minus-deleted market cap | Nothing usable on the branch: needs a constituent-change file; the date coincides with the killed opex row | Chen, Noronha, Singal 2004; Petajisto 2011. Prior LOW: Thread B's bucket scored 0/32 and event days were calmer, not richer | Untestable without the file; if built, net ≤ 0 |

Scout's ranking: the leveraged-ETF candidate has the cleanest mechanism and the shortest data path (one file, six tickers; exactly what option D anticipates) but is a refinement of a gate that already failed, so expectations are tempered. The VIX-settlement candidate has the sharpest citation and the lowest prior, and cannot reach 200 holdout trades. The S&P rebalance candidate is a relabelling of a killed family; drop it unless a constituent file appears. If the owner chooses C, the leveraged-ETF candidate is the one to pre-register, with the AUM file supplied first.

---

## Status after the owner's option C (2026-09-13, judge round 6 DONE on b7d4772)

| Item | Result | What would change it |
|---|---|---|
| A39 overnight-loss liquidation rebound (3 trials) | Holdout T1 +2.20 pts, n 158 (UNDERPOWERED), p 0.26, mirror also positive → not promoted | Only more data: a forward test on sessions after 2026-09-11 (option B), symmetric spec |
| A38 leveraged-ETF rebalancing (owner's pick) | Built, tested, wired; SKIPS — `data/ext/letf_aum_2006_2026.csv` does not exist and is not on GitHub | The owner fetches it locally (`tools/fetch_letf_aum_local.py`, sponsors' downloads) and pushes it; `make all` then runs the pre-registered test unchanged |
| Track B swing-start detector (24 trials, SPY + gold, locked) | Both winners FAILED; 0 of 24 pass FDR; the sweep effect exists at a sixth of a bar, below cost | Nothing on price data alone; the pattern tables are the finding |
| Real 0DTE option prices | Not on the branch; the k × VIX model prices every option leg | The owner fetches SPY 0DTE 1-minute option bars from February 2024 (`tools/fetch_spy_0dte_local.py`) — the single highest-value addition: real costs, real premiums, and an event-day long-volatility test the model cannot price |

Every candidate that can be built from the data on this branch has now been pre-registered, run once, and judged. The remaining levers are two files only the owner can obtain. Until one lands, any further run would be an unregistered search over data that has already answered, which the contract forbids; the run therefore stays closed and no agent is launched against the automated stop hook.

---

## Status after the real-price batch (2026-09-13, judge round 7 DONE on d684bf9)

| Item | Result | What would change it |
|---|---|---|
| A41 re-pricing with the owner's real 0DTE bars | Every modelled trade keeps its sign; the model was optimistic by ½–4 points of premium after the spread; no row significant; k unidentifiable at 2 % ITM; prints missing in 80 % of named minutes, fills a median 3 minutes late | Nothing — the question is answered |
| A42 event-day long volatility | Daily straddle −7 % of premium at 09:31, −17 % at 13:30 (n 608, p 1.00); FOMC afternoons near zero (n 20, UNDERPOWERED, lottery profile) | Only years more of FOMC days |
| The one large, measured effect | The 0DTE variance risk premium: 7–17 % of premium per day, n 646/608, on the SELL side | Option E below |

### Owner options, updated

- **A. Stop.** The finding stands on three data sets and 39 pre-registered trials: no long-only 0DTE mechanism clears its cost.
- **B. Forward test** the overnight-loss call (symmetric spec) on sessions after 2026-09-11; no data needed, ≈ 2 years to 200 signals.
- **C/D. Leveraged-ETF candidate** (A38): built and waiting for `data/ext/letf_aum_2006_2026.csv`.
- **E. Change the account constraint.** The only effect this programme measured that is large enough to pay costs is the premium collected by SELLING 0DTE straddles, which the prop account forbids. If the own-account track (a stock account with options approval) may hold DEFINED-RISK short premium (iron condors / short straddles with wings), a pre-registered sell-side test can run on the same real bars: tail risk is the whole question (worst day, margin, the 4 % daily-loss rule), not the mean. Say so and it will be pre-registered in its own commit before any run.

No agent is launched against the automated stop hook; the run resumes on a letter or a file.

## Status after Track C (2026-09-14): option E tested — FAILED at the registered costs

| Item | Result | What would change it |
|---|---|---|
| A43 S1/S2/S3 (defined-risk short 0DTE premium) | All FAIL: -8.6 / -5.0 / -6.8 % of max loss per structure at $0.10/leg; drawdowns 104–198 % at the 4 % rule | Only a cost assumption near $0.03 per leg (breakeven) — a new pre-registration (A43b), and even then roughly breakeven, not an edge |
| The premium itself | Real: the short legs earn +0.26/+0.24 per share per day; the wings give back -0.14/-0.07; the rest is spread | A naked straddle at ~$0.03/leg would net ≈ $0.20/share/day with an unbounded tail — not a defined-risk account's trade |

Recommendation unchanged in direction, sharpened by the number: no account is worth opening for E. Options A (stop) and B (passive forward test, A44) remain; C waits for the assets file.

## Status after the inversion research (2026-09-15; judge DONE on 6c88943, tidied at a9eab64)

The owner directed a reverse-thinking research pass — what day and swing traders do wrong, and
whether the inverse of each mistake is reachable under the account constraint — delivered as
`INVERSION.md` with evidence in `notes/inversion/` (u1, u2, u3, u5). No run was launched and the
trial family is unchanged at 42 (43 once A44 runs).

| Finding | Consequence for the block |
|---|---|
| Of 24 failure modes, 3 have an inverse the account can take (all process disciplines), 11 can only be avoided, 10 are unreachable because the winning side requires selling, overnight, shares or being the intermediary (`INVERSION.md` §1 counts) | The goal condition stays unsatisfiable on the data on the branch |
| The largest measured effect in the programme remains the forbidden sell-side premium (A42; `INVERSION.md` §3) | Unchanged |
| Exactly one candidate survived the screen, the intraday forced-flattening rebound (`INVERSION.md` §5), LOW prior, projected n ≈ 151 modelled / ≈ 65–68 real-priced, UNDERPOWERED by construction on current data, three trials if registered | A new owner option, not a way out of the block |

### Owner options, updated

- **A. Stop.** The finding stands on three data sets and 39 pre-registered trials: no long-only 0DTE mechanism clears its cost.
- **B. Forward test** the overnight-loss call (symmetric spec) on sessions after 2026-09-11; no data needed, ≈ 2 years to 200 signals.
- **C/D. Leveraged-ETF candidate** (A38): built and waiting for `data/ext/letf_aum_2006_2026.csv`.
- **F. Adopt any of the four new rules in `INVERSION.md` §4** (per-trade fraction and attempts cap, which amends `ACCEPTANCE.md:108-112`; no first-30-minute entries; no size or frequency increase after a loss; resting mid limit orders, which needs the no-live-execution non-goal relaxed before it can be measured) — each adoption is its own `ACCEPTANCE.md` amendment.
- **G. Pre-register the §5 candidate as three trials** (family 42 → 45, or 43 → 46 after A44), run it modelled on 2020-07→2026-09 with a real-priced sub-window check on the 2024–2026 shards, accepting that the likely label is UNDERPOWERED and that the kill criterion is the mirror-asymmetry test that already failed for A39.

No agent is launched against the automated stop hook; the run resumes on a letter (A–G) or a file.

