"""Step 6 — discount the sweep for how many questions were asked, then apply the cost wall.

Block bootstrap (whole trading days) gives p-values that respect intraday autocorrelation.
Benjamini-Hochberg controls false-discovery rate across ALL 282 tests, not just winners.
"""
import numpy as np
import pandas as pd
from stats_engine import block_bootstrap_p, bh_fdr

COSTS = {"ES spread only": 0.25, "ES + commission": 0.33, "CFD": 0.50}

res = pd.read_pickle("sweep_raw.pkl")
print(f"tests: {len(res)}")

# one-sided bootstrap p on the TEST set (direction was locked on train)
pv = []
for _, r in res.iterrows():
    p = block_bootstrap_p(r["_v"], r["_d"], n_boot=1500)
    pv.append(p / 2 if r["te_mean"] > 0 else 1.0)   # one-sided
res["p_boot"] = pv

res["fdr_pass"] = bh_fdr(res["p_boot"].to_numpy(), alpha=0.10)
print(f"survive Benjamini-Hochberg FDR 10% across all {len(res)} tests: {res['fdr_pass'].sum()}")
print(f"survive Bonferroni (p < {0.05/len(res):.5f}): {(res['p_boot'] < 0.05/len(res)).sum()}\n")

win = res[res["fdr_pass"]].sort_values("te_mean", ascending=False)
print("=" * 108)
print("SURVIVORS — effect measured in SPX index points per trade, direction fixed on train")
print("=" * 108)
print(f"{'condition':>22} {'hz':>6} {'dir':>4} {'n':>6} {'train':>8} {'TEST':>8} {'t':>6} {'p_boot':>8} "
      f"{'net@.25':>8} {'net@.33':>8}")
for r in win.itertuples():
    print(f"{r.cond:>22} {r.hz:>6} {r.dir:>+4d} {r.te_n:>6} {r.tr_mean:>+8.3f} {r.te_mean:>+8.3f} "
          f"{r.te_t:>+6.2f} {r.p_boot:>8.4f} {r.te_mean-0.25:>+8.3f} {r.te_mean-0.33:>+8.3f}")

print("\n" + "=" * 108)
print("COST WALL — how many survivors are still positive after realistic round-trip cost")
print("=" * 108)
for nm, c in COSTS.items():
    alive = win[win["te_mean"] > c]
    print(f"  {nm:>18} ({c:.2f} pts): {len(alive):>2d} of {len(win)} survivors remain positive")
    for r in alive.itertuples():
        print(f"        -> {r.cond} @ {r.hz}: {r.te_mean-c:+.3f} pts/trade net, n={r.te_n}")

res.drop(columns=["_v", "_d"]).to_pickle("sweep_scored.pkl")
