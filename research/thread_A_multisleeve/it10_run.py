import pandas as pd, numpy as np, warnings; warnings.filterwarnings("ignore")
from it8 import load_prices, vol_target, perf, show, COST_BPS
from it10 import session_returns, effective_bets, strategy_momentum_weights
raw,C=load_prices(); OV,IT,TOT=session_returns(raw)
V=pd.read_pickle("it9_vt.pkl"); keep=pd.read_pickle("it9_keep.pkl")
SPLIT="2012-01-01"

# ---- S7: overnight-alpha TILT. Monthly rebalance only -> no daily cost wall.
onsh=(OV.rolling(252).mean()/OV.rolling(252).std()).shift(1)      # trailing overnight Sharpe
iv=(1/TOT.rolling(60).std().shift(1)).replace([np.inf,-np.inf],np.nan)
rk=onsh.rank(axis=1,pct=True); n=onsh.notna().sum(axis=1)
w=((rk>0.66).astype(float)*iv)
w=w.div(w.sum(axis=1).replace(0,np.nan),axis=0).where(n>=8,0.0)
mstart=~w.index.to_period("M").duplicated()                        # rebalance monthly
w=w.where(pd.Series(mstart,index=w.index),np.nan).ffill().fillna(0.0)
turn=w.diff().abs().sum(axis=1).fillna(0.0)
s7=((w*TOT).sum(axis=1)-turn*COST_BPS/10000).rename("S7_ONTILT")
# control: same construction, random ranks
rng=np.random.default_rng(4)
rr=pd.DataFrame(rng.random(onsh.shape),index=onsh.index,columns=onsh.columns).rank(axis=1,pct=True)
wc=((rr>0.66).astype(float)*iv); wc=wc.div(wc.sum(axis=1).replace(0,np.nan),axis=0).where(n>=8,0.0)
wc=wc.where(pd.Series(mstart,index=wc.index),np.nan).ffill().fillna(0.0)
s7c=((wc*TOT).sum(axis=1)-wc.diff().abs().sum(axis=1).fillna(0)*COST_BPS/10000)

print("=== IDEA A (cost-aware): overnight-alpha tilt, monthly rebalance ===")
for lbl,m in [("TRAIN",V.index<SPLIT),("TEST ",V.index>=SPLIT)]:
    a=perf(vol_target(s7).reindex(V.index).fillna(0)[m],""); b=perf(vol_target(s7c).reindex(V.index).fillna(0)[m],"")
    print(f"  {lbl}  S7 Sharpe={a['sharpe']:>5.2f}  maxDD={a['maxdd']*100:>6.2f}%   |  random-rank control Sharpe={b['sharpe']:>5.2f}")

V2=V.copy(); V2["S7_ONTILT"]=vol_target(s7).reindex(V.index).fillna(0)
keep2=keep+["S7_ONTILT"]
base=V[keep].mean(axis=1)
with7=V2[keep2].mean(axis=1)

# ---- IDEA B: scale gross exposure by trailing effective bets
nb=effective_bets(V2[keep2])
scale=(nb/nb.rolling(504,min_periods=100).median()).clip(0.5,1.5).fillna(1.0)
ideaB=with7*scale

# ---- IDEA C: strategy momentum weights
Wm=strategy_momentum_weights(V2[keep2])
ideaC=(V2[keep2]*Wm).sum(axis=1)

print("\n=== ALL THREE IDEAS vs the iteration-9 baseline ===")
print(f"  {'variant':<34}{'TRAIN Sharpe':>14}{'TEST Sharpe':>13}{'TEST maxDD':>12}")
for lbl,r in [("baseline (5 sleeves, it9)",base),("A: + overnight tilt (6 sleeves)",with7),
              ("B: + correlation-scaled exposure",ideaB),("C: + strategy-momentum weights",ideaC)]:
    a=perf(r[V.index<SPLIT].dropna(),""); b=perf(r[V.index>=SPLIT].dropna(),"")
    print(f"  {lbl:<34}{a['sharpe']:>14.2f}{b['sharpe']:>13.2f}{b['maxdd']*100:>11.2f}%")
pd.to_pickle({"base":base,"A":with7,"B":ideaB,"C":ideaC,"nb":nb},"it10_out.pkl")
print(f"\n  trailing effective bets: median {nb.median():.2f}, range [{nb.min():.2f}, {nb.max():.2f}]")
