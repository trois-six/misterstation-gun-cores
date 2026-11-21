#!/usr/bin/env python3
"""Decide which cores need a build.

For every core of cores.json, compares the upstream branch with the entry of
the published index (release `latest`, asset index.json):
  * upstream HEAD commit unchanged and same recipe -> skip (one ls-remote);
  * otherwise a shallow, blob-less fetch gives the source key: the hash of the
    HEAD tree without `releases/` (MiSTer release commits only add an .rbf
    there, they must not trigger a rebuild); same key and recipe -> skip;
  * the patch is checked on the new sys/ascal.vhd (one blob): a core whose
    patch no longer applies is reported, not built.
The recipe hash covers the patcher, the build script, the Quartus image, the
border geometry and the core's entry, so changing any of them rebuilds.

Writes JSON to stdout: {"matrix": [...], "patch_failures": [...], "skipped": [...]}.
"""

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import sinden_border  # noqa: E402


def git(*args, cwd=None):
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True).stdout


def recipe_hash(cfg, core):
    h = hashlib.sha256()
    for rel in ("scripts/sinden_border.py", "scripts/build-core.sh"):
        with open(os.path.join(ROOT, rel), "rb") as f:
            h.update(f.read())
    keep = {k: core[k] for k in ("name", "repo", "branch", "project", "revision")}
    h.update(json.dumps([cfg["quartus_image"], cfg["border"], cfg["inset"], keep], sort_keys=True).encode())
    return h.hexdigest()[:16]


def fetch_head(repo, branch, workdir, cache):
    """Shallow blob-less fetch of the branch; returns the local git dir."""
    if (repo, branch) in cache:
        return cache[(repo, branch)]
    d = os.path.join(workdir, repo.replace("/", "_") + "_" + branch)
    git("init", "-q", "--bare", d)
    git("fetch", "-q", "--depth=1", "--filter=blob:none", f"https://github.com/{repo}", f"+refs/heads/{branch}:refs/heads/b", cwd=d)
    commit = git("rev-parse", "refs/heads/b", cwd=d).decode().strip()
    date = git("log", "-1", "--format=%cI", "refs/heads/b", cwd=d).decode().strip()
    tree = git("ls-tree", "refs/heads/b", cwd=d).decode().splitlines()
    tree = [t for t in tree if t.split("\t", 1)[1] != "releases"]
    key = hashlib.sha1("\n".join(tree).encode()).hexdigest()[:16]
    cache[(repo, branch)] = (d, commit, date, key)
    return cache[(repo, branch)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--index", help="current index.json (may be missing)")
    ap.add_argument("--force", action="store_true", help="build every selected core")
    ap.add_argument("--only", default="", help="comma-separated core names (default: all)")
    args = ap.parse_args()

    with open(os.path.join(ROOT, "cores.json")) as f:
        cfg = json.load(f)
    index = {}
    if args.index and os.path.exists(args.index):
        with open(args.index) as f:
            index = json.load(f).get("cores", {})
    only = {c.strip() for c in args.only.split(",") if c.strip()}
    unknown = only - {c["name"] for c in cfg["cores"]}
    if unknown:
        sys.exit(f"unknown core(s): {', '.join(sorted(unknown))}")

    out = {"matrix": [], "patch_failures": [], "skipped": []}
    cache, heads = {}, {}
    with tempfile.TemporaryDirectory() as work:
        for core in cfg["cores"]:
            name = core["name"]
            if only and name not in only:
                continue
            recipe = recipe_hash(cfg, core)
            prev = index.get(name, {})
            ref = (core["repo"], core["branch"])
            if ref not in heads:
                ls = git("ls-remote", f"https://github.com/{core['repo']}", f"refs/heads/{core['branch']}").decode().split()
                if not ls:
                    sys.exit(f"{name}: branch {core['branch']} not found in {core['repo']}")
                heads[ref] = ls[0]
            same_recipe = prev.get("recipe") == recipe
            if not args.force and same_recipe and prev.get("upstream_commit") == heads[ref]:
                out["skipped"].append({"name": name, "reason": "upstream unchanged"})
                continue
            d, commit, date, key = fetch_head(core["repo"], core["branch"], work, cache)
            if not args.force and same_recipe and prev.get("source_key") == key:
                out["skipped"].append({"name": name, "reason": f"only releases/ changed upstream ({commit[:7]})"})
                continue
            try:
                src = git("show", "refs/heads/b:sys/ascal.vhd", cwd=d).decode("latin-1")
                sinden_border.patch_text(src, cfg["border"], cfg["inset"])
            except (sinden_border.PatchError, subprocess.CalledProcessError) as e:
                msg = str(e) if isinstance(e, sinden_border.PatchError) else "sys/ascal.vhd not found"
                out["patch_failures"].append({"name": name, "repo": core["repo"], "commit": commit, "error": msg})
                continue
            out["matrix"].append({
                **core,
                "commit": commit,
                "commit_date": date,
                "source_key": key,
                "recipe": recipe,
                "image": cfg["quartus_image"],
                "border": cfg["border"],
                "inset": cfg["inset"],
                "reason": "forced" if args.force else ("new recipe" if not same_recipe else f"upstream {prev.get('upstream_commit', 'none')[:7]} -> {commit[:7]}"),
            })
    json.dump(out, sys.stdout)
    print()


if __name__ == "__main__":
    main()
