import numpy as np, pandas as pd, warnings; warnings.filterwarnings("ignore")
from it8 import *
from it7 import dipscore, trades

raw,C = load_prices()
R=C.pct_change()
# inverse-vol scaling: standard risk-parity sizing, uses only trailing data
iv=(1.0/(R.rolling(60).std().shift(1))).replace([np.inf,-np.inf],np.nan)

def tsmom_iv(C,lb=252):
    sig=(C/C.shift(lb)-1>0).shift(1).astype(float).where(C.shift(lb).notna())
    w=(sig*iv); w=w.div(w.sum(axis=1).replace(0,np.nan),axis=0).fillna(0.0)
    turn=w.diff().abs().sum(axis=1).fillna(0.0)
    return (w*R).sum(axis=1)-turn*COST_BPS/10000.0

def xsmom_iv(C,lb=252,frac=3):
    mom=(C/C.shift(lb)-1).shift(1); rk=mom.rank(axis=1,pct=True)
    n=mom.notna().sum(axis=1)
    lw=((rk>1-1/frac).astype(float)*iv); sw=((rk<1/frac).astype(float)*iv)
    lw=lw.div(lw.sum(axis=1).replace(0,np.nan),axis=0)
    sw=sw.div(sw.sum(axis=1).replace(0,np.nan),axis=0)
    w=(lw.fillna(0)-sw.fillna(0)).where(n>=8,0.0)
    turn=w.diff().abs().sum(axis=1).fillna(0.0)
    return (w*R).sum(axis=1)-turn*COST_BPS/10000.0

d=raw["spy"].reset_index(); d.columns=["date","open","high","low","close"]; d=dipscore(d)
t=trades(d,(d.score>=0.35).values,2.0,1.0,5,cost_bps=COST_BPS)
s1=pd.Series(0.0,index=C.index); spyr=C["spy"].pct_change()
for _,x in t.iterrows():
    m=(C.index>pd.Timestamp(x.entry_date))&(C.index<=pd.Timestamp(x.exit_date))
    if m.sum()>0: s1[m]+=spyr[m].values
S=pd.concat([s1.rename("S1_MEANREV"),tsmom_iv(C).rename("S2_TSMOM"),
             xsmom_iv(C).rename("S3_XSMOM"),s4_turn_of_month(C).rename("S4_TURNMONTH")],
            axis=1).fillna(0.0)
S=S.loc[S.index>=C.dropna(how="all").index.min()+pd.Timedelta(days=400)]
V=S.apply(vol_target)                       # each sleeve to 10% vol, trailing only
S.to_pickle("it8b_raw.pkl"); V.to_pickle("it8b_vt.pkl")

print("=== SLEEVES after inverse-vol sizing + 10% vol targeting (full sample) ===")
for c in V.columns: show(perf(V[c],c))
cm=V.corr(); iu=np.triu_indices_from(cm.values,1); rho=np.nanmean(cm.values[iu])
print(f"\nmean pairwise strategy correlation = {rho:.3f} -> n_eff = {4/(1+3*max(rho,0)):.2f}")

SPLIT="2012-01-01"
print(f"\n=== COMBINED PORTFOLIO — equal weight across the four sleeves ===")
for lbl,m in [("TRAIN 2006-2011",V.index<SPLIT),("TEST  2012-2017",V.index>=SPLIT)]:
    print(f"  --- {lbl} ---")
    comb=V[m].mean(axis=1)
    for c in V.columns: show(perf(V[m][c],"   "+c))
    show(perf(comb,"   COMBINED (equal weight)"))
    show(perf(spyr.reindex(V.index)[m].fillna(0),"   BENCH buy&hold SPY"))
