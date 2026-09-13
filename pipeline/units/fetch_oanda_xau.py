"""Fetch unit: Oanda XAU_USD 1-minute bars (FutureSharks/financial-data), Track B gold range.
Unlike fetch_oanda.py, files are pulled one-by-one over raw.githubusercontent.com instead of
`_gh.clone` + `_gh.show`: a blobless clone of this repo grows past 5 GB once individual blobs
are fetched on demand, so we never clone here -- `git ls-remote` (refs only, no objects) finds
the HEAD commit, and each monthly CSV is a plain HTTPS GET against that commit, retried with
backoff. A missing month is recorded in the manifest rather than failing the unit.
Stamps are UTC, same convention as fetch_oanda.py's SPX500_USD bars (verified there against the
Sunday Globex open; not re-verified independently for gold, which trades the same Oanda session).

    python -m pipeline.units.fetch_oanda_xau --out data/raw/oanda_XAU_USD.parquet
"""
import argparse
import io
import subprocess
import time
import pandas as pd
import requests
from pipeline.units import _gh

REPO = "FutureSharks/financial-data"
BASE = "pyfinancialdata/data/currencies/oanda/XAU_USD"
FIRST, LAST = (2006, 3), (2020, 5)     # verified span of the source's monthly files (171 months)
RETRIES, BACKOFF = 4, 2.0              # attempts and base seconds for transient failures


def _head_commit(repo):
    """HEAD commit sha via `git ls-remote` (refs only -- no clone, no objects)."""
    out = subprocess.run(["git", "ls-remote", f"https://github.com/{repo}", "HEAD"],
                         check=True, capture_output=True, text=True).stdout
    return out.split()[0]


def _months():
    for y in range(FIRST[0], LAST[0] + 1):
        start_m = FIRST[1] if y == FIRST[0] else 1
        end_m = LAST[1] if y == LAST[0] else 12
        for m in range(start_m, end_m + 1):
            yield y, m


def _fetch(url):
    """GET with retry/backoff for transient failures; a real 404 returns None right away."""
    for attempt in range(RETRIES):
        try:
            r = requests.get(url, timeout=60)
        except requests.RequestException:
            r = None
        if r is not None and r.status_code == 200:
            return r.text
        if r is not None and r.status_code == 404:
            return None
        time.sleep(BACKOFF * (2 ** attempt))
    return None


def main(out):
    commit = _head_commit(REPO)
    pattern = f"https://raw.githubusercontent.com/{REPO}/<commit>/{BASE}/<year>/oanda-XAU_USD-<year>-<month>.csv"
    frames, files_read, missing = [], 0, []
    for y, m in _months():
        f = f"{BASE}/{y}/oanda-XAU_USD-{y}-{m}.csv"
        txt = _fetch(f"https://raw.githubusercontent.com/{REPO}/{commit}/{f}")
        if txt is None:
            missing.append(f"{y}-{m:02d}")
            continue
        frames.append(pd.read_csv(io.StringIO(txt), usecols=["time", "open", "high", "low", "close", "volume"]))
        files_read += 1
    df = pd.concat(frames, ignore_index=True)
    df["ts"] = pd.to_datetime(df["time"], utc=True)
    df = (df[["ts", "open", "high", "low", "close", "volume"]]
          .dropna(subset=["open", "high", "low", "close"])
          .sort_values("ts").reset_index(drop=True))
    n_before = len(df)
    df = df.drop_duplicates("ts").reset_index(drop=True)
    dupes_dropped = n_before - len(df)
    df["volume"] = df["volume"].fillna(0).astype("int64")
    df.to_parquet(out, index=False)
    years = df["ts"].dt.year.value_counts().sort_index()
    _gh.manifest("oanda_XAU_USD", repo=REPO, commit=commit, source_url_pattern=pattern,
                 files_expected=files_read + len(missing), files_read=files_read, months_missing=missing,
                 rows=len(df), duplicates_dropped=int(dupes_dropped),
                 ts_min=df["ts"].min(), ts_max=df["ts"].max(),
                 rows_per_year={int(k): int(v) for k, v in years.items()})


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data/raw/oanda_XAU_USD.parquet")
    a = ap.parse_args()
    _gh.run(lambda: main(a.out), a.out)
