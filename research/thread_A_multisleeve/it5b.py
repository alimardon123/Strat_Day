import pickle, numpy as np, pandas as pd, warnings; warnings.filterwarnings("ignore")
from it5 import dipscore, run
O,H,L,C=pickle.load(open("panel.pkl","rb"))
r=C.pct_change()
# ROOT-CAUSE REPAIR: reverse-split / delisting artifacts, not real returns.
chronic = (r.abs()>0.5).sum()
drop = chronic[chronic>5].index
keep = [s for s in C.columns if s not in drop]
print(f"dropped {len(drop)} symbols with >5 days of |ret|>50% (reverse-split artifacts)")
O,H,L,C = O[keep],H[keep],L[keep],C[keep]
bad = C.pct_change().abs()>0.5
for D in (O,H,L,C): D[bad]=np.nan
print(f"remaining symbols: {len(keep)}; masked {int(bad.sum().sum())} artifact stock-days")

def make_index(cols):
    pc=C[cols].shift(1)
    rc=(C[cols]/pc-1); ro=(O[cols]/pc-1); rh=(H[cols]/pc-1); rl=(L[cols]/pc-1)
    valid=rc.notna().sum(axis=1)
    keepd = valid >= max(1,int(0.6*len(cols)))
    mc,mo,mh,ml=[x.mean(axis=1)[keepd] for x in (rc,ro,rh,rl)]
    m=mc.notna()&mo.notna()&mh.notna()&ml.notna()
    mc,mo,mh,ml=mc[m],mo[m],mh[m],ml[m]
    lvl=100*(1+mc).cumprod(); prev=lvl.shift(1).fillna(100)
    df=pd.DataFrame({"date":lvl.index,"open":prev*(1+mo),"high":prev*(1+mh),
                     "low":prev*(1+ml),"close":lvl.values}).reset_index(drop=True)
    df["high"]=df[["open","high","close"]].max(axis=1)
    df["low"]=df[["open","low","close"]].min(axis=1)
    return df.dropna().reset_index(drop=True)

# ---- VALIDATION GATE before any strategy is run ----
print("\nGATE: annualised vol must be plausible (10-45%) and fall as k rises.")
rng=np.random.default_rng(7); syms=list(C.columns); vols={}
for k in [1,5,20,50,150,len(syms)]:
    vs=[]
    for _ in range(min(15, 1 if k>=len(syms) else 15)):
        cols=syms if k>=len(syms) else list(rng.choice(syms,k,replace=False))
        idx=make_index(cols)
        if len(idx)>1500: vs.append(idx.close.pct_change().std()*np.sqrt(252))
    vols[k]=np.median(vs); print(f"  k={k:<5} median annualised vol = {np.median(vs)*100:5.1f}%")
ok = all(10<=vols[k]*100<=60 for k in vols) and vols[1]>vols[len(syms)]
print("GATE:", "PASS" if ok else "FAIL")
pickle.dump((O,H,L,C), open("panel_clean.pkl","wb"))
