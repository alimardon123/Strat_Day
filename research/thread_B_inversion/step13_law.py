"""Step 13 — the law behind all twelve studies.

Every intraday result died at the same wall. This derives the wall in closed form and
checks it against the measured data.

Per trade:   net edge = e - c        (e = gross edge, c = round-trip cost, both in % of price)
Trade vol:   sigma_h = sigma_d * sqrt(h)     (h = holding period in days)
Annualised:  Sharpe = (e - c) / sigma_h * sqrt(252 / h)

Rearranged, the Sharpe you LOSE to costs is:

    cost drag = c * N / sigma_annual        where N = trades per year

Cost drag scales LINEARLY with trade frequency. That is the whole story: it does not
matter how good the signal is, only how many times you pay to use it.
"""
import numpy as np
import pandas as pd
from step9_axes import daily_frame

if __name__ == "__main__":
    spx = daily_frame("data/spx_*.csv")
    sigma_d = (np.log(spx["close"]).diff().std()) * 100
    sigma_a = sigma_d * np.sqrt(252)
    print(f"SPX daily vol {sigma_d:.3f}% | annualised {sigma_a:.1f}%\n")

    costs = {"ES futures (0.33 pts)": 100 * 0.33 / 2100,
             "tight retail (0.15 pts)": 100 * 0.15 / 2100,
             "CFD (0.50 pts)": 100 * 0.50 / 2100}

    print("=" * 84)
    print("COST DRAG ON ANNUAL SHARPE  =  cost_per_trade x trades_per_year / annual_vol")
    print("=" * 84)
    print(f"{'style':>34} {'trades/yr':>10}" + "".join(f"{k.split(' (')[0]:>16}" for k in costs))
    styles = [("scalping, 20/day", 5040), ("active day trading, 10/day", 2520),
              ("day trading, 4/day", 1008), ("this study's breakout", 9776),
              ("1 round trip per day", 252), ("swing, 2/week", 104),
              ("VRP, 21-day hold", 12)]
    for nm, n in styles:
        row = "".join(f"{c*n/sigma_a:>16.2f}" for c in costs.values())
        print(f"{nm:>34} {n:>10}{row}")

    print("\nRead the numbers as: the GROSS Sharpe you must achieve just to break even.")
    print("A world-class systematic fund runs a net Sharpe of roughly 1.0 - 2.0.\n")

    print("=" * 84)
    print("WHAT THIS STUDY ACTUALLY MEASURED, against that bar")
    print("=" * 84)
    rows = [("breakout, 9,776 trades", 9776, 0.0157, "died: needed gross Sharpe 9.7"),
            ("gap+ORB, ~1,600/yr", 1600, 0.0157, "died: needed 1.6, had ~0.3"),
            ("overnight hold, 252/yr", 252, 0.0157, "died: net SR 0.27 vs buy-hold 0.77"),
            ("structural flow, ~40/yr", 40, 0.0157, "died: no effect to harvest"),
            ("VRP, 12/yr", 12, 0.0157, "SURVIVED: net SR 2.10")]
    print(f"{'strategy':>28} {'N/yr':>7} {'needs gross SR':>16}   outcome")
    for nm, n, c, out in rows:
        print(f"{nm:>28} {n:>7} {c*n/sigma_a:>16.2f}   {out}")

    print("\n" + "=" * 84)
    print("THE DAY-TRADING CONSTRAINT, STATED HONESTLY")
    print("=" * 84)
    for n, lbl in [(1008, "4 trades/day"), (2520, "10 trades/day")]:
        for cname, c in costs.items():
            need = c * n / sigma_a
            print(f"  {lbl:>14} @ {cname:<24} needs gross Sharpe {need:>5.2f}")
    print("\n  For reference: Renaissance Medallion, the best-documented track record in")
    print("  finance, is estimated at gross Sharpe ~2-3 before fees, with proprietary data,")
    print("  co-located execution and institutional cost structure.")

    print("\n" + "=" * 84)
    print("WHAT WOULD MAKE DAY TRADING VIABLE — solve for allowable trade count")
    print("=" * 84)
    print(f"{'assumed gross Sharpe':>22} " + "".join(f"{k.split(' (')[0]:>18}" for k in costs))
    for gs in [1.0, 2.0, 3.0, 5.0]:
        row = "".join(f"{gs*sigma_a/c:>18.0f}" for c in costs.values())
        print(f"{gs:>22.1f} {row}")
    print("\n(cells = maximum trades per year before costs consume the entire edge)")
