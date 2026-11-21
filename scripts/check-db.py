#!/usr/bin/env python3
"""Check the Downloader database written by make-db.py.

usage: check-db.py DB_JSON_ZIP [--downloader DOWNLOADER_SRC] [--index INDEX]

Fails (exit 1, every problem listed) unless:

* the zip holds exactly one `db.json`, as Downloader expects of a
  `*.json.zip` database;
* the format is the one of Downloader's docs/custom-databases.md, v1:
  only documented fields; `db_id` from cores.json and matching Downloader's
  ID regex; integer `timestamp`; files with an MD5 `hash`, an integer
  `size`, an `http(s)` `url` to a public host, `tags` that are indexes of
  `tag_dictionary`, a `tangle` list; folders; normalized tag names;
* every path passes Downloader's path rules (also MiSTerStation's, which
  are the same: relative, no `..`, not under `linux/`, `screenshots/`,
  `savestates/`, `downloader/`, not `MiSTer.ini` and the other reserved
  files), lies in the database's folder, has its parent in `folders`, and
  is named `<Core>-Sinden_<YYYYMMDD>.rbf` for a core of cores.json, one
  file per core;
* with --index, the files are exactly the newest builds of the index
  (asset, size, url);
* with --downloader (a checkout of MiSTer-devel/Downloader_MiSTer, used
  read-only), Downloader's own code accepts it: `DbEntity` (the checks and
  the v1 migration run when it opens a database), its ID regex, and
  `check_folder_paths` / `check_file_pkg` on every entry (the checks its
  workers run before installing).
"""

import argparse
import ipaddress
import json
import os
import re
import sys
import zipfile
from urllib.parse import urlparse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

TOP_FIELDS = {"v", "db_id", "timestamp", "files", "folders", "base_files_url", "tag_dictionary",
              "default_options", "archives"}
FILE_FIELDS = {"hash", "size", "url", "tags", "overwrite", "path", "reboot", "tangle"}
FOLDER_FIELDS = {"tags", "path"}
DB_ID_RE = re.compile(r"^[a-zA-Z][-._a-zA-Z0-9]*[/]?[-._a-zA-Z0-9]+$")
INVALID_PATHS = {"mister.ini", "mister_alt.ini", "mister_alt_1.ini", "mister_alt_2.ini", "mister_alt_3.ini",
                 "mister.new", "downloader.ini", "mister", "menu.rbf", "scripts/update.sh"}
INVALID_ROOTS = {"linux", "screenshots", "savestates", "downloader", "saves"}


def url_ok(url):
    try:
        u = urlparse(url)
        if u.scheme not in ("http", "https") or "\r" in url or "\n" in url or not u.hostname:
            return False
        if u.hostname.lower() == "localhost":
            return False
        try:
            ip = ipaddress.ip_address(u.hostname)
            return not (ip.is_private or ip.is_loopback)
        except ValueError:
            return True
    except ValueError:
        return False


def path_problem(path):
    if not isinstance(path, str) or path == "" or path[0] in "/.\\":
        return "not a relative path"
    lower = path.lower()
    parts = lower.split("/")
    if lower in INVALID_PATHS:
        return "reserved file"
    if len(parts) == 1 and lower.startswith("downloader_") and lower.endswith(".ini"):
        return "reserved file"
    if ".." in parts or "" in parts or parts[0] in INVALID_ROOTS:
        return "forbidden folder"
    return None


def check_format(db, cfg, index, problems):
    p = problems.append
    dbc = cfg["database"]
    folder = dbc["folder"]
    for k in db:
        if k not in TOP_FIELDS:
            p(f"undocumented top-level field {k!r}")
    if db.get("v") != 1:
        p(f"v must be 1, not {db.get('v')!r}")
    if db.get("db_id") != dbc["db_id"]:
        p(f"db_id {db.get('db_id')!r} is not {dbc['db_id']!r}")
    if not isinstance(db.get("db_id"), str) or not DB_ID_RE.match(db["db_id"]) or len(db["db_id"]) > 255:
        p("db_id does not match Downloader's ID regex")
    if not isinstance(db.get("timestamp"), int) or isinstance(db.get("timestamp"), bool) or db["timestamp"] <= 0:
        p("timestamp must be a positive integer")
    tags = db.get("tag_dictionary", {})
    if not isinstance(tags, dict):
        p("tag_dictionary must be an object")
        tags = {}
    for t, n in tags.items():
        if t != t.lower().replace("-", "").replace("_", "") or not t:
            p(f"tag {t!r} is not normalized (lowercase, no '-' or '_')")
        if not isinstance(n, int) or isinstance(n, bool) or n < 0:
            p(f"tag {t!r} has no integer index")
    indexes = set(tags.values())
    files, folders = db.get("files"), db.get("folders")
    if not isinstance(files, dict) or not files:
        p("files must be a non-empty object")
        files = {}
    if not isinstance(folders, dict):
        p("folders must be an object")
        folders = {}

    def check_tags(where, d):
        t = d.get("tags", [])
        if not isinstance(t, list) or not all(isinstance(x, int) and x in indexes for x in t):
            p(f"{where}: tags must be indexes of tag_dictionary")

    for path, d in folders.items():
        if path.rstrip("/") != folder:
            p(f"folder {path!r}: only {folder!r} is expected")
        if problem := path_problem(path.rstrip("/")):
            p(f"folder {path!r}: {problem}")
        if not isinstance(d, dict) or set(d) - FOLDER_FIELDS:
            p(f"folder {path!r}: unexpected fields")
            continue
        check_tags(f"folder {path!r}", d)
    names = {c["name"]: c for c in cfg["cores"]}
    seen, tangles = {}, {}
    rbf = re.compile(r"^(?P<core>[A-Za-z0-9_]+)-Sinden_(?P<date>\d{8})\.rbf$")
    for path, d in files.items():
        where = f"file {path!r}"
        if problem := path_problem(path):
            p(f"{where}: {problem}")
        if os.path.dirname(path) not in [f.rstrip("/") for f in folders]:
            p(f"{where}: its folder is not in folders")
        if os.path.dirname(path) != folder:
            p(f"{where}: not in {folder}/")
        m = rbf.match(os.path.basename(path))
        if not m or m["core"] not in names:
            p(f"{where}: not named <Core>-Sinden_<YYYYMMDD>.rbf for a core of cores.json")
        elif m["core"] in seen:
            p(f"{where}: second file for {m['core']} ({seen[m['core']]})")
        else:
            seen[m["core"]] = path
        if not isinstance(d, dict):
            p(f"{where}: not an object")
            continue
        if extra := set(d) - FILE_FIELDS:
            p(f"{where}: undocumented fields {sorted(extra)}")
        if not isinstance(d.get("hash"), str) or not re.fullmatch(r"[0-9a-f]{32}", d["hash"]):
            p(f"{where}: hash must be a lowercase MD5")
        if not isinstance(d.get("size"), int) or isinstance(d.get("size"), bool) or d["size"] <= 0:
            p(f"{where}: size must be a positive integer")
        if not isinstance(d.get("url"), str) or not url_ok(d["url"]) or not d["url"].startswith("https://"):
            p(f"{where}: url must be https to a public host")
        check_tags(where, d)
        t = d.get("tangle")
        if not (isinstance(t, list) and len(t) == 1 and isinstance(t[0], str)):
            p(f"{where}: tangle must be one string")
        elif t[0] in tangles:
            p(f"{where}: tangle {t[0]!r} also used by {tangles[t[0]]}")
        else:
            tangles[t[0]] = path
        for k in ("overwrite", "reboot", "path"):
            if k in d:
                p(f"{where}: {k} is not expected")
    if index is not None:
        want = {f"{folder}/{e['asset']}": e for n, e in index.items() if n in names}
        if set(want) != set(files):
            p(f"files {sorted(files)} are not the index's newest builds {sorted(want)}")
        for path, e in want.items():
            d = files.get(path)
            if isinstance(d, dict) and (d.get("size") != e["size"] or d.get("url") != e["download_url"]):
                p(f"file {path!r}: size or url differ from the index")


def check_with_downloader(db, src, problems):
    sys.path.insert(0, os.path.join(src, "src"))
    from downloader import db_entity
    from downloader.config_reader import ConfigReader
    from downloader.path_package import PathPackage, PATH_TYPE_FILE, PATH_PACKAGE_KIND_STANDARD

    db_id = db["db_id"]
    try:
        ConfigReader._valid_db_id(ConfigReader.__new__(ConfigReader), "db_id", db_id)
    except Exception as e:
        problems.append(f"Downloader: {e}")
    try:
        entity = db_entity.DbEntity(json.loads(json.dumps(db)), db_id)
        err = entity.migrate()
        if err is not None:
            raise err
        db_entity.check_folder_paths(list(entity.folders), db_id)
        for path, d in entity.files.items():
            pkg = PathPackage(path, None, d, PATH_TYPE_FILE, PATH_PACKAGE_KIND_STANDARD, None)
            db_entity.check_file_pkg(pkg, db_id, entity.base_files_url + path if "url" not in d else None)
        for zip_id, z in entity.zips.items():
            db_entity.check_zip_description(z, db_id, zip_id)
    except Exception as e:
        problems.append(f"Downloader: {type(e).__name__}: {e}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("db_zip")
    ap.add_argument("--downloader")
    ap.add_argument("--index")
    args = ap.parse_args()
    with open(os.path.join(ROOT, "cores.json")) as f:
        cfg = json.load(f)
    problems = []
    with zipfile.ZipFile(args.db_zip) as z:
        if z.namelist() != ["db.json"]:
            sys.exit(f"{args.db_zip}: must hold exactly db.json, holds {z.namelist()}")
        db = json.loads(z.read("db.json"))
    index = None
    if args.index:
        with open(args.index) as f:
            index = json.load(f)["cores"]
    check_format(db, cfg, index, problems)
    if args.downloader:
        check_with_downloader(db, args.downloader, problems)
    for pr in problems:
        print(f"::error::db.json: {pr}")
    if problems:
        sys.exit(1)
    print(f"{args.db_zip}: valid ({len(db['files'])} files, db_id {db['db_id']}, timestamp {db['timestamp']}"
          + (", accepted by Downloader's code" if args.downloader else "") + ")")


if __name__ == "__main__":
    main()
