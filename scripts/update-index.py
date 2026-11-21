#!/usr/bin/env python3
"""Merge new build manifests into the published index (index.json).

usage: update-index.py OLD_INDEX NEW_INDEX REPOSITORY MANIFEST...

Each MANIFEST is the <asset>.json written by build-core.sh, completed by the
workflow with release_tag, download_url, run_url, upstream_branch, source_key
and recipe. The index keeps, per core, the newest build; cores not rebuilt
keep their previous entry. OLD_INDEX may be missing (first build).
"""

import datetime
import json
import os
import sys


def main():
    if len(sys.argv) < 4:
        sys.exit(__doc__)
    old, new, repo, manifests = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4:]
    cores = {}
    if os.path.exists(old):
        with open(old) as f:
            cores = json.load(f).get("cores", {})
    for path in manifests:
        with open(path) as f:
            m = json.load(f)
        cores[m["core"]] = m
    index = {
        "format": 1,
        "repository": f"https://github.com/{repo}",
        "generated_at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "cores": dict(sorted(cores.items())),
    }
    with open(new, "w") as f:
        json.dump(index, f, indent=2)
        f.write("\n")


if __name__ == "__main__":
    main()
