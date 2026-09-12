import numpy as np, pandas as pd, warnings; warnings.filterwarnings("ignore")
from it8 import *
from it7 import dipscore, trades
raw,C = load_prices()
print("assets:",C.shape[1],"| span",C.index.min().date(),"->",C.index.max().date())

# S1: DipScore on SPY, converted to a daily return-on-capital stream
d=raw["spy"].reset_index().rename(columns={"index":"date"})
d.columns=["date","open","high","low","close"]; d=dipscore(d)
t=trades(d,(d.score>=0.35).values,2.0,1.0,5,cost_bps=COST_BPS)
s1=pd.Series(0.0,index=C.index)
for _,x in t.iterrows():
    # spread the trade's pnl across its holding window as a held position
    m=(C.index>pd.Timestamp(x.entry_date))&(C.index<=pd.Timestamp(x.exit_date))
    k=m.sum()
    if k>0: s1[m]+= C["spy"].pct_change()[m].values
s1.name="S1_MEANREV"

s2=s2_tsmom(C); s2.name="S2_TSMOM"
s3=s3_xsmom(C); s3.name="S3_XSMOM"
s4=s4_turn_of_month(C); s4.name="S4_TURNMONTH"
S=pd.concat([s1,s2,s3,s4],axis=1).fillna(0.0)
S=S.loc[S.index>=C.dropna(how="all").index.min()+pd.Timedelta(days=400)]
S.to_pickle("it8_streams.pkl")

print("\n=== RAW STRATEGY STREAMS (before vol targeting), full sample ===")
for c in S.columns: show(perf(S[c],c))
show(perf(C["spy"].pct_change().reindex(S.index).fillna(0),"BENCH buy&hold SPY"))

print("\n=== STRATEGY-RETURN CORRELATION — the number iteration 7 said matters ===")
cm=S.corr(); print(cm.round(3).to_string())
iu=np.triu_indices_from(cm.values,1); rho=np.nanmean(cm.values[iu])
n=S.shape[1]; print(f"\n  mean pairwise strategy correlation = {rho:.3f}")
print(f"  EFFECTIVE INDEPENDENT BETS = {n/(1+(n-1)*max(rho,0)):.2f}   "
      f"(23 assets, one rule, gave 1.78)")
