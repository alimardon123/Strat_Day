import pandas as pd, numpy as np, warnings; warnings.filterwarnings("ignore")
from md import backtest_md
from mh import stats, fmt
d=pd.read_pickle("rth2.pkl")
day=d.groupby("date",sort=False).agg(open=("open","first"),high=("high","max"),low=("low","min"),close=("close","last")).reset_index()
c,h,l=day.close,day.high,day.low
pc=c.shift(1); tr_=pd.concat([h-l,(h-pc).abs(),(l-pc).abs()],axis=1).max(axis=1)
day["atr14"]=tr_.ewm(alpha=1/14,adjust=False).mean()
day["sma50"]=c.rolling(50).mean(); day["sma200"]=c.rolling(200).mean()
up=(c>day.sma200)&(day.sma200.diff(20)>0)
dl=c.diff(); u=dl.clip(lower=0).ewm(alpha=.5,adjust=False).mean(); dn=(-dl.clip(upper=0)).ewm(alpha=.5,adjust=False).mean()
rsi2=100-100/(1+u/dn.replace(0,np.nan)); ibs=(c-l)/(h-l).replace(0,np.nan)
ll10=l.rolling(10).min(); ret=c.pct_change()
ds=(ret<0).astype(int).groupby((ret>=0).cumsum()).cumsum()
rv=ret.rolling(20).std()*np.sqrt(252); vp=rv.rolling(504).rank(pct=True)
s=pd.Series(0.0,index=day.index)
s+=np.where(rsi2<10,.25,0)+np.where(rsi2<5,.10,0)+np.where(ibs<.20,.20,0)
s+=np.where(c<=ll10.shift(1),.20,0)+np.where(ds>=3,.15,0)+np.where(c<day.sma50,.10,0)
s+=np.where(vp<.80,.10,0)+np.where(vp>.90,-.15,0)
day["score"]=s.where(up,0.0); day["trade_date"]=day.date.shift(-1)

def daily_bar_backtest(day, fire, stm, tgm, maxd):
    """The OLD resolution: daily bars, stop wins any same-day tie."""
    o,hh,ll,cc=day.open.values,day.high.values,day.low.values,day.close.values
    atr=day.atr14.values; f=np.asarray(fire); out=[]; n=len(day); i=0
    while i<n-1:
        if not f[i] or not np.isfinite(atr[i]): i+=1; continue
        e=i+1; entry=o[e]; risk=stm*atr[i]
        stop=entry-risk; targ=entry+tgm*atr[i]; px=None
        for j in range(e,min(e+maxd,n)):
            if ll[j]<=stop: px="s"; pr=stop; break
            if hh[j]>=targ: px="t"; pr=targ; break
        if px is None: j=min(e+maxd-1,n-1); pr=cc[j]
        pnl=pr-entry-0.004-entry*0.0001
        out.append((pnl,pnl/risk,j-e+1))
        i=j+1
    return pd.DataFrame(out,columns=["pnl_pts","r","days"])

print("=== ABLATION: what did minute-path resolution actually buy? ===")
print("Same signal, same geometry. Only the stop-vs-target sequencing differs.")
for thr,lbl in [(0.35,"Tier B")]:
    fire=(day.score>=thr).values
    for stm,tgm in [(2.0,1.0),(1.0,2.0),(0.75,1.5)]:
        t=daily_bar_backtest(day,fire,stm,tgm,6)
        w=(t.r>0).mean()*100; rr=t[t.r>0].r.mean()/abs(t[t.r<=0].r.mean())
        print(f"  DAILY-BAR resolution [{stm}/{tgm}] {lbl}: n={len(t)} win={w:.1f}% R:R=1:{rr:.2f} meanR={t.r.mean():+.4f}")
print()

d["sigmap"]=None
for thr,lbl in [(0.55,"Tier A"),(0.35,"Tier B"),(0.20,"Tier C")]:
    sd=day.loc[day.score>=thr,["trade_date","atr14"]].dropna(); m=dict(zip(sd.trade_date,sd.atr14))
    d["sig"]=d.date.map(lambda x: x in m); d["patr"]=d.date.map(m)
    print(f"=== {lbl} (score>={thr}) — {d[d.sig].date.nunique()} signal days ===")
    for split,mask in [("TRAIN",(d.yr<=2014).values),("TEST ",(d.yr>=2015).values)]:
        x=d[mask].reset_index(drop=True); x["dayid"]=pd.factorize(x.date)[0]; ndx=x.date.nunique()
        sig=(d.sig&(d.bar==360)).values[mask]     # 15:30 entry, best of iteration 2
        for stm,tgm in [(1.0,2.0),(0.75,1.5)]:
            t=backtest_md(x,sig,(stm*x.patr).values,(tgm*x.patr).values,5,1,lbl)
            print(f"  {split} "+fmt(f"15:30 entry [{stm}/{tgm}]", stats(t,ndx)))
    print()
