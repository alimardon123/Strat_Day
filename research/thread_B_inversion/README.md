# Reverse-Logic Trading Study

Tests whether inverting a losing strategy produces a profitable one, using
S&P 500 1-minute bars (2013-2018).

## Run order
```
pip install pandas numpy
python3 loader.py          # sanity-check the data
python3 step1_baseline.py  # build the losing strategy  -> baseline_trades.pkl
python3 step2_inversion.py # mirror + symmetric inversion
python3 step3_sweep.py     # stop-cascade excursion study + matched controls
python3 step4_regime.py    # conditional polarity, train/test split
```

## Getting the data
```
mkdir data
B=https://raw.githubusercontent.com/FutureSharks/financial-data/master/pyfinancialdata/data/stocks/histdata/SPXUSD
for y in 2013 2014 2015 2016 2017 2018; do
  curl -sfL "$B/DAT_ASCII_SPXUSD_M1_${y}.csv" -o data/spx_${y}.csv
done
```

## Swapping in your own strategy
Replace `build_signals()` in `step1_baseline.py`. Everything downstream —
inversion, sweep study, regime split — runs unchanged.

See RESULTS.md for findings.

## Part 2 — broad hypothesis search
```
python3 step5_sweep.py     # 282 structural/behavioural hypotheses -> sweep_raw.pkl
python3 step6_correct.py   # day-block bootstrap + Benjamini-Hochberg FDR
python3 step7_validate.py  # cross-market out-of-sample test of the best candidate
```
Extra data for step 7 (DAX / Nikkei / EuroStoxx + SPX holdout years):
```
B=https://raw.githubusercontent.com/FutureSharks/financial-data/master/pyfinancialdata/data/stocks/histdata
for s in GRXEUR JPXJPY ETXEUR; do for y in $(seq 2010 2018); do
  curl -sfL "$B/$s/DAT_ASCII_${s}_M1_${y}.csv" -o data/${s}_${y}.csv; done; done
for y in 2010 2011 2012; do curl -sfL "$B/SPXUSD/DAT_ASCII_SPXUSD_M1_${y}.csv" -o data/SPXHOLD_${y}.csv; done
```
python3 step8_execution.py  # limit vs market entry, with adverse selection

See RESULTS.md, RESULTS_PART2.md, RESULTS_PART3.md for findings.

## Part 3-4 — execution and alternative axes
python3 step8_execution.py   # limit vs market entry, adverse selection modelled
python3 step9_axes.py        # holding period / time zone / cross-section
python3 step10_fixed.py      # same, with look-ahead removed (see RESULTS_PART4.md)


## Part 5 — quadrant 2: the variance risk premium
curl -sfL https://raw.githubusercontent.com/datasets/finance-vix/main/data/vix-daily.csv -o data/vix.csv
python3 step11_vrp.py        # VIX vs subsequent realised vol — see RESULTS_PART5.md


## Part 6 — structural flow + the frequency law
python3 step12_flow.py       # expiry / month-end / quarter-end effects
python3 step13_law.py        # cost drag = cost x frequency / vol  (RESULTS_PART6.md)


## Part 7 — what VIX predicts before the open
python3 step14_vix_intraday.py   # range vs direction vs character (RESULTS_PART7.md)


## Part 8 — 0DTE mechanics
python3 step15_odte.py   # Black-Scholes 0DTE sim on minute data (RESULTS_PART8.md)


## Part 9 — autonomous signal hunt with cross-asset data
python3 step16_crossasset.py   # gold/oil/bonds/Nikkei -> US session (RESULTS_PART9.md)


## Part 10 — the signal (market intraday momentum, VIX-conditioned)
curl for oanda SPX500_USD 2019-2020 as in step 16
python3 step17_intramom.py   # replication + holdout + VIX conditioning (RESULTS_PART10.md)

