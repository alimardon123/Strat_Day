import glob, sys, pandas as pd, numpy as np
from multiprocessing import Pool
from fleet_worker import worker
files = sorted(glob.glob("/home/claude/xs/big_movers-main/collected_stocks/*.csv"))
print("symbols to fan out:", len(files))
with Pool(4) as p:
    res = p.map(worker, files, chunksize=8)
rows = [r for sub in res for r in sub]
df = pd.DataFrame(rows)
df.to_csv("fleet_results.csv", index=False)
print("symbols passing liquidity/history filters:", df.sym.nunique())
print("total trades pooled:", int(df.n.sum()))
