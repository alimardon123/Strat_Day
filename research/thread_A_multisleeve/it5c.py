import pickle, numpy as np, pandas as pd, warnings; warnings.filterwarnings("ignore")
from it5 import dipscore, run
O,H,L,C=pickle.load(open("panel_clean.pkl","rb"))
def make_index(cols):
    pc=C[cols].shift(1)
    rc=(C[cols]/pc-1); ro=(O[cols]/pc-1); rh=(H[cols]/pc-1); rl=(L[cols]/pc-1)
    valid=rc.notna().sum(axis=1); keepd=valid>=max(1,int(0.6*len(cols)))
    mc,mo,mh,ml=[x.mean(axis=1)[keepd] for x in (rc,ro,rh,rl)]
    m=mc.notna()&mo.notna()&mh.notna()&ml.notna(); mc,mo,mh,ml=mc[m],mo[m],mh[m],ml[m]
    lvl=100*(1+mc).cumprod(); prev=lvl.shift(1).fillna(100)
    df=pd.DataFrame({"date":lvl.index,"open":prev*(1+mo),"high":prev*(1+mh),
                     "low":prev*(1+ml),"close":lvl.values}).reset_index(drop=True)
    df["high"]=df[["open","high","close"]].max(axis=1); df["low"]=df[["open","low","close"]].min(axis=1)
    return df.dropna().reset_index(drop=True)
syms=list(C.columns); rng=np.random.default_rng(23)
GEOS=[("wide",2.0,1.0,5),("one_two",1.0,2.0,10)]
tr=[]
for k,reps in [(1,80),(5,60),(20,45),(50,35),(150,25),(len(syms),1)]:
    for rep in range(reps):
        cols=syms if k>=len(syms) else list(rng.choice(syms,k,replace=False))
        idx=make_index(cols)
        if len(idx)<1500: continue
        idx=dipscore(idx); rr=np.random.default_rng(5000+rep*7+k)
        for g,sm,tm,mh in GEOS:
            s=run(idx,(idx.score>=0.35).values,sm,tm,mh)
            c=run(idx,(idx.up & (rr.random(len(idx))<0.03)).values,sm,tm,mh)
            if len(s)<20 or len(c)<20: continue
            tr.append(s.assign(k=k,rep=rep,geo=g,kind="s"))
            tr.append(c.assign(k=k,rep=rep,geo=g,kind="c"))
    print(f"  k={k} done")
T=pd.concat(tr); T["date"]=pd.to_datetime(T.date); T.to_pickle("it5c_trades.pkl")
print("total trades:",len(T))

def blk(s,c):
    a=s.groupby("date").r.mean(); b=c.groupby("date").r.mean()
    j=pd.concat([a,b],axis=1,keys=["s","c"]).dropna(); d=j.s-j.c
    return d.mean(), d.mean()/(d.std()/np.sqrt(len(d))), len(d)

for geo in ["wide","one_two"]:
    print(f"\n=== {geo} : excess over matched control vs basket size ===")
    print(f"  {'k':>6}{'n_trades':>10}{'win%':>8}{'net R:R':>10}{'excess':>10}{'clust t':>9}   held-out 2015+")
    for k in sorted(T.k.unique()):
        x=T[(T.geo==geo)&(T.k==k)]
        s=x[x.kind=="s"]; c=x[x.kind=="c"]
        if len(s)<50: continue
        e,t,_=blk(s,c)
        w=s[s.r>0].r.mean(); l=abs(s[s.r<=0].r.mean())
        po=T.date>='2015-01-01'
        s2=x[(x.kind=="s")&po]; c2=x[(x.kind=="c")&po]
        e2,t2,_=blk(s2,c2) if len(s2)>50 else (np.nan,np.nan,0)
        print(f"  {k:>6}{len(s):>10}{(s.r>0).mean()*100:>8.1f}{'1:'+f'{w/l:.2f}':>10}"
              f"{e:>+10.4f}{t:>9.2f}   {e2:+.4f} (t={t2:.2f})")
