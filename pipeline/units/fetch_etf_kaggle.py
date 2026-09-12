"""Fetch unit: daily ETF files from the Kaggle "Huge Stock Market Dataset" GitHub mirror
(neo-zhao/CMSC320_Final_Tutorial_Huge_Stock_Market_Dataset), long format. Files are
`<dir>/<ticker>.us.txt` with header Date,Open,High,Low,Close,Volume,OpenInt; panel ends 2017-11-10.

    python -m pipeline.units.fetch_etf_kaggle --in ETFs --out data/raw/etf_daily_kaggle.parquet
"""
import argparse
import io
import pandas as pd
from pipeline.units import _gh

REPO = "neo-zhao/CMSC320_Final_Tutorial_Huge_Stock_Market_Dataset"
UNIVERSE = ("spy efa eem ewj ewz ewa tlt ief lqd hyg tip gld slv gdx dbc dba uso xop uup "
            "fxe fxy fxb vnq rwx iyr").split()
VOL = "vxx vxz vixy vixm svxy uvxy".split()
INDEX_ETFS = ("qqq iwm dia mdy ijh ijr iwb iwv ivv voo vti vtv vug iwd iwf ewg ewu ewc ewh "
              "ews ewt ewy eza ilf epp fxi").split()


def main(dirname, out):
    path = _gh.clone(REPO, "kaggle_etfs")
    files = {f.rsplit("/", 1)[-1][:-7]: f for f in _gh.tree(path)
             if f.split("/")[-2:-1] == [dirname] and f.endswith(".us.txt")}
    want = list(dict.fromkeys(UNIVERSE + VOL + INDEX_ETFS))
    frames, missing = [], []
    for t in want:
        txt = _gh.show(path, files[t]) if t in files else None
        if not txt:
            missing.append(t)
            continue
        d = pd.read_csv(io.StringIO(txt))
        d.columns = [c.strip().lower() for c in d.columns]
        d["date"] = pd.to_datetime(d["date"], errors="coerce")
        d = d.dropna(subset=["date", "close"])
        d.insert(0, "ticker", t)
        frames.append(d[["ticker", "date", "open", "high", "low", "close", "volume", "openint"]])
    df = pd.concat(frames, ignore_index=True).sort_values(["ticker", "date"]).drop_duplicates(["ticker", "date"])
    df = df.astype({c: "float64" for c in ["open", "high", "low", "close", "volume", "openint"]})
    df.to_parquet(out, index=False)
    _gh.manifest("etf_kaggle", repo=REPO, commit=_gh.commit(path), tickers_found=sorted(df["ticker"].unique()),
                 tickers_missing=missing, rows=len(df), date_min=df["date"].min(), date_max=df["date"].max())


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", default="ETFs")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    _gh.run(lambda: main(a.inp, a.out), a.out)
