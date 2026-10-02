"""Verify a fresh `make fetch` against the committed provenance (RETRO 2026-10-02: provenance recorded, never compared).

Every fetch unit rewrites `data/raw/manifest_<name>.json` (`pipeline/units/_gh.py`, `manifest`). The committed copies
of those manifests describe the exact inputs every published table in `out/` was built from. A fresh fetch that
differs used to change results silently. Two cases are on record, both found 2026-10-02:
- a daily-updated upstream (VIX), now pinned in the Makefile;
- a transiently skipped file (one stock, BBD), which shifted all seven own-account outputs.

This step makes such a fetch fail loudly instead. It checks:
  1. every committed manifest is rewritten with identical content, ignoring only `fetched_at`;
  2. every manifest's data file exists and holds exactly the manifest's `rows` (parquet metadata only, no full read);
  3. no `data/raw/*.error` file exists.

On success the committed manifests are restored byte-for-byte: their `fetched_at` churn is not provenance worth
committing, so a clean fetch leaves `git status` clean. On failure nothing is restored, so the fresh manifests can be
inspected, and the exit code is 1.

    python -m pipeline.verify_raw        # the last step of `make fetch`; also `make verify-raw`
"""
import argparse
import glob
import json
import os
import subprocess
import sys

import pyarrow.parquet as pq

IGNORED = {"fetched_at"}
DATA_FILE = {   # manifest name -> the data file its fetch command writes (Makefile `fetch`)
    "vix": "vix_daily.parquet",
    "oanda_SPX500_USD": "oanda_SPX500_USD.parquet",
    "oanda_XAU_USD": "oanda_XAU_USD.parquet",
    "histdata_SPXUSD": "histdata_SPXUSD.parquet",
    "histdata_GRXEUR": "histdata_GRXEUR.parquet",
    "histdata_ETXEUR": "histdata_ETXEUR.parquet",
    "histdata_JPXJPY": "histdata_JPXJPY.parquet",
    "bigmovers_spy": "spy_daily.parquet",
    "bigmovers_stocks": "stocks_daily.parquet",
    "etf_kaggle": "etf_daily_kaggle.parquet",
}


def _git(repo, *args, text=True):
    return subprocess.run(["git", "-C", repo, *args], capture_output=True, text=text)


def tracked_manifests(repo=".", root="data/raw"):
    r = _git(repo, "ls-files", f"{root}/manifest_*.json")
    if r.returncode != 0:
        raise SystemExit(f"verify_raw: not a git checkout ({r.stderr.strip()}); cannot read the committed manifests")
    return r.stdout.split()


def check(repo=".", root="data/raw"):
    """Return (manifest names checked, list of problems). An empty problem list means the fetch matches."""
    problems, names = [], []
    paths = tracked_manifests(repo, root)
    if not paths:
        problems.append(f"no committed manifests under {root}")
    for path in paths:
        name = os.path.basename(path)[len("manifest_"):-len(".json")]
        names.append(name)
        old = json.loads(_git(repo, "show", f"HEAD:{path}").stdout)
        try:
            with open(os.path.join(repo, path)) as f:
                new = json.load(f)
        except FileNotFoundError:
            problems.append(f"{name}: manifest missing")
            continue
        for key in sorted((set(old) | set(new)) - IGNORED):
            if old.get(key) != new.get(key):
                problems.append(f"{name}: {key} committed {old.get(key)!r} != fetched {new.get(key)!r}")
        data = DATA_FILE.get(name)
        if data is None:
            problems.append(f"{name}: no data file mapped for this manifest (add it to DATA_FILE)")
            continue
        dpath = os.path.join(repo, root, data)
        if not os.path.exists(dpath) or os.path.getsize(dpath) == 0:
            problems.append(f"{name}: {root}/{data} missing or empty")
            continue
        if "rows" in new:
            n = pq.ParquetFile(dpath).metadata.num_rows
            if n != new["rows"]:
                problems.append(f"{name}: {root}/{data} holds {n} rows but the manifest says {new['rows']}")
    for err in sorted(glob.glob(os.path.join(repo, root, "*.error"))):
        problems.append(f"error file present: {os.path.relpath(err, repo)}")
    return names, problems


def restore(repo=".", root="data/raw"):
    """Write each committed manifest back byte-for-byte; returns how many had drifted (fetched_at only, by now)."""
    n = 0
    for path in tracked_manifests(repo, root):
        committed = _git(repo, "show", f"HEAD:{path}", text=False).stdout
        full = os.path.join(repo, path)
        with open(full, "rb") as f:
            current = f.read()
        if current != committed:
            with open(full, "wb") as f:
                f.write(committed)
            n += 1
    return n


def main(repo=".", root="data/raw"):
    names, problems = check(repo, root)
    if problems:
        print(f"VERIFY RAW: FAIL — {len(problems)} problem(s) across {len(names)} committed manifests; the fetch does "
              "not match the provenance every published table was built from (fresh manifests left in place):")
        for p in problems:
            print("  -", p)
        sys.exit(1)
    restored = restore(repo, root)
    print(f"VERIFY RAW: PASS — {len(names)} manifests match the committed provenance (ignoring fetched_at), every data "
          f"file holds its manifest's row count, no .error files; restored {restored} manifest(s) to the committed bytes")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--repo", default=".")
    ap.add_argument("--root", default="data/raw")
    a = ap.parse_args()
    main(a.repo, a.root)
