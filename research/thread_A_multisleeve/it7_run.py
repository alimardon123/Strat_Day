import numpy as np, pandas as pd, warnings; warnings.filterwarnings("ignore")
from it7 import load, dipscore, trades, SLEEVES, ALL
data={}; T=[]
for s in ALL:
    d=load(s)
    if d is None: print("skip",s); continue
    d=dipscore(d); data[s]=d
    rr=np.random.default_rng(abs(hash(s))%2**31)
    t=trades(d,(d.score>=0.35).values); c=trades(d,(d.up & (rr.random(len(d))<0.03)).values)
    if len(t)<15: continue
    T.append(t.assign(sym=s,kind="s")); T.append(c.assign(sym=s,kind="c"))
T=pd.concat(T,ignore_index=True); T.to_pickle("it7_trades.pkl")
import pickle; pickle.dump({k:v[["date","close"]] for k,v in data.items()},open("it7_px.pkl","wb"))
print("assets:",T.sym.nunique(),"| strategy trades:",int((T.kind=='s').sum()))

# effective independent bets across the multi-asset universe
P=pd.concat({k:v.set_index("date").close for k,v in data.items()},axis=1).pct_change()
P=P.dropna(how="all")
cm=P.corr().values; iu=np.triu_indices_from(cm,1); rho=np.nanmean(cm[iu])
n=cm.shape[0]; neff=n/(1+(n-1)*max(rho,0))
print(f"\nmean pairwise correlation across {n} assets = {rho:.3f}")
print(f"EFFECTIVE INDEPENDENT BETS = {neff:.2f}   (26 index ETFs gave 1.28)")

s=T[T.kind=='s']
print(f"\npooled: n={len(s)} win={(s.r>0).mean()*100:.1f}% meanR={s.r.mean():+.4f}")
per=s.groupby("sym").r.agg(['size','mean',lambda x:(x>0).mean()])
per.columns=['n','meanR','win']
ctrl=T[T.kind=='c'].groupby("sym").r.mean()
per['ctrl']=ctrl; per['excess']=per.meanR-per.ctrl
per=per.sort_values('excess',ascending=False)
print("\nper-asset (wide-stop):")
print(per.round(4).to_string())
print(f"\npositive excess: {(per.excess>0).sum()}/{len(per)} | mean excess {per.excess.mean():+.4f}")
print(f"correlation-adjusted t = {per.excess.mean()/(per.excess.std()/np.sqrt(neff)):.2f}  (bar = 2.99)")
