"""Shared helpers for fetch units: read files from public GitHub repos through the session
git proxy (api.github.com is not reachable; blobless clones and raw URLs are)."""
import json
import os
import subprocess
import sys
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


def show(path, file):
    """File contents as text, or None if the file is not in the tree."""
    r = subprocess.run(["git", "-C", path, "show", f"HEAD:{file}"], capture_output=True, text=True)
    return r.stdout if r.returncode == 0 else None


def manifest(name, **fields):
    fields["fetched_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with open(f"data/raw/manifest_{name}.json", "w") as f:
        json.dump(fields, f, indent=1, default=str)


def run(main, out):
    """Unit wrapper: any failure writes an empty output file and exits 0."""
    try:
        os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
        main()
    except Exception:
        traceback.print_exc(file=sys.stderr)
        open(out, "w").close()
    sys.exit(0)
