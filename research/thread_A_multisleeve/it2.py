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
day["score"]=s.where(up,0.0); day["fire"]=day.score>=0.35
day["trade_date"]=day.date.shift(-1)
sd=day.loc[day.fire,["trade_date","atr14"]].dropna(); m=dict(zip(sd.trade_date,sd.atr14))
d["sigday"]=d.date.map(lambda x: x in m); d["patr"]=d.date.map(m)
print("signal days:",d[d.sigday].date.nunique())

def once(mask_series, dates):
    s=pd.Series(np.asarray(mask_series)); 
    return (s & (s.groupby(pd.Series(dates)).cumsum()==1)).values

V={}
V["open (baseline)"]=(d.sigday&(d.bar==1)).values
V["first VWAP reclaim"]=once((d.sigday&(d.close>d.vwap)&(d.close.shift(1)<=d.vwap)&(d.bar>=5)).values, d.date.values)
V["VWAP + session-high push"]=once((d.sigday&(d.close>d.vwap)&(d.close>=d.run_hi)&(d.bar>=30)).values, d.date.values)
V["15:30 entry"]=(d.sigday&(d.bar==360)).values

for split,mask in [("TRAIN 2005-2014",(d.yr<=2014).values),("TEST 2015-2020",(d.yr>=2015).values)]:
    x=d[mask].reset_index(drop=True); x["dayid"]=pd.factorize(x.date)[0]; ndx=x.date.nunique()
    print(f"\n===== {split}  ({ndx} sessions) =====")
    for nm,sf in V.items():
        sig=sf[mask]
        for stm,tgm in [(2.0,1.0),(1.0,2.0),(0.75,1.5)]:
            risk=(stm*x.patr).values
            t=backtest_md(x,sig,risk,(tgm*x.patr).values,5,1,nm)
            print("  "+fmt(f"{nm} [stop{stm}/targ{tgm}]", stats(t,ndx)))
