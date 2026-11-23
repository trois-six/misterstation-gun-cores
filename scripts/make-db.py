#!/usr/bin/env python3
"""Generate the Downloader database (db.json, db.json.zip) from index.json.

usage: make-db.py INDEX OUT_DIR [PREVIOUS_DB_JSON]

The database lists the newest build of every core of cores.json that the
index has, as `<folder>/<asset>` (`_LightGun/NES-Sinden_20261121.rbf`),
downloaded from its release asset: each asset is fetched once to compute
its MD5 (Downloader's hash) and to check its size and sha256 against the
index. Tags follow Distribution_MiSTer's filter terms (`nes`, `console`,
`cores`...) plus `lightgun`/`sinden`, so a user's global download filter
treats a Sinden core like the official one.

When PREVIOUS_DB_JSON lists the same files, folders and tags, its
timestamp is kept and the output is byte-identical (the zip has a fixed
date), so an unchanged database is not republished. Prints `changed` or
`unchanged`.
"""

import datetime
import hashlib
import json
import os
import sys
import urllib.request
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ZIP_DATE = (2000, 1, 1, 0, 0, 0)


def normalize(tag):
    # Downloader matches filter terms lowercased, without '-' and '_'.
    return tag.lower().replace("-", "").replace("_", "")


def fetch(url, sha256, size):
    req = urllib.request.Request(url, headers={"User-Agent": "misterstation-sinden-cores"})
    md5, sha = hashlib.md5(), hashlib.sha256()
    n = 0
    with urllib.request.urlopen(req, timeout=120) as r:
        while chunk := r.read(1 << 20):
            md5.update(chunk)
            sha.update(chunk)
            n += len(chunk)
    if n != size or sha.hexdigest() != sha256:
        sys.exit(f"{url}: size {n} / sha256 {sha.hexdigest()} do not match the index ({size} / {sha256})")
    return md5.hexdigest()


def tag_dictionary(cfg):
    """Every tag (and alias) -> index; aliases share their group's index."""
    groups = [[normalize(t) for t in g] for g in cfg["database"]["tag_aliases"]]
    used = list(cfg["database"]["tags"])
    for core in cfg["cores"]:
        used += core["tags"]
    for t in map(normalize, used):
        if not any(t in g for g in groups):
            groups.append([t])
    # only the groups some entry uses, numbered in order of first use
    order = []
    for t in map(normalize, used):
        g = next(i for i, g in enumerate(groups) if t in g)
        if g not in order:
            order.append(g)
    return {t: n for n, g in enumerate(order) for t in sorted(groups[g])}


def build(cfg, index):
    db = cfg["database"]
    folder = db["folder"]
    tags = tag_dictionary(cfg)
    common = [tags[normalize(t)] for t in db["tags"]]
    files, per_file_tags = {}, []
    for core in cfg["cores"]:
        entry = index.get(core["name"])
        if entry is None:
            print(f"{core['name']}: not built yet, not in the database", file=sys.stderr)
            continue
        ftags = []
        for t in [tags[normalize(t)] for t in core["tags"]] + common:
            if t not in ftags:
                ftags.append(t)
        per_file_tags.append(ftags)
        files[f"{folder}/{entry['asset']}"] = {
            "hash": fetch(entry["download_url"], entry["sha256"], entry["size"]),
            "size": entry["size"],
            "url": entry["download_url"],
            "tags": ftags,
            # the dated rbfs of a core are one entity: if a new one fails
            # to download, Downloader keeps the previous one
            "tangle": [f"{core['name'].lower()}_sinden_core"],
        }
    if not files:
        sys.exit("no core in the index: nothing to publish")
    # the folder keeps the tags every file has, as Distribution does
    # (`_Console`: console, cores), so a filter never drops it while
    # keeping one of its files
    folder_tags = [t for t in per_file_tags[0] if all(t in f for f in per_file_tags)]
    return {
        "v": 1,
        "db_id": db["db_id"],
        "timestamp": 0,
        "files": dict(sorted(files.items())),
        "folders": {folder: {"tags": folder_tags}},
        "tag_dictionary": tags,
    }


def main():
    if len(sys.argv) not in (3, 4):
        sys.exit(__doc__)
    index_path, out = sys.argv[1], sys.argv[2]
    with open(os.path.join(ROOT, "cores.json")) as f:
        cfg = json.load(f)
    with open(index_path) as f:
        index = json.load(f)["cores"]
    db = build(cfg, index)
    prev = None
    if len(sys.argv) == 4 and os.path.exists(sys.argv[3]):
        with open(sys.argv[3]) as f:
            prev = json.load(f)
    same = prev is not None and {**prev, "timestamp": 0} == db
    db["timestamp"] = prev["timestamp"] if same else int(datetime.datetime.now(datetime.timezone.utc).timestamp())
    text = json.dumps(db, indent=2) + "\n"
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, "db.json"), "w") as f:
        f.write(text)
    info = zipfile.ZipInfo("db.json", ZIP_DATE)
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = 0o644 << 16
    with zipfile.ZipFile(os.path.join(out, "db.json.zip"), "w") as z:
        z.writestr(info, text, compresslevel=9)
    print("unchanged" if same else "changed")


if __name__ == "__main__":
    main()
