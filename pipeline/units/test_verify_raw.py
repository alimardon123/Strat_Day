"""Tests for pipeline.verify_raw (a fresh fetch must match the committed manifests) and pipeline.units._gh.show's retry.

Each test builds a throwaway git repository holding one committed manifest and its parquet data file, then mutates
the "fetched" side the way a real fetch can drift. Runnable with pytest, or directly:
    python -m pipeline.units.test_verify_raw
"""
import json
import os
import subprocess
import sys
import tempfile
from types import SimpleNamespace
from unittest import mock

import pandas as pd

from pipeline import verify_raw
from pipeline.units import _gh

MANIFEST = {"repo": "willhjw/big_movers", "commit": "8ccb831", "files_read": 3, "files_skipped": [], "rows": 5,
            "tickers": 3, "fetched_at": "2026-09-12T19:48:36+00:00"}


def _repo(manifest=MANIFEST, rows=5, name="bigmovers_stocks"):
    """A committed manifest plus a data file holding `rows` rows; returns the repo path."""
    d = tempfile.mkdtemp()
    os.makedirs(os.path.join(d, "data/raw"))
    git = ["git", "-C", d, "-c", "user.name=t", "-c", "user.email=t@t"]
    subprocess.run(["git", "init", "-q", d], check=True)
    with open(os.path.join(d, f"data/raw/manifest_{name}.json"), "w") as f:
        json.dump(manifest, f, indent=1)
    pd.DataFrame({"x": range(rows)}).to_parquet(os.path.join(d, "data/raw", verify_raw.DATA_FILE[name]))
    with open(os.path.join(d, ".gitignore"), "w") as f:          # the real repo's rule: data ignored, manifests kept
        f.write("data/raw/*\n!data/raw/manifest_*.json\n")
    subprocess.run(git + ["add", ".gitignore", f"data/raw/manifest_{name}.json"], check=True)
    subprocess.run(git + ["commit", "-q", "-m", "manifest"], check=True)
    return d


def _fetched(d, name="bigmovers_stocks", **changes):
    """Rewrite the working manifest as a fresh fetch would, with `changes` applied."""
    m = dict(MANIFEST, fetched_at="2026-10-02T16:48:00+00:00", **changes)
    with open(os.path.join(d, f"data/raw/manifest_{name}.json"), "w") as f:
        json.dump(m, f, indent=1)


def test_clean_fetch_passes_and_restores_committed_bytes():
    d = _repo()
    committed = subprocess.run(["git", "-C", d, "show", "HEAD:data/raw/manifest_bigmovers_stocks.json"],
                               capture_output=True).stdout
    _fetched(d)                                                  # only fetched_at differs
    names, problems = verify_raw.check(d)
    assert names == ["bigmovers_stocks"] and problems == []
    assert verify_raw.restore(d) == 1
    with open(os.path.join(d, "data/raw/manifest_bigmovers_stocks.json"), "rb") as f:
        assert f.read() == committed
    assert subprocess.run(["git", "-C", d, "status", "--porcelain"], capture_output=True, text=True).stdout == ""


def test_skipped_file_fails_naming_the_field():                  # the BBD case: one file dropped, rows and tickers fall
    d = _repo(rows=5)
    _fetched(d, files_read=2, files_skipped=["collected_stocks/BBD.csv: boom"], rows=5, tickers=2)
    _, problems = verify_raw.check(d)
    assert any("files_skipped" in p for p in problems)
    assert any("files_read" in p for p in problems) and any("tickers" in p for p in problems)


def test_upstream_drift_fails():                                 # the VIX case: same unit, newer upstream content
    d = _repo()
    _fetched(d, commit="3dbea23")
    _, problems = verify_raw.check(d)
    assert problems == ["bigmovers_stocks: commit committed '8ccb831' != fetched '3dbea23'"]


def test_data_file_row_count_must_match_manifest():
    d = _repo(rows=4)                                            # manifest says 5, file holds 4
    _fetched(d)
    _, problems = verify_raw.check(d)
    assert problems == ["bigmovers_stocks: data/raw/stocks_daily.parquet holds 4 rows but the manifest says 5"]


def test_missing_data_file_fails():
    d = _repo()
    _fetched(d)
    os.remove(os.path.join(d, "data/raw/stocks_daily.parquet"))
    _, problems = verify_raw.check(d)
    assert problems == ["bigmovers_stocks: data/raw/stocks_daily.parquet missing or empty"]


def test_error_file_fails():
    d = _repo()
    _fetched(d)
    open(os.path.join(d, "data/raw/stocks_daily.parquet.error"), "w").write("traceback")
    _, problems = verify_raw.check(d)
    assert problems == ["error file present: data/raw/stocks_daily.parquet.error"]


def test_missing_manifest_fails():
    d = _repo()
    os.remove(os.path.join(d, "data/raw/manifest_bigmovers_stocks.json"))
    _, problems = verify_raw.check(d)
    assert problems == ["bigmovers_stocks: manifest missing"]


def test_unmapped_manifest_fails():
    d = _repo()
    git = ["git", "-C", d, "-c", "user.name=t", "-c", "user.email=t@t"]
    with open(os.path.join(d, "data/raw/manifest_newsource.json"), "w") as f:
        json.dump({"rows": 1}, f)
    subprocess.run(git + ["add", "data/raw/manifest_newsource.json"], check=True)
    subprocess.run(git + ["commit", "-q", "-m", "new"], check=True)
    _fetched(d)
    _, problems = verify_raw.check(d)
    assert problems == ["newsource: no data file mapped for this manifest (add it to DATA_FILE)"]


def test_main_fails_without_restoring_and_passes_with_restore():
    d = _repo()
    _fetched(d, rows=6)
    try:
        verify_raw.main(d)
        raise AssertionError("main() must exit non-zero on a mismatch")
    except SystemExit as e:
        assert e.code == 1
    with open(os.path.join(d, "data/raw/manifest_bigmovers_stocks.json")) as f:
        assert json.load(f)["rows"] == 6                         # fresh manifest left in place for inspection
    _fetched(d)
    verify_raw.main(d)                                           # passes: returns normally
    assert subprocess.run(["git", "-C", d, "status", "--porcelain"], capture_output=True, text=True).stdout == ""


def test_every_makefile_manifest_is_mapped():
    """DATA_FILE must cover every manifest this checkout commits, so a new fetch unit cannot be added unverified."""
    names = [os.path.basename(p)[len("manifest_"):-len(".json")] for p in verify_raw.tracked_manifests(".")]
    assert names and set(names) <= set(verify_raw.DATA_FILE)


def test_show_retries_transient_failures_then_succeeds():
    calls = []

    def fake_run(cmd, capture_output, text):
        calls.append(cmd)
        ok = len(calls) == 3
        return SimpleNamespace(returncode=0 if ok else 128, stdout="a,b\n" if ok else "")
    with mock.patch.object(_gh.subprocess, "run", fake_run), mock.patch.object(_gh.time, "sleep") as sleep:
        assert _gh.show("repo", "f.csv") == "a,b\n"
    assert len(calls) == 3 and [c.args[0] for c in sleep.call_args_list] == [1, 2]


def test_show_returns_none_after_all_attempts():
    with mock.patch.object(_gh.subprocess, "run", return_value=SimpleNamespace(returncode=128, stdout="")) as run, \
            mock.patch.object(_gh.time, "sleep"):
        assert _gh.show("repo", "f.csv") is None
    assert run.call_count == 4


def main():
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    failed = 0
    for t in tests:
        try:
            t()
            print(f"[PASS] {t.__name__}")
        except Exception as e:  # noqa: BLE001
            failed += 1
            print(f"[FAIL] {t.__name__}: {type(e).__name__}: {e}")
    print(f"{len(tests) - failed}/{len(tests)} passed")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
