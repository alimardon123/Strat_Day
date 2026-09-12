"""D5 addendum (PLAN 7b) — VIX minus subsequent 21-day realised vol of SPY, 2000 → 2026-03
(Thread B step11's measurement; ACCEPTANCE A14: measured, labelled not-tradeable).

    python -m pipeline.vrp   → out/vrp_vix_minus_rv.csv
"""
import numpy as np
import pandas as pd


def main():
    spy = pd.read_parquet("data/raw/spy_daily.parquet").sort_values("date").set_index("date")["close"]
    vix = pd.read_parquet("data/raw/vix_daily.parquet").set_index("date")["close"]
    lr = np.log(spy).diff()
    rv = lr.rolling(21).std().shift(-21) * np.sqrt(252) * 100      # realised vol over the NEXT 21 sessions
    vprev = vix.reindex(spy.index, method="ffill").shift(1)          # prior close
    d = pd.DataFrame({"vix_prev": vprev, "rv_next21": rv}).dropna()
    d["premium"] = d["vix_prev"] - d["rv_next21"]
    y = d.groupby(d.index.year)["premium"].agg(mean="mean", pct_positive=lambda x: 100 * (x > 0).mean(), worst="min", n="size")
    total = pd.DataFrame([dict(mean=d["premium"].mean(), pct_positive=100 * (d["premium"] > 0).mean(), worst=d["premium"].min(), n=len(d))],
                         index=["ALL 2000-2026"])
    out = pd.concat([y, total])
    out.index.name = "year"
    out.reset_index().to_csv("out/vrp_vix_minus_rv.csv", index=False, float_format="%.4f")
    print(out.to_string(float_format=lambda x: f"{x:.2f}"))


if __name__ == "__main__":
    main()
