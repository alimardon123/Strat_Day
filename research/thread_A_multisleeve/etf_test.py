import numpy as np, pandas as pd, glob, os, warnings; warnings.filterwarnings("ignore")
from it5 import dipscore
D="/home/claude/etfs/CMSC320_Final_Tutorial_Huge_Stock_Market_Dataset-main/ETFs"
COST=2.0  # bp per side, ETFs
# PRE-REGISTERED index-ETF list, chosen before seeing any result (ASSESSMENT it4 §5)
CORE="spy qqq iwm dia mdy rsp efa eem vti ijh ijr xlf xlk xle xlv xli xlp xlu xly xlb ewj ewg ewu fxi iyr smh".split()

def run(df,sig,sm,tm,mh,cost_bps=COST):
    o,h,l,c=df.open.values,df.high.values,df.low.values,df.close.values
    atr=df.atr14.values; dt=df.date.values; n=len(df); cost=cost_bps*2/10000
    out=[];i=0;sig=np.asarray(sig,bool)
    while i<n-1:
        if not sig[i] or not np.isfinite(atr[i]) or atr[i]<=0: i+=1; continue
        e=i+1; entry=o[e]; risk=sm*atr[i]
        stop,targ=entry-risk,entry+tm*atr[i]; px=None
        for j in range(e,min(e+mh+1,n)):
            if j==e and o[j]<=stop: px=o[j]
            elif l[j]<=stop: px=stop
            elif h[j]>=targ: px=targ
            if px is not None: break
        if px is None: j=min(e+mh,n-1); px=c[j]
        p=(px/entry-1)-cost; out.append((dt[e],p,p*entry/risk)); i=j+1
    return pd.DataFrame(out,columns=["date","pnl","r"])

def load(sym):
    p=f"{D}/{sym}.us.txt"
    if not os.path.exists(p): return None
    df=pd.read_csv(p)
    df.columns=[x.strip().lower() for x in df.columns]
    df["date"]=pd.to_datetime(df.date,errors="coerce")
    df=df.dropna(subset=["date","open","high","low","close"]).sort_values("date").reset_index(drop=True)
    if len(df)<1200 or df.close.median()<10: return None
    if (df.close*df.volume).median()<5e6: return None
    df["high"]=df[["open","high","close"]].max(axis=1); df["low"]=df[["open","low","close"]].min(axis=1)
    return dipscore(df[["date","open","high","low","close","volume"]].copy())

GEOS=[("wide",2.0,1.0,5),("one_two",1.0,2.0,10)]
rows=[];tr=[]
for sym in CORE:
    df=load(sym)
    if df is None: print(f"  skip {sym}"); continue
    rr=np.random.default_rng(abs(hash(sym))%2**31)
    for g,sm,tm,mh in GEOS:
        s=run(df,(df.score>=0.35).values,sm,tm,mh)
        c=run(df,(df.up & (rr.random(len(df))<0.03)).values,sm,tm,mh)
        if len(s)<10: continue
        rows.append(dict(sym=sym,geo=g,n=len(s),win=(s.r>0).mean(),meanR=s.r.mean(),
                         ctrl=c.r.mean(),excess=s.r.mean()-c.r.mean(),
                         start=str(df.date.min().date()),end=str(df.date.max().date())))
        tr.append(s.assign(sym=sym,geo=g,kind="s")); tr.append(c.assign(sym=sym,geo=g,kind="c"))
R=pd.DataFrame(rows); T=pd.concat(tr); T["date"]=pd.to_datetime(T.date)
R.to_csv("etf_rows.csv",index=False); T.to_pickle("etf_trades.pkl")
print(f"\nETFs tested: {R.sym.nunique()} | span {R.start.min()} -> {R.end.max()} | trades {int(R.n.sum())}")
