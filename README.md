# Strat_Day — 0DTE research programme

## Start here

**[`FINDING.md`](FINDING.md) — the one-page answer.** What was asked, what was tested, what was found, and what
would change it. Everything else in this repository is the evidence behind that page.

**Short version:** 48 pre-registered trials across three data sets; **0 pass the family-wide false-discovery
correction**. Under the account constraint (0DTE options only, long-only, naked calls or puts, no overnight) the
permitted instrument reduces to a leveraged intraday position with a hard 2% stop, and no directional edge found
here pays its 1-2 index points of spread. The one large effect the programme did measure — the 0DTE variance
risk premium, 3.6-11% of premium per session before costs (7-17% after a $0.10 round trip) — is on the sell side, which the account forbids.

## The deliverables

| file | what it is |
|---|---|
| `FINDING.md` | **The answer, one page.** Read this first |
| `PLAYBOOK_0DTE.md` | The constrained book. Every number generated from `out/`, never typed. §15 is the adopted risk rulebook; §16-19 are the validations |
| `OWN_ACCOUNT.md` | The unconstrained (stock-account) track, secondary |
| `BLOCKED.md` | The owner's options, each with its measured price |
| `ASSESSMENT.md` | Where every done-statement landed, and every gap with a root cause |
| `SCORECARD.md` | The trial ledger |

## The contract and the record

| file | what it is |
|---|---|
| `ACCEPTANCE.md` | **Append-only.** The contract: done-statements, the six-condition survival rule, numeric budgets, non-goals, and every amendment (A1-A50) pre-registered before its code was written |
| `CRITIQUE.md` | Every review round, every defect, and its disposition |
| `RETRO.md` | Process findings and the guards they earned |
| `CHANGELOG.md` | What changed, when, and what was verified |
| `DATA.md` / `ARCHITECTURE.md` / `PLAN.md` | Inputs, ownership map, ranked task list |
| `INVERSION.md` | The reverse-thinking pass: trader failure modes and whether their inverses are reachable here |
| `TRACK_B.md` / `TRACK_C.md` | The swing-start detector, and the defined-risk short-premium track |
| `research/` | The prior two threads' bundle, **verbatim and never edited** |

## How to reproduce

```
make fetch     # populates data/raw from GitHub mirrors (~13 min); data/ext is committed
make all       # regenerates every table and every generated document (~17 min, 36 steps)
make repeat    # runs it again and diffs; must print "REPEAT: byte-identical"
```

Verified from a genuinely clean clone at commit 96a1431: 36/36 steps, and `diff -r` against the committed `out/`
returned **nothing** across all 177 files, with all four generated documents matching by md5.

## Two things a reader should know

1. **Tables are generated, never typed.** Anything in `PLAYBOOK_0DTE.md`, `OWN_ACCOUNT.md`, `TRACK_B.md` or
   `TRACK_C.md` comes from `out/`. Editing them by hand is a defect; edit `pipeline/report*.py` instead.
2. **`out/trials.csv` has a trial label containing a comma inside a quoted field.** A naive `awk -F','` split
   misreads that row. Use a real CSV parser. The correct figure is 48 trials, 0 passing.
