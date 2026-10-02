"""Shared helpers for fetch units: read files from public GitHub repos through the session
git proxy (api.github.com is not reachable; blobless clones and raw URLs are)."""
import json
import os
import subprocess
import sys
import time
import traceback
from datetime import datetime, timezone

SRC = "data/raw/_src"


def clone(repo, name):
    """Blobless, no-checkout clone (fetches file contents lazily on `show`). Reused if present."""
    path = os.path.join(SRC, name)
    if not os.path.isdir(os.path.join(path, ".git")):
        os.makedirs(SRC, exist_ok=True)
        subprocess.run(["git", "clone", "--quiet", "--filter=blob:none", "--no-checkout", "--depth", "1",
                        f"https://github.com/{repo}", path], check=True)
    return path


def commit(path):
    return subprocess.run(["git", "-C", path, "rev-parse", "HEAD"], check=True,
                          capture_output=True, text=True).stdout.strip()


def tree(path):
    out = subprocess.run(["git", "-C", path, "ls-tree", "-r", "--name-only", "HEAD"],
                         check=True, capture_output=True, text=True).stdout
    return out.splitlines()


def show(path, file, attempts=4):
    """File contents as text, or None if `git show` still fails after `attempts` tries. Every caller asks only for
    files listed by `tree()`, so a failure here is a transient lazy-blob fetch through the proxy, not a missing file;
    it is retried (1, 2, 4 s back-off) rather than allowed to drop a file from a panel silently, which is how one
    stock file (BBD) vanished from a 2026-10-02 fetch. `pipeline.verify_raw` catches anything that still slips."""
    for i in range(attempts):
        r = subprocess.run(["git", "-C", path, "show", f"HEAD:{file}"], capture_output=True, text=True)
        if r.returncode == 0:
            return r.stdout
        if i < attempts - 1:
            time.sleep(2 ** i)
    return None


def manifest(name, **fields):
    fields["fetched_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with open(f"data/raw/manifest_{name}.json", "w") as f:
        json.dump(fields, f, indent=1, default=str)


def run(main, out):
    """Unit wrapper (ACCEPTANCE A32): any failure writes an empty output file AND `<out>.error`
    with the traceback, then exits 2 so a dead unit is visible but never blocks the fleet."""
    try:
        os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
        main()
        err = out + ".error"
        if os.path.exists(err):
            os.remove(err)
    except Exception:
        tb = traceback.format_exc()
        sys.stderr.write(tb)
        open(out, "w").close()
        with open(out + ".error", "w") as f:
            f.write(tb)
        sys.exit(2)
    sys.exit(0)
