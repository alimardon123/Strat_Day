"""Step 11 — quadrant 2: get PAID to hold risk, instead of predicting direction.

The variance risk premium: implied volatility (VIX) systematically exceeds the
volatility that subsequently materialises. This is not a mispricing waiting to be
arbitraged away — it is the price of insurance. Someone has to sell the hedge, and
they demand compensation. That compensation persists precisely BECAUSE it is
compensation for something genuinely unpleasant.

Test: VIX(t) vs realised vol of SPX over the following 21 trading days.
Then the honest part — what selling it actually feels like.
"""
import numpy as np
import pandas as pd
from stats_engine import block_bootstrap_p
from step9_axes import daily_frame

WINDOW = 21   # trading days ~ VIX's 30 calendar days


def spx_daily():
    a = daily_frame("data/SPXHOLD_*.csv")
    b = daily_frame("data/spx_*.csv")
    d = pd.concat([a, b])
    d = d[~d.index.duplicated()].sort_index()
    d["ret"] = np.log(d["close"]).diff()
    return d


def build():
    spx = spx_daily()
    vix = pd.read_csv("data/vix.csv", parse_dates=["DATE"]).set_index("DATE")
    vix.index = vix.index.date
    df = spx.join(vix[["CLOSE"]].rename(columns={"CLOSE": "vix"}), how="inner")

    # forward realised vol, annualised, in vol points
    fwd = df["ret"].shift(-1).rolling(WINDOW).std().shift(-(WINDOW - 1))
    df["rv_fwd"] = fwd * np.sqrt(252) * 100
    df["vrp"] = df["vix"] - df["rv_fwd"]           # premium in vol points
    return df.dropna(subset=["vrp"])


if __name__ == "__main__":
    df = build()
    print(f"sessions: {len(df)}  {df.index.min()} -> {df.index.max()}\n")

    print("=" * 76)
    print("VARIANCE RISK PREMIUM — implied (VIX) minus subsequently realised vol")
    print("=" * 76)
    v = df["vrp"]
    p = block_bootstrap_p(v.to_numpy(), pd.PeriodIndex(pd.to_datetime(df.index), freq="M").astype(str), 2000)
    print(f"  mean VIX            {df['vix'].mean():6.2f}")
    print(f"  mean realised vol   {df['rv_fwd'].mean():6.2f}")
    print(f"  mean premium        {v.mean():+6.2f} vol points")
    print(f"  premium positive    {100*(v>0).mean():5.1f}% of days")
    print(f"  bootstrap p (monthly blocks) {p/2:.5f}")

    print("\n  by year:")
    yr = df.groupby(pd.to_datetime(df.index).year).agg(
        vix=("vix", "mean"), rv=("rv_fwd", "mean"), vrp=("vrp", "mean"))
    yr["pos%"] = df.groupby(pd.to_datetime(df.index).year)["vrp"].apply(lambda x: 100*(x>0).mean())
    print(yr.round(2).to_string())

    print("\n" + "=" * 76)
    print("TRADING IT — sell 1 unit of variance each day, hold 21 days (overlapping)")
    print("=" * 76)
    # P&L proxy in vol points, non-overlapping so returns are independent
    nl = df.iloc[::WINDOW]
    pnl = nl["vrp"]
    sr = pnl.mean() / pnl.std() * np.sqrt(252 / WINDOW)
    print(f"  non-overlapping periods: {len(pnl)}")
    print(f"  mean per period  {pnl.mean():+6.2f} vol pts | win rate {100*(pnl>0).mean():.1f}%")
    print(f"  annualised Sharpe (before costs/leverage): {sr:+.2f}")
    print(f"  best period {pnl.max():+6.2f} | WORST period {pnl.min():+6.2f}")
    print(f"  ratio worst loss / mean gain: {abs(pnl.min())/pnl.mean():.1f}x")

    print("\n  worst 6 periods:")
    for d, x in pnl.nsmallest(6).items():
        print(f"    {d}  {x:+7.2f} vol pts   (VIX was {df.loc[d,'vix']:.1f}, realised {df.loc[d,'rv_fwd']:.1f})")

    print("\n" + "=" * 76)
    print("FEBRUARY 2018 — what the tail actually did")
    print("=" * 76)
    win = df.loc[[d for d in df.index if pd.Timestamp(d) >= pd.Timestamp('2018-01-15')
                  and pd.Timestamp(d) <= pd.Timestamp('2018-02-15')]]
    print(f"{'date':>12} {'VIX':>7} {'fwd RV':>8} {'premium':>9}")
    for d, r in win.iterrows():
        print(f"{str(d):>12} {r['vix']:>7.2f} {r['rv_fwd']:>8.2f} {r['vrp']:>+9.2f}")
    df.to_pickle("vrp.pkl")
