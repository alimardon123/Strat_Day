# CRITIQUE.md — open and resolved findings

Phase 0 tribunal (2026-09-12): four fresh-context hostile lenses (statistician, 0DTE
practitioner, infrastructure engineer, mission-fidelity) attacked the upgraded prompt,
ACCEPTANCE.md v1, DATA.md and PLAN.md. 32 findings. Dispositions below; ADOPTED items are
already in ACCEPTANCE.md v2 and the pipeline. Root cause precedes every fix.

| # | Sev | Lens | Finding (short) | Root cause | Disposition |
|---|---|---|---|---|---|
| 1 | 9 | practitioner | 54% loss-at-stop used to size trades that have no stop; max loss is 100% of premium | Thread B's 53.8% was measured on ATM calls with a 1.5-ATR stop | ADOPTED: size on measured worst trade with a 100% floor; MAE; combined-book worst day (budgets, A17) |
| 2 | 9 | statistician | Thread B's Oanda holdout (n=85, SR 1.67) is DST-misaligned and not produced by step17 | step17 detects one open minute on naive UTC stamps | CONFIRMED by replication (legacy mode reproduces n=85/+0.0975/1.67 exactly; winter sessions measured 14:30→15:00 ET and carried +0.236 vs summer +0.019). ADOPTED as A22 (c1/c2) |
| 3 | 8 | statistician | Holdout p<0.10 across all 8 candidates is a second selection | Rule conflated confirmation with filtering | ADOPTED: rank in-sample, ONE holdout test, others POST-SELECTION |
| 4 | 8 | engineer | Same as #2 from the code side | — | ADOPTED with #2 |
| 5 | 8 | engineer | Largest-|Δclose|-minute DST probe is dominated by 08:30/10:00 releases | Wrong statistic | REFUTED as of Phase 2: the probe was already replaced by the sustained 15-minute activity step at 08:30/09:30/10:30, which passes 47/47 months; the Sunday-first-bar anchor is added as an informational column |
| 6 | 7 | practitioner | ES continuous roll jumps and SPX stale open have no rule | Only SPY got a cleaning rule | ADOPTED: ext_manifest.json, roll handling, SPX open/close definitions (A6) |
| 7 | 7 | statistician | DSR undefined (V[SR], T, trial definition) | Under-specified | ADOPTED: A15, A31, survival rule 5 |
| 8 | 7 | statistician | Thread A ±0.3 tolerance on an option return with unpinned conventions | it22 script missing | ADOPTED: hard/soft gate (A30); convention inferred from evidence and logged |
| 9 | 7 | mission | 2013→2020-05 is Thread B's fit window; ranking rigged | 17.06/0.665 fitted on 2010–2018 | ADOPTED: vixmove gate re-derived as an expanding rule and as a frozen pre-2013 fit; literal thresholds reported, not ranked |
| 10 | 7 | engineer | Month blocks give p=1.0 for every per-year row | 20-block guard | ADOPTED: day blocks per year, NA below 20 blocks (rule 2, A26) |
| 11 | 6 | practitioner | k-sensitivity is null at 2% ITM with <1 h; spread is the real axis | Time value ≈ 0 | ADOPTED (confirmed by options sanity: identical premium at k=1.0/1.3/1.6): spread {1,2,3}; k for 13:00 leg only |
| 12 | 6 | practitioner | SPY 0DTE is physically settled → overnight shares; SPX cash-settled | Settlement unstated | ADOPTED: A28 per-instrument settlement; SPY exits by 15:55 |
| 13 | 6 | statistician | block_bootstrap_p is two-sided, 20-block floor, module RNG | Function semantics | ADOPTED (already in stats.py: per-call seed, one-sided convention); halves with month blocks |
| 14 | 6 | statistician | Same-day random-minute control collapses into "mean > 0" | Wrong null | ADOPTED: day-selection control is the survival test; timing control reported (A16) |
| 15 | 6 | mission | "extended data" vs "holdout" ambiguity lets full-sample numbers into the playbook | Loose wording | ADOPTED: D4 headline = holdout only |
| 16 | 6 | engineer | Old and new VXX never overlap; splice cannot be proven | Series B relaunch 2018 | ADOPTED: bridge via VIXY/VIXM (A13) |
| 17 | 5 | practitioner | Decision price = fill price in step17 | Bar-close fill | ALREADY HANDLED: pipeline enters at the next bar's open (A11); step17's convention only in the gate; difference logged |
| 18 | 5 | practitioner | Worst day per signal, not per book | Overlapping positions | ADOPTED (A17) |
| 19 | 5 | statistician | Asymmetric fitting; net Sharpe undefined across frequencies | — | ADOPTED: pre-2013 derivation; calendar-day Sharpe metric |
| 20 | 5 | statistician | "Frozen" vs "expanding" contradiction for the magnitude gate | — | ADOPTED: expanding is a rule; frozen variant is a counted trial |
| 21 | 5 | mission | Gate (c) references a table step17 cannot print; seed/one-sided claims mismatch the function | — | ADOPTED via A22 and stats.py |
| 22 | 5 | mission | P&L unit undeclared | — | ADOPTED: Units section |
| 23 | 5 | engineer | Price level cannot separate SPX from ES | — | ADOPTED: manifest (A6) |
| 24 | 5 | engineer | k=1.3 in A7 would be applied to the reproduction | — | ADOPTED: k=1.0 for every reproduction (A7) |
| 25 | 5 | engineer | Empty-output-exit-0 hides failed units | Contract | ADOPTED: `.error` + exit 2; run_all fails on empties (A32) |
| 26 | 4 | practitioner | Strike rounding to nearest can land < 2% ITM; SPY grid | — | ADOPTED (A8) |
| 27 | 4 | mission | VRP sleeve and cross-market silently dropped from D-list | — | ADOPTED: non-goal stated; D2b and D5 extended |
| 28 | 4 | mission | DSR N must include the trials that produced the candidate | — | ADOPTED (rule 5, A15) |
| 29 | 4 | engineer | Running step17 in place would dirty research/ | — | ADOPTED: never run in place (reproduce.py is a separate path); git-status check (A33) |
| 30 | 3 | statistician | Oanda 2017 feed hole and CFD-only sessions need a category | — | ADOPTED (A27 "feed gap"; VIX-calendar filter A4) |
| 31 | 3 | mission | `research/unified/CLAUDE.md` path, "2022 and 2024 holiday changes" placeholder, first output lacks commit hash | — | ADOPTED: paths corrected (A2); explicit calendar list in sessions.py; commit hash in every status |
| 32 | 3 | engineer | Oanda ends 2020-05-13, not 05-29 | Stated from HANDOFF, not the file | ADOPTED (A1; ext file from 2020-05-14) |

## Open

None from this round. Next tribunal: Phase 4, on the Phase 3 build.
